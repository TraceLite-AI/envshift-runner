#!/usr/bin/env python3
"""探针:除了 pathlib.Path,还有哪些「语言内建抽象在撒谎」的地方。

为什么找这个(2026-09-17 从三轮失败里反推):
  已确认的 12 道 badcase 全是「语言抽象撒谎」——Windows 上 Path('k')==Path('K') 返回 True,
  而 NTFS 里那是两个文件。agent 没有任何理由去怀疑一个语言内建的相等判断。
  反过来,我三次针对 macOS 的尝试全败(0/22),因为 macOS 的缺口在**文件系统**,
  而 agent 对外部状态有系统性防御:写完回读、清点前 stat、去重按 inode,都自发做了。

  → 结论:环境差异只有落在**语言内建抽象**上才形成盲区。本探针按这条找新机制。

每条测的都是同一个形状:**语言层的判断 vs 真实状态**,不一致的地方就是候选机制。
"""
import json
import os
import pathlib
import shutil
import stat
import sys
import tempfile
import time

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OUT = {"platform": sys.platform, "os_name": os.name}


def rec(k, v):
    OUT[k] = v


def tmpdir():
    return pathlib.Path(tempfile.mkdtemp(prefix="absl_"))


# ── A. os.environ:环境变量名的大小写 ──────────────────────────────────
def probe_environ():
    r = {}
    try:
        os.environ["ABSLPROBE_Mixed"] = "AAA"
        r["按原样取"] = os.environ.get("ABSLPROBE_Mixed")
        r["按全大写取"] = os.environ.get("ABSLPROBE_MIXED")
        r["按全小写取"] = os.environ.get("abslprobe_mixed")
        keys = [k for k in os.environ if k.upper().startswith("ABSLPROBE")]
        r["实际存下来的键"] = keys
        # 写两个只差大小写的名字,看是一个还是两个
        os.environ["ABSLPROBE_dup"] = "AAA"
        os.environ["ABSLPROBE_DUP"] = "BBB"
        dup = [k for k in os.environ if k.upper() == "ABSLPROBE_DUP"]
        r["只差大小写的两个名字"] = {"键数": len(dup), "键": dup,
                                    "取回": os.environ.get("ABSLPROBE_dup")}
        r["撒谎"] = len(dup) == 1
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        for k in [k for k in list(os.environ) if k.upper().startswith("ABSLPROBE")]:
            os.environ.pop(k, None)
    return r


# ── B. 尾随点/空格:exists() 说有,盘上未必是那个名字 ────────────────────
def probe_trailing():
    d = tmpdir()
    r = {}
    try:
        (d / "base").write_bytes(b"AAA")
        for tag, nm in (("尾点", "base."), ("尾空格", "base "), ("双尾点", "base..")):
            p = d / nm
            r[tag + "_exists说有"] = p.exists()
            try:
                r[tag + "_读到的字节"] = p.read_bytes().decode()
            except OSError as e:
                r[tag + "_读到的字节"] = "ERR " + type(e).__name__
        r["目录里实际的名字"] = sorted(x.name for x in d.iterdir())
        # 撒谎 = exists() 说存在,但目录里根本没有这个名字
        r["撒谎"] = bool(r.get("尾点_exists说有")) and "base." not in r["目录里实际的名字"]
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return r


# ── C. 保留设备名:open 成功,但没落下文件 ──────────────────────────────
def probe_reserved():
    d = tmpdir()
    r = {}
    try:
        for nm in ("CON", "NUL", "AUX", "COM1"):
            p = d / (nm + ".txt")
            try:
                p.write_bytes(b"AAA")
                wrote = True
            except OSError as e:
                wrote = "ERR " + type(e).__name__
            r[nm] = {"写入": wrote, "exists": p.exists() if wrote is True else None}
        r["目录里实际的名字"] = sorted(x.name for x in d.iterdir())
        # 撒谎 = 写入成功且 exists 说有,但目录里没这个名字
        r["撒谎"] = any(isinstance(v, dict) and v.get("写入") is True and v.get("exists")
                        and (k + ".txt") not in r["目录里实际的名字"]
                        for k, v in r.items() if isinstance(v, dict))
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return r


# ── D. 时间戳精度:写进去的和读回来的不是同一个数 ──────────────────────
def probe_mtime():
    d = tmpdir()
    r = {}
    try:
        p = d / "t.bin"
        p.write_bytes(b"x")
        want = 1_700_000_000.123456789
        os.utime(p, (want, want))
        got = p.stat().st_mtime
        got_ns = p.stat().st_mtime_ns
        r["设置的"] = want
        r["读回的"] = got
        r["读回纳秒"] = got_ns
        r["差(纳秒)"] = abs(got_ns - int(want * 1e9))
        r["相等判断说一样"] = (got == want)
        r["撒谎"] = (got != want)
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return r


# ── E. 权限位:chmod 设进去,读回来不是那个值 ──────────────────────────
def probe_mode():
    d = tmpdir()
    r = {}
    try:
        p = d / "m.bin"
        p.write_bytes(b"x")
        os.chmod(p, 0o600)
        m = stat.S_IMODE(p.stat().st_mode)
        r["设的"] = "0o600"
        r["读回的"] = oct(m)
        r["撒谎"] = (m != 0o600)
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return r


# ── F. 子进程退出码语义 ───────────────────────────────────────────────
def probe_exitcode():
    import subprocess
    r = {}
    try:
        code = "import sys; sys.exit(255)"
        p = subprocess.run([sys.executable, "-c", code], capture_output=True)
        r["退出 255 读回"] = p.returncode
        code2 = "import sys; sys.exit(-1)"
        p2 = subprocess.run([sys.executable, "-c", code2], capture_output=True)
        r["退出 -1 读回"] = p2.returncode
        r["撒谎"] = (p.returncode != 255) or (p2.returncode not in (-1, 255))
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    return r


for name, fn in (("A_environ_case", probe_environ),
                 ("B_trailing_dot_space", probe_trailing),
                 ("C_reserved_names", probe_reserved),
                 ("D_mtime_precision", probe_mtime),
                 ("E_chmod_readback", probe_mode),
                 ("F_exit_code", probe_exitcode)):
    try:
        rec(name, fn())
    except Exception as e:
        rec(name, {"error": "%s: %s" % (type(e).__name__, e)})

print("ABSLPROBE " + json.dumps(OUT, ensure_ascii=False))
