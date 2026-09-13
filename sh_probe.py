#!/usr/bin/env python3
"""量 Windows 上「判据怎么启动一个 shell 交付物」才行得通。

M4/X5 的判据现在用 ["bash", BIN, ROOT] 启动,在 Windows 上参考解也只拿 10 分,
说明这一路根本没跑起来。逐个试可能的启动方式,把每种的退出码与输出打出来。
"""
import os, pathlib, shutil, subprocess, sys, tempfile

for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

W = pathlib.Path(tempfile.mkdtemp(prefix="shprobe_"))
(W / "store").mkdir()
(W / "store" / "batch1.csv").write_text("tag,name\ngrp-east,Alice\ngrp-west,bob\n", encoding="utf-8", newline="")
script = W / "export.sh"
script.write_text('''#!/bin/sh
ROOT="$1"
cat "$ROOT"/store/*.csv | grep -v '^tag,name$' | cut -d, -f2 | LC_ALL=C sort -u
''', encoding="utf-8", newline="")
try:
    os.chmod(script, 0o755)
except OSError:
    pass

def posix(p):
    p = str(p).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return p

BASH = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.EXE"
SH = shutil.which("sh") or r"C:\Program Files\Git\usr\bin\sh.EXE"
print("bash =", BASH)
print("sh   =", SH)
print("脚本 =", script)
print("数据 =", W)

TRIES = [
    ("bash 原样路径",      [BASH, str(script), str(W)]),
    ("bash posix 路径",    [BASH, posix(script), posix(W)]),
    ("bash 脚本posix/数据原样", [BASH, posix(script), str(W)]),
    ("sh 原样路径",        [SH, str(script), str(W)]),
    ("sh posix 路径",      [SH, posix(script), posix(W)]),
    ("直接执行(无解释器)",  [str(script), str(W)]),
    ("bash -c 串",         [BASH, "-c", f'"{posix(script)}" "{posix(W)}"']),
]
for name, cmd in TRIES:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=60)
        out = p.stdout.decode("utf-8", "replace").strip().replace("\n", "|")
        err = p.stderr.decode("utf-8", "replace").strip().replace("\n", "|")
        print(f"[{name}] rc={p.returncode} out={out[:70]!r} err={err[:90]!r}")
    except Exception as e:
        print(f"[{name}] 启动失败 {type(e).__name__}: {str(e)[:90]}")
shutil.rmtree(W, ignore_errors=True)
