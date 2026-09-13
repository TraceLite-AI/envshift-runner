#!/usr/bin/env python3
"""直接在 Windows 上跑真题 X83 的完整三阶段,把每一步的实况打出来。

前两轮探针都用自造脚本,五种启动方式全 rc=0,于是排除了启动方式;
但真门一里 X83 的两臂都挂在第一条判据。差别只可能在「真题的脚本是怎么落到盘上的」,
所以这轮直接调用真题自己的 fixture 与 arm 文件,不再自造。
"""
import io, json, os, pathlib, shutil, subprocess, sys, tarfile, tempfile

for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

TASK = "X83-archive-m22"
BINNAME = "rollcall.sh"
VENV = "X83"
here = pathlib.Path(__file__).resolve().parent
td = here / "tasks" / TASK
print("题目录存在:", td.exists())
if not td.exists():
    print("★题包没还原出来,先看 tasks/ 下有什么:", [p.name for p in (here / "tasks").glob("X8*")][:6])
    sys.exit(1)

W = pathlib.Path(tempfile.mkdtemp(prefix="p3_"))
data, app = W / "data", W / "app"
data.mkdir(); app.mkdir()

r = subprocess.run([sys.executable, str(td / "mkfixture.py"), str(data)],
                   capture_output=True, text=True, env={**os.environ, f"{VENV}_APP": str(app)})
print("fixture rc =", r.returncode, "|", (r.stdout or r.stderr).strip()[:120])
print("app 目录:", [p.name for p in app.iterdir()])
print("data 目录:", [p.name for p in data.iterdir()])

tool = app / BINNAME
if tool.exists():
    raw = tool.read_bytes()
    print(f"fixture 写的现成工具: {len(raw)} 字节, 含CR={b'@@CR@@'.replace(b'@@CR@@', bytes([13])) in raw}")
    print("  首 80 字节:", raw[:80])

for arm in ("oracle", "naive"):
    src = td / "arms" / arm / BINNAME
    shutil.copy(src, tool)
    raw = tool.read_bytes()
    has_cr = bytes([13]) in raw
    print(f"--- {arm}: {len(raw)} 字节, 含CR={has_cr}")
    print("   首 60 字节:", raw[:60])
    exe = "bash" if os.name == "nt" else "sh"
    p = subprocess.run([exe, str(tool), str(data)], capture_output=True, timeout=120)
    print(f"   {exe} 直跑 rc={p.returncode}")
    print("     stdout=", p.stdout.decode('utf-8', 'replace').strip().replace(chr(10), '|')[:100])
    print("     stderr=", p.stderr.decode('utf-8', 'replace').strip().replace(chr(10), '|')[:220])
    # 再按判据的方式跑一次
    env = {**os.environ, f"{VENV}_ROOT": str(data), f"{VENV}_BIN": str(tool), f"{VENV}_LOG": str(W / "logs")}
    v = subprocess.run([sys.executable, str(td / "verifier" / "check.py")], capture_output=True, text=True, env=env)
    print("   判据 rc=", v.returncode, "|", (v.stdout or "").strip().replace(chr(10), " | ")[:200])

shutil.rmtree(W, ignore_errors=True)
