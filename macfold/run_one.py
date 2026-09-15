#!/usr/bin/env python3
"""EnvShift 实验仓执行器:在一台 runner 上跑一道题的一条臂,然后判分。

三阶段,与正式仓的执行器同构,但题目直接读仓库里的 tasks/,方便迭代:

  1. fixture  物化数据与「现成工具」。不施加任何格子环境,让本机的真实差异自己显现。
  2. arm      把 oracle / naive 的交付物放进 app 目录(agent 臂则让模型自己写)。
  3. verify   跑判据,输出一行机器可读的结果。

用法:
    python run_one.py --task <题名> --arm oracle|naive
    python run_one.py --task <题名> --arm oracle --data ./_data --app ./_app

输出(最后一行,固定格式,便于汇总):
    <题名> cell=<系统>-baseline arm=<臂> reward=<0|1> 诊断=<得分>/<总分> vrc=<判据退出码> s=<秒>
判据未满分时,把判据日志尾部打到 **stderr**(不是 stdout)。
★这一条是血的教训:工作流用 `| tail -1` 只留结果行,诊断信息走 stdout 会把结果行顶掉,
整轮门一会读起来像「朴素解一道都没翻」。
"""
import argparse
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
import time

for _st in (sys.stdout, sys.stderr):
    try:
        _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

HERE = pathlib.Path(__file__).resolve().parent

ap = argparse.ArgumentParser()
ap.add_argument("--task", required=True, help="tasks/ 下的目录名")
ap.add_argument("--arm", default="oracle", help="oracle / naive / null")
ap.add_argument("--data", default=None, help="数据根目录,默认 ./_data")
ap.add_argument("--app", default=None, help="工具落点,默认 ./_app")
ap.add_argument("--out", default=None, help="产物目录,默认 ./_out/<题>-<臂>")
ap.add_argument("--time-limit", type=int, default=300, help="判据里跑交付物的单次超时")
a = ap.parse_args()

td = HERE / "tasks" / a.task
if not td.is_dir():
    print(f"{a.task} 找不到题目录 {td}", file=sys.stderr)
    sys.exit(2)

spec_path = td / "task.json"
if not spec_path.exists():
    print(f"{a.task} 缺 task.json(必须声明 tool 与 venv)", file=sys.stderr)
    sys.exit(2)
spec = json.loads(spec_path.read_text(encoding="utf-8"))
binname = spec["tool"]
venv = spec["venv"]

data = pathlib.Path(a.data or (HERE / "_data")).resolve()
app = pathlib.Path(a.app or (HERE / "_app")).resolve()
out = pathlib.Path(a.out or (HERE / "_out" / f"{a.task}-{a.arm}")).resolve()
for p in (data, app, out):
    p.mkdir(parents=True, exist_ok=True)


def wipe(p):
    def onerr(fn, path, exc):
        try:
            os.chmod(path, stat.S_IWRITE)
            fn(path)
        except Exception:
            pass
    for c in list(p.iterdir()):
        if c.is_dir():
            shutil.rmtree(c, onerror=onerr)
        else:
            try:
                c.unlink()
            except OSError:
                pass


wipe(data)
wipe(app)
t0 = time.time()

# ── 1. fixture ─────────────────────────────────────────────────────────
# ★fixture 与判据是「装置」,它们的 stdout 钉成 UTF-8,免得自己的中文 print 在 Windows 上
# 被 cp1252 卡死(实验仓故意不全局设 PYTHONUTF8,那会抹平默认编码类机制)。
# 注意:PYTHONIOENCODING 只影响这两个装置进程,**不传给被测工具** —— 判据自己 spawn 交付物时
# 用的是它自己的环境,那一层的默认编码必须保持本机真实值,否则测不出东西。
_dev_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}

r = subprocess.run([sys.executable, str(td / "mkfixture.py"), str(data)],
                   capture_output=True, text=True, encoding="utf-8", errors="replace",
                   env={**_dev_env, f"{venv}_APP": str(app)}, timeout=600)
(out / "fixture.log").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")
if r.returncode != 0:
    print(f"{a.task} cell=? arm={a.arm} FIXTURE-FAIL", file=sys.stderr)
    for ln in ((r.stderr or "").strip().splitlines() or ["(无 stderr)"])[-8:]:
        print("  FIXTURE " + ln[:200], file=sys.stderr)
    sys.exit(4)

# ── 2. 臂 ──────────────────────────────────────────────────────────────
if a.arm not in ("null", "agent"):
    src = td / "arms" / a.arm / binname
    if not src.exists():
        print(f"{a.task} 没有 {a.arm} 臂的 {binname}", file=sys.stderr)
        sys.exit(2)
    shutil.copy(str(src), str(app / binname))
    try:
        b = app / binname
        b.chmod(b.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    except OSError:
        pass

# ── 3. 判据 ────────────────────────────────────────────────────────────
t1 = time.time()
logdir = out / "verifier-log"
if logdir.exists():
    shutil.rmtree(logdir, ignore_errors=True)
logdir.mkdir(parents=True, exist_ok=True)

env = dict(_dev_env, **{
    f"{venv}_LOG": str(logdir),
    f"{venv}_BIN": str(app / binname),
    f"{venv}_ROOT": str(data),
    f"{venv}_TIME_LIMIT": str(a.time_limit),
})
r = subprocess.run([sys.executable, str(td / "verifier" / "check.py")],
                   env=env, capture_output=True, text=True, encoding="utf-8", errors="replace",
                   timeout=1800)
(out / "verifier.log").write_text((r.stdout or "") + (r.stderr or ""), encoding="utf-8")

reward = (logdir / "reward.txt").read_text(encoding="utf-8").strip() if (logdir / "reward.txt").exists() else "?"
tr = json.loads((logdir / "trace_results.json").read_text(encoding="utf-8")) if (logdir / "trace_results.json").exists() else {}
cell = os.environ.get("XOS_CELL", "local")
line = (f"{a.task} cell={cell}-baseline arm={a.arm} reward={reward} "
        f"诊断={tr.get('points', '?')}/{tr.get('total', '?')} vrc={r.returncode} s={int(time.time() - t1)}")

if reward != "1":
    # ★诊断走 stderr:工作流用 tail -1 只留结果行。
    # 打「未通过项的完整 detail」而不是日志末尾几行——detail 里才有首个分歧位置这类定位信息,
    # 之前只打末 8 行,恰好把它截掉了,排查时只能看到「不一致」三个字。
    for c in (tr.get("checks") or []):
        if not c.get("passed"):
            print("  VERIFIER-FAIL %s | %s" % (c.get("name"), c.get("detail", ""))[:600], file=sys.stderr)
    if not tr.get("checks"):
        for ln in ((r.stdout or "") + (r.stderr or "")).strip().splitlines()[-8:]:
            print("  VERIFIER " + ln[:220], file=sys.stderr)

print(line)
(out / "meta.json").write_text(json.dumps({"line": line, "reward": reward, "trace": tr},
                                          ensure_ascii=False, indent=2), encoding="utf-8")
