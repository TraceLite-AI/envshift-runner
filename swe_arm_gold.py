#!/usr/bin/env python3
"""在 arm64 runner 上直接用 SWE-bench 官方 arm64 镜像跑 gold 补丁 + 官方 eval_script + 官方 parser。
   用法: swe_arm_gold.py <instance_id> [arm64|x86_64]
   数据从 HF 拉该实例的一行(不进仓库)。"""
import json, os, subprocess, sys, tempfile, pathlib, urllib.request
iid = sys.argv[1]; arch = sys.argv[2] if len(sys.argv) > 2 else "arm64"
def sh(c, **k): return subprocess.run(c, shell=True, capture_output=True, text=True, **k)
# 取该实例数据(HF datasets-server 行查询)
q = urllib.request.quote(f'"{iid}"')
u = f"https://datasets-server.huggingface.co/filter?dataset=SWE-bench/SWE-bench_Verified&config=default&split=test&where=instance_id={q}"
row = json.load(urllib.request.urlopen(u, timeout=120))["rows"][0]["row"]
img = f"swebench/sweb.eval.{arch}.{iid.replace('__', '_1776_')}:latest"
print("镜像:", img)
p = sh(f"docker pull -q {img}")
if p.returncode != 0: print("PULL-FAIL", p.stderr.strip()[:200]); sys.exit(3)
c = f"swe-{arch}-{os.getpid()}"
sh(f"docker run -d --name {c} {img} sleep 3600")
print("容器架构:", sh(f"docker exec {c} uname -m").stdout.strip())
t = pathlib.Path(tempfile.mkdtemp())
(t / "patch.diff").write_text(row["patch"], encoding="utf-8"); (t / "eval.sh").write_text(row["eval_script"], encoding="utf-8")
sh(f"docker cp {t}/patch.diff {c}:/tmp/patch.diff"); sh(f"docker cp {t}/eval.sh {c}:/eval.sh")
g = sh(f"docker exec {c} sh -c 'cd /testbed && git apply -v /tmp/patch.diff'")
if g.returncode != 0: print("GOLD-APPLY-FAIL", g.stderr[-200:]); sys.exit(4)
e = sh(f"docker exec {c} bash /eval.sh", timeout=3000); log = e.stdout + e.stderr
sh(f"docker rm -f {c}")
import importlib
LP = importlib.import_module("swebench.harness.log_parsers")
parser = getattr(LP, row["log_parser"])
try: status = parser(log, row)
except TypeError: status = parser(log)
f2p = json.loads(row["FAIL_TO_PASS"]); p2p = json.loads(row["PASS_TO_PASS"])
fo = sum(status.get(x) == "PASSED" for x in f2p); po = sum(status.get(x) == "PASSED" for x in p2p)
res = int(fo == len(f2p) and po == len(p2p) and len(f2p) > 0)
print(f"RESULT {iid} arch={arch} resolved={res} f2p={fo}/{len(f2p)} p2p={po}/{len(p2p)}")
json.dump({"instance_id": iid, "arch": arch, "resolved": res, "status": status}, open(f"result_{arch}.json", "w"))
