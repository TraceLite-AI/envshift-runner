#!/usr/bin/env python3
"""三系统定向探针(第四轮):只测追加 50 题里那 10 条「合理但从未实测」的候选轴。

背景:那批题状态是 candidate_unvalidated,50 个候选轴里 22 条不是 OS 差异(要人为注入配置)、
10 条与已有机制重复、8 条在这三台上不成立,剩下这 10 条方向是新的但没有任何实测支撑。
今天已经有四条凭常识列的差异被真机推翻,所以一律先测再说。

★探针纪律(今天用血换来的):
- 调用形态要和真题一致:该走 PATH 查找就走 PATH 查找,不要先用 which 拿全路径绕开;
- 响型(报错/命令不存在)与静默型要分开标注,只有静默型能造题;
- 每个点都打印原始值,不做判断,判断留给对比。
"""
import os
import pathlib
import platform
import shutil
import stat
import subprocess
import sys
import tempfile

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

OUT = []
W = pathlib.Path(tempfile.mkdtemp(prefix="probe4_"))
IS_WIN = os.name == "nt"


def rec(k, v):
    OUT.append((k, str(v).replace("\n", "\\n").replace("\t", " ")[:200]))


def probe(k, fn):
    try:
        rec(k, fn())
    except Exception as e:
        rec(k, f"<{type(e).__name__}: {str(e)[:110]}>")


rec("Z00_platform", f"{platform.system()} {platform.machine()} py{platform.python_version()}")
rec("Z01_byteorder", sys.byteorder)

# ── CAND-48 / 49:Git 检出与工作树元数据 ────────────────────────────────
GIT = shutil.which("git") or "git"


def git(*args, cwd=None):
    r = subprocess.run([GIT, *args], cwd=str(cwd or W), capture_output=True, timeout=90)
    return (r.stdout + r.stderr).decode("utf-8", "replace").strip()


probe("G01_git_version", lambda: git("--version"))
probe("G02_autocrlf_default", lambda: git("config", "--get", "core.autocrlf") or "(未设)")
probe("G03_autocrlf_system", lambda: git("config", "--system", "--get", "core.autocrlf") or "(未设)")
probe("G04_filemode_default", lambda: git("config", "--get", "core.fileMode") or "(未设)")


def git_checkout_bytes():
    """建仓、提交一个 LF 文件、删掉再检出,看检出到工作树的字节是什么。
    ★这是 CAND-49 的核心:core.autocrlf 在 Windows 上默认 true,检出会变 CRLF。"""
    d = W / "repo"
    d.mkdir(exist_ok=True)
    git("init", "-q", cwd=d)
    git("config", "user.email", "p@x", cwd=d)
    git("config", "user.name", "p", cwd=d)
    f = d / "a.txt"
    with open(f, "wb") as fh:
        fh.write(b"one\ntwo\nthree\n")
    git("add", "a.txt", cwd=d)
    git("commit", "-qm", "x", cwd=d)
    blob = git("cat-file", "-p", "HEAD:a.txt", cwd=d)
    f.unlink()
    git("checkout", "--", "a.txt", cwd=d)
    raw = f.read_bytes()
    return f"工作树={raw!r} 仓库内换行数={blob.count(chr(10))}"


probe("G05_checkout_line_endings", git_checkout_bytes)


def git_filemode():
    """chmod +x 之后 git 认不认这个变化。★CAND-48:Windows 默认 core.fileMode=false,认不出来。"""
    d = W / "repo2"
    d.mkdir(exist_ok=True)
    git("init", "-q", cwd=d)
    git("config", "user.email", "p@x", cwd=d)
    git("config", "user.name", "p", cwd=d)
    f = d / "s.sh"
    f.write_text("#!/bin/sh\necho hi\n", encoding="utf-8", newline="")
    git("add", "s.sh", cwd=d)
    git("commit", "-qm", "x", cwd=d)
    mode_before = git("ls-files", "-s", "s.sh", cwd=d)
    try:
        os.chmod(f, 0o755)
    except OSError:
        pass
    st = git("status", "--porcelain", cwd=d)
    return f"入库模式={mode_before.split()[0] if mode_before else '?'} chmod后status={st!r}"


probe("G06_filemode_detects_chmod", git_filemode)

# ── CAND-43:tar 里的 UID / GID ─────────────────────────────────────────
def tar_owner():
    d = W / "t"
    d.mkdir(exist_ok=True)
    (d / "f.txt").write_text("x", encoding="utf-8", newline="")
    import tarfile
    tp = W / "o.tar"
    with tarfile.open(tp, "w") as tf:
        tf.add(str(d / "f.txt"), arcname="f.txt")
    with tarfile.open(tp) as tf:
        m = tf.getmember("f.txt")
        return f"uid={m.uid} gid={m.gid} uname={m.uname!r} gname={m.gname!r} mode={oct(m.mode)}"


probe("T01_tar_member_owner", tar_owner)
probe("T02_os_getuid", lambda: os.getuid() if hasattr(os, "getuid") else "<无 getuid>")

# ── CAND-54:硬链接快照语义 ─────────────────────────────────────────────
def hardlink_snapshot():
    a = W / "hl_a.txt"
    a.write_text("first", encoding="utf-8", newline="")
    b = W / "hl_b.txt"
    os.link(str(a), str(b))
    n1 = a.stat().st_nlink
    # 改原文件:硬链接应当一起变
    with open(a, "w", encoding="utf-8", newline="") as fh:
        fh.write("second")
    same = b.read_text(encoding="utf-8")
    # 用「先删后建」的方式改:硬链接应当保持旧内容
    a.unlink()
    with open(a, "w", encoding="utf-8", newline="") as fh:
        fh.write("third")
    after = b.read_text(encoding="utf-8")
    return f"nlink={n1} 就地改后B={same!r} 删建后B={after!r} A的nlink={a.stat().st_nlink}"


