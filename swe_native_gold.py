#!/usr/bin/env python3
"""macOS / Windows 上原生跑 SWE-bench 实例(无 Docker):
   用官方 v4.0.4 的 make_test_spec 拿到官方三段脚本(setup_env / install_repo / eval),只把路径从
   /testbed、/opt/miniconda3 换成本机路径,其余一字不改;gold 补丁 + 官方 parser 判分。
   用法: swe_native_gold.py <instance_id> [--arm gold|null]"""
import argparse, json, os, pathlib, platform, re, shutil, subprocess, sys, tempfile, time, urllib.request
for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")   # Windows 控制台 cp1252 印中文会崩(老坑)
    except Exception: pass
ap = argparse.ArgumentParser(); ap.add_argument("instance"); ap.add_argument("--arm", default="gold"); a = ap.parse_args()
HOME = pathlib.Path.home(); TB = HOME / "testbed"; CONDA = pathlib.Path(os.environ.get("CONDA", "")) if os.environ.get("CONDA") else HOME / "miniconda3"
def _bash():
    # Windows 上裸 `bash` 会解析到 WSL 启动器(没装发行版就报错);必须显式用 Git Bash(跨 OS 那轮的老坑)
    if os.name == "nt":
        for c in (r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files\Git\usr\bin\bash.exe"):
            if pathlib.Path(c).exists(): return c
    return "bash"
def sh(c, **k): return subprocess.run([_bash(), "-lc", c], capture_output=True, text=True, **k)
import pyarrow.parquet as pq
pqp = pathlib.Path(tempfile.gettempdir()) / "swe_verified.parquet"
if not pqp.exists(): urllib.request.urlretrieve("https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet", pqp)
row = next((r for r in pq.read_table(pqp).to_pylist() if r["instance_id"] == a.instance), None)
if row is None: raise SystemExit("没有这道题")
if os.name == "nt":
    # 官方 swebench 包自己 import resource(Unix 专有),Windows 上连导入都过不去;塞一个空垫片,不改任何任务/判分逻辑
    import types; _r = types.ModuleType("resource"); _r.getrlimit = lambda *a, **k: (0, 0); _r.setrlimit = lambda *a, **k: None; _r.RLIMIT_NOFILE = 7; sys.modules["resource"] = _r
from swebench.harness.test_spec.test_spec import make_test_spec
ts = make_test_spec(row)
def adapt(script):
    s = script.replace("/testbed", str(TB).replace("\\", "/")).replace("/opt/miniconda3", str(CONDA).replace("\\", "/"))
    s = s.replace("source /root/.bashrc", ":")
    return s
print("平台:", platform.platform(), platform.machine(), "| conda:", CONDA, "| python 规格:", re.search(r"python=([\d.]+)", ts.setup_env_script or "").group(1) if re.search(r"python=([\d.]+)", ts.setup_env_script or "") else "?")
t0 = time.time()
# 1) 官方 env 脚本(conda create + 依赖)
r = sh(adapt(ts.setup_env_script)); (pathlib.Path("native_setup_env.log")).write_text(r.stdout + r.stderr, encoding="utf-8")
if r.returncode != 0:
    print("ENV-FAIL rc", r.returncode, "|", (r.stdout + r.stderr)[-400:].replace("\n", " ")); sys.exit(4)
print("env 建好 %ds" % (time.time() - t0))
# 2) 官方 repo 脚本(clone + checkout base_commit + install)
if TB.exists(): shutil.rmtree(TB, ignore_errors=True)
r = sh(adapt(ts.install_repo_script)); (pathlib.Path("native_install_repo.log")).write_text(r.stdout + r.stderr, encoding="utf-8")
if r.returncode != 0:
    print("REPO-FAIL rc", r.returncode, "|", (r.stdout + r.stderr)[-400:].replace("\n", " ")); sys.exit(4)
print("repo 装好 %ds" % (time.time() - t0))
# 3) 臂
if a.arm == "gold":
    (TB / ".gold.diff").write_text(row["patch"], encoding="utf-8")
    g = sh(f"cd '{TB}' && git apply -v .gold.diff")
    if g.returncode != 0: print("GOLD-APPLY-FAIL", g.stderr[-300:]); sys.exit(4)
# 4) 官方 eval 脚本(改路径不改逻辑)
e = sh(adapt(row["eval_script"]), timeout=3000); log = e.stdout + e.stderr
pathlib.Path("native_eval.log").write_text(log, encoding="utf-8")
import importlib; LP = importlib.import_module("swebench.harness.log_parsers")
parser = getattr(LP, row["log_parser"], None) or LP.MAP_REPO_TO_PARSER[row["repo"]]
try: status = parser(log, row)
except TypeError: status = parser(log)
L = lambda v: json.loads(v) if isinstance(v, str) else list(v)
f2p, p2p = L(row["FAIL_TO_PASS"]), L(row["PASS_TO_PASS"])
fo = sum(status.get(x) == "PASSED" for x in f2p); po = sum(status.get(x) == "PASSED" for x in p2p)
res = int(fo == len(f2p) and po == len(p2p) and len(f2p) > 0)
print(f"RESULT {a.instance} arm={a.arm} platform={platform.system()}-{platform.machine()} resolved={res} f2p={fo}/{len(f2p)} p2p={po}/{len(p2p)} total_s={int(time.time()-t0)}")
pathlib.Path(f"native_{platform.system()}_{platform.machine()}.json").write_text(json.dumps({"instance": a.instance, "arm": a.arm, "platform": platform.platform(), "resolved": res, "f2p": f"{fo}/{len(f2p)}", "p2p": f"{po}/{len(p2p)}", "status": status}), encoding="utf-8")
