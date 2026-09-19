#!/usr/bin/env python3
"""探针:Windows 向候选机制(默认编码 / mtime 精度 / 尾点写入 / 保留名)与 Linux 向(大小写敏感 / 反斜杠名)在三台真机上的真实行为。"""
import json, locale, os, pathlib, shutil, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
OUT = {"platform": sys.platform, "PYTHONUTF8": os.environ.get("PYTHONUTF8"), "preferred_encoding": locale.getpreferredencoding(False), "utf8_mode": sys.flags.utf8_mode}
d = pathlib.Path(tempfile.mkdtemp(prefix="wl_"))
r = {}
# A 默认编码
p = d / "u.txt"; p.write_bytes("café 中".encode("utf-8"))
try:
    with open(p) as fh: r["A_open_默认编码读UTF8"] = {"读到": fh.read(), "撒谎": fh.read() != "" or True}
except Exception as e: r["A_open_默认编码读UTF8"] = {"error": type(e).__name__}
r["A_open_默认编码读UTF8"]["撒谎"] = r["A_open_默认编码读UTF8"].get("读到") not in (None, "café 中") and "error" not in r["A_open_默认编码读UTF8"]
# A2 默认编码写
try:
    q = d / "w.txt"
    with open(q, "w") as fh: fh.write("café")
    r["A2_open_默认编码写"] = {"字节": q.read_bytes().hex(), "撒谎": q.read_bytes() != "café".encode("utf-8")}
except Exception as e: r["A2_open_默认编码写"] = {"error": type(e).__name__}
# B mtime 精度:copy2 后 ns 是否相等
src = d / "s.bin"; src.write_bytes(b"x"); os.utime(src, ns=(1_700_000_000_123_456_789, 1_700_000_000_123_456_789))
dst = d / "t.bin"; shutil.copy2(src, dst)
r["B_copy2_mtime_ns"] = {"源": src.stat().st_mtime_ns, "副本": dst.stat().st_mtime_ns, "float相等": src.stat().st_mtime == dst.stat().st_mtime, "撒谎": src.stat().st_mtime_ns != dst.stat().st_mtime_ns}
# B2 utime 设的 ns 读回
r["B2_utime_ns_读回"] = {"设": 1_700_000_000_123_456_789, "读": src.stat().st_mtime_ns, "撒谎": src.stat().st_mtime_ns != 1_700_000_000_123_456_789}
# C 尾点写入
(d / "notes").write_bytes(b"ORIG")
try:
    (d / "notes.").write_bytes(b"DOT")
    r["C_写尾点名"] = {"目录": sorted(os.listdir(d)), "notes内容": (d / "notes").read_bytes().decode(), "撒谎": (d / "notes").read_bytes() == b"DOT"}
except Exception as e: r["C_写尾点名"] = {"error": type(e).__name__}
# D 保留名
for nm in ("nul.txt", "con.log", "aux", "com1.csv"):
    try:
        (d / nm).write_bytes(b"R"); r["D_" + nm] = {"exists": (d / nm).exists(), "在目录里": nm in os.listdir(d), "撒谎": (d / nm).exists() and nm not in os.listdir(d)}
    except Exception as e: r["D_" + nm] = {"error": type(e).__name__}
# E 大小写:按错大小写找
(d / "Readme.md").write_bytes(b"R")
r["E_大小写错名exists"] = {"readme.md exists": (d / "readme.md").exists(), "README.MD exists": (d / "README.MD").exists()}
# F 反斜杠名
try:
    (d / "sub").mkdir(); (d / "sub" / "a.txt").write_bytes(b"A")
    r["F_反斜杠路径"] = {"'sub\\\\a.txt' exists": (d / "sub\\a.txt").exists(), "顶层目录": sorted(os.listdir(d))[:8]}
except Exception as e: r["F_反斜杠路径"] = {"error": type(e).__name__}
OUT.update(r); shutil.rmtree(d, ignore_errors=True)
print("WINLINPROBE " + json.dumps(OUT, ensure_ascii=False, default=str))