probe("H01_hardlink_semantics", hardlink_snapshot)


def copy_vs_link_ino():
    a = W / "ci_a.txt"
    a.write_text("x", encoding="utf-8", newline="")
    b = W / "ci_b.txt"
    os.link(str(a), str(b))
    c = W / "ci_c.txt"
    shutil.copy(str(a), str(c))
    sa, sb, sc = a.stat(), b.stat(), c.stat()
    return (f"link同ino={sa.st_ino == sb.st_ino and sa.st_ino != 0} "
            f"copy异ino={sa.st_ino != sc.st_ino} ino非零={sa.st_ino != 0} dev={sa.st_dev}")


probe("H02_copy_vs_link_identity", copy_vs_link_ino)

# ── CAND-13:设备号与 inode 的联合身份 ──────────────────────────────────
def ino_stability():
    p = W / "ino_x.txt"
    p.write_text("x", encoding="utf-8", newline="")
    before = p.stat().st_ino
    q = W / "ino_y.txt"
    p.rename(q)
    after = q.stat().st_ino
    return f"改名前={before} 改名后={after} 相等={before == after} 非零={before != 0}"


probe("I01_inode_stable_across_rename", ino_stability)


def ino_after_rewrite():
    p = W / "ino_z.txt"
    p.write_text("a", encoding="utf-8", newline="")
    b1 = p.stat().st_ino
    with open(p, "w", encoding="utf-8", newline="") as fh:
        fh.write("bb")
    b2 = p.stat().st_ino
    p.unlink()
    p.write_text("ccc", encoding="utf-8", newline="")
    b3 = p.stat().st_ino
    return f"就地重写同ino={b1 == b2} 删建后同ino={b1 == b3}"


probe("I02_inode_after_rewrite", ino_after_rewrite)

# ── CAND-12:目录符号链接的物化 ─────────────────────────────────────────
def dir_symlink():
    real = W / "realdir"
    real.mkdir(exist_ok=True)
    (real / "inner.txt").write_text("i", encoding="utf-8", newline="")
    link = W / "linkdir"
    try:
        os.symlink(str(real), str(link), target_is_directory=True)
    except OSError as e:
        return f"<建不了目录符号链接: {e.__class__.__name__} {str(e)[:60]}>"
    walked = []
    for root, dirs, files in os.walk(str(W)):
        for f in files:
            if f == "inner.txt":
                walked.append(os.path.relpath(os.path.join(root, f), str(W)))
    return (f"islink={os.path.islink(str(link))} isdir={os.path.isdir(str(link))} "
            f"walk命中={sorted(walked)}")


probe("L01_dir_symlink", dir_symlink)

# ── CAND-51:strftime 对低年份的填充 ────────────────────────────────────
def strftime_low_year():
    import datetime
    out = []
    for y in (1, 99, 875, 1900):
        try:
            d = datetime.date(y, 3, 4)
            out.append(f"{y}->{d.strftime('%Y-%m-%d')}")
        except Exception as e:
            out.append(f"{y}-><{type(e).__name__}>")
    return " ".join(out)


probe("S01_strftime_low_year", strftime_low_year)
probe("S02_strftime_pct_minus", lambda: __import__("datetime").date(2026, 3, 4).strftime("%-d/%-m") )

# ── CAND-30 / 52:NumPy 整数宽度与 longdouble ───────────────────────────
def numpy_info():
    try:
        import numpy as np
    except ImportError:
        return "<未装 numpy>"
    a = np.array([1, 2, 3])
    ld = np.finfo(np.longdouble)
    return (f"ver={np.__version__} 默认整型={a.dtype} itemsize={a.dtype.itemsize} "
            f"longdouble位数={ld.bits} 尾数={ld.nmant} eps={float(ld.eps):.3e}")


probe("N01_numpy", numpy_info)


def numpy_big_sum():
    try:
        import numpy as np
    except ImportError:
        return "<未装 numpy>"
    a = np.array([2**31 - 1] * 4)
    return f"dtype={a.dtype} sum={a.sum()} 溢出={int(a.sum()) != 4 * (2**31 - 1)}"


probe("N02_numpy_sum_overflow", numpy_big_sum)

# ── CAND-29:plain char 的有符号性 ──────────────────────────────────────
def char_signedness():
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        return "<无 C 编译器>"
    src = W / "c.c"
    src.write_text(
        "#include <stdio.h>\n"
        "int main(void){ char c = (char)200; printf(\"%d\\n\", (int)c); return 0; }\n",
        encoding="utf-8", newline="")
    exe = W / ("c.exe" if IS_WIN else "c.out")
    r = subprocess.run([cc, str(src), "-o", str(exe)], capture_output=True, timeout=180)
    if r.returncode != 0:
        return f"<编译失败 {(r.stderr or b'').decode('utf-8','replace')[:80]}>"
    p = subprocess.run([str(exe)], capture_output=True, timeout=60)
    v = p.stdout.decode("utf-8", "replace").strip()
    return f"编译器={os.path.basename(cc)} (char)200={v} ({'有符号' if v.startswith('-') else '无符号'})"


probe("C01_plain_char_signed", char_signedness)

print("== ENVSHIFT-PROBE4 ==")
for k, v in OUT:
    print(f"{k}\t{v}")
print("== END ==")
shutil.rmtree(W, ignore_errors=True)
