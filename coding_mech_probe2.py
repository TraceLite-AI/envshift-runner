#!/usr/bin/env python3
"""Coding 机制探针第二轮:路径按 / 切、句柄未关时的清理、Path 比较大小写、子进程输出换行、os.rename 覆盖、glob 大小写。"""
import json, os, pathlib, platform, subprocess, sys, tempfile, glob
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True); SYS = platform.system(); R = {"platform": platform.platform(), "checks": {}}
W = pathlib.Path(tempfile.mkdtemp(prefix="envshift-cprobe2-"))
def rec(k, v): R["checks"][k] = v; print(k, json.dumps(v, ensure_ascii=False)[:300], flush=True)
def safe(fn):
    try: return fn()
    except Exception as e: return "%s: %s" % (type(e).__name__, str(e)[:60])
# A 路径字符串按 / 切
p = W / "data" / "report.csv"; p.parent.mkdir(); p.write_text("x")
s = str(p); rec("A_split_slash", {"str_path": s[-22:], "basename_by_split": s.split("/")[-1][-22:], "os_basename": os.path.basename(s), "sep": os.sep, "join_slash_then_exists": os.path.exists("/".join([str(W), "data", "report.csv"]))})
# B 句柄未关时删除/改名(带 try/except 的清理)
q = W / "tmp.log"; q.write_text("log"); fh = open(q); fh.read(1)
r = {}
try: os.remove(q); r["remove_while_open"] = "ok"
except Exception as e: r["remove_while_open"] = type(e).__name__
try: os.rename(q if q.exists() else W / "none", W / "moved.log"); r["rename_while_open"] = "ok"
except Exception as e: r["rename_while_open"] = type(e).__name__
fh.close(); r["files_left"] = sorted(x.name for x in W.iterdir() if x.suffix == ".log"); rec("B_open_handle_cleanup", r)
# C Path 比较与去重
rec("C_path_equality", {"Path_eq_case": pathlib.Path("A.txt") == pathlib.Path("a.txt"), "set_len": len({pathlib.Path("A.txt"), pathlib.Path("a.txt")}), "PurePosix_eq": pathlib.PurePosixPath("A.txt") == pathlib.PurePosixPath("a.txt")})
# D 子进程输出换行
out = subprocess.run([sys.executable, "-c", "print('l1'); print('l2')"], capture_output=True).stdout
rec("D_subprocess_bytes", {"raw": repr(out), "split_n_last": repr(out.decode().split("\n")[0]), "text_mode": repr(subprocess.run([sys.executable, "-c", "print('l1')"], capture_output=True, text=True).stdout)})
# E os.rename 覆盖已存在目标
a = W / "a.txt"; b = W / "b.txt"; a.write_text("A"); b.write_text("B")
rec("E_rename_overwrite", {"os_rename": safe(lambda: (os.rename(a, b), "ok")[1]), "b_content_after": b.read_text() if b.exists() else None, "os_replace": safe(lambda: (os.replace(W / "a.txt", b) if (W / "a.txt").exists() else None, "ok")[1])})
# F glob / fnmatch 大小写
(W / "photo.JPG").write_text("1"); (W / "photo2.jpg").write_text("2")
rec("F_glob_case", {"glob_jpg": sorted(os.path.basename(x) for x in glob.glob(str(W / "*.jpg"))), "Path_glob_jpg": sorted(x.name for x in W.glob("*.jpg"))})
# G 文件名末尾空格/点 与 大小写共存
(W / "Readme.md").write_text("1"); r7 = safe(lambda: ((W / "readme.md").write_text("2"), sorted(x.name for x in W.iterdir() if x.name.lower() == "readme.md"))[1]); rec("G_case_coexist", {"after_write_lower": r7, "Readme_content": (W / "Readme.md").read_text()})
# H 默认编码
rec("H_default_encoding", {"preferred": __import__("locale").getpreferredencoding(False), "fs": sys.getfilesystemencoding(), "utf8_mode": sys.flags.utf8_mode, "LANG": os.environ.get("LANG"), "PYTHONUTF8": os.environ.get("PYTHONUTF8")})
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); print("CPROBE2-DONE", SYS, flush=True)
