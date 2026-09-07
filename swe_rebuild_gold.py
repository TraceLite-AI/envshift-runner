#!/usr/bin/env python3
"""用 SWE-bench 官方 v4.0.4 构建器重建一道题的环境(可改 ubuntu 版本;架构随宿主),然后 gold 补丁 + 官方 eval_script + 官方 parser。
   用法: swe_rebuild_gold.py <instance_id> <ubuntu_version> <tag> [--jsonl path]
   目的:实测"在别的 OS/架构上重建"到底难不难 —— 官方解在重建环境里过不过,就是闸门。"""
import argparse, inspect, json, os, platform, subprocess, sys, tempfile, pathlib, time, urllib.request
ap = argparse.ArgumentParser(); ap.add_argument("instance"); ap.add_argument("ubuntu"); ap.add_argument("tag"); ap.add_argument("--jsonl", default="")
a = ap.parse_args()
def sh(c, **k): return subprocess.run(c, shell=True, capture_output=True, text=True, **k)
# ---- 取实例 ----
if a.jsonl:
    row = next(json.loads(l) for l in open(a.jsonl, encoding="utf-8") if json.loads(l)["instance_id"] == a.instance)
else:
    import pyarrow.parquet as pq
    pq_path = pathlib.Path(tempfile.gettempdir()) / "swe_verified.parquet"
    if not pq_path.exists():
        urllib.request.urlretrieve("https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified/resolve/main/data/test-00000-of-00001.parquet", pq_path)
    row = next((r for r in pq.read_table(pq_path).to_pylist() if r["instance_id"] == a.instance), None)
    if row is None: raise SystemExit(f"没有这道题: {a.instance}")
# ---- 官方构建器:改 ubuntu 版本(这是官方模板自带的参数),架构随宿主 ----
import swebench.harness.constants as C
for name in dir(C):
    v = getattr(C, name)
    if isinstance(v, dict) and v.get("ubuntu_version"):
        v["ubuntu_version"] = a.ubuntu; print(f"官方模板参数 {name}.ubuntu_version -> {a.ubuntu}")
from swebench.harness.test_spec.test_spec import make_test_spec
import docker
client = docker.from_env()
# 官方一体化构建:base → env → instance。base/env 用官方默认 tag(镜像名本身含架构),instance 用本次 tag。
# ★同一架构上换 ubuntu 版本会覆盖同名 base/env 镜像,所以 force_rebuild=True,并在结果里记录 ubuntu 版本。
ts = make_test_spec(row, instance_image_tag=a.tag)
print("宿主架构:", platform.machine(), "| 官方 spec 架构:", ts.arch, ts.platform)
print("镜像名:", ts.base_image_key, "|", ts.env_image_key, "|", ts.instance_image_key)
from swebench.harness import docker_build as DB
import logging; logging.basicConfig(level=logging.WARNING)
t0 = time.time()
DB.build_instance_images(client=client, dataset=[row], force_rebuild=os.environ.get("FORCE_REBUILD", "0") == "1", max_workers=2, namespace=None, tag=a.tag)
print("构建耗时 %ds" % (time.time() - t0))
img = ts.instance_image_key
# ---- gold + 官方 eval ----
c = f"swe-rebuild-{os.getpid()}"
sh(f"docker rm -f {c}"); sh(f"docker run -d --name {c} {img} sleep 3600")
print("容器内:", sh(f"docker exec {c} sh -c 'uname -m; . /etc/os-release; echo $PRETTY_NAME'").stdout.strip().replace("\n", " | "))
t = pathlib.Path(tempfile.mkdtemp())
(t / "patch.diff").write_text(row["patch"], encoding="utf-8"); (t / "eval.sh").write_text(row["eval_script"], encoding="utf-8")
sh(f"docker cp {t}/patch.diff {c}:/tmp/patch.diff"); sh(f"docker cp {t}/eval.sh {c}:/eval.sh")
g = sh(f"docker exec {c} sh -c 'cd /testbed && git apply -v /tmp/patch.diff'")
if g.returncode != 0: print("GOLD-APPLY-FAIL", g.stderr[-300:]); sh(f"docker rm -f {c}"); sys.exit(4)
e = sh(f"docker exec {c} bash /eval.sh", timeout=3000); log = e.stdout + e.stderr
sh(f"docker rm -f {c}")
import importlib
LP = importlib.import_module("swebench.harness.log_parsers"); parser = getattr(LP, row["log_parser"], None)
if parser is None:
    from swebench.harness.log_parsers import MAP_REPO_TO_PARSER
    parser = MAP_REPO_TO_PARSER[row["repo"]]
try: status = parser(log, row)
except TypeError: status = parser(log)
L = lambda v: json.loads(v) if isinstance(v, str) else list(v)   # parquet 里已是列表,jsonl 里是字符串
f2p = L(row["FAIL_TO_PASS"]); p2p = L(row["PASS_TO_PASS"])
fo = sum(status.get(x) == "PASSED" for x in f2p); po = sum(status.get(x) == "PASSED" for x in p2p)
res = int(fo == len(f2p) and po == len(p2p) and len(f2p) > 0)
print(f"RESULT {a.instance} arch={ts.arch} ubuntu={a.ubuntu} resolved={res} f2p={fo}/{len(f2p)} p2p={po}/{len(p2p)}")
pathlib.Path(f"rebuild_{ts.arch}_u{a.ubuntu}.json").write_text(json.dumps({"instance": a.instance, "arch": ts.arch, "ubuntu": a.ubuntu, "resolved": res, "f2p": f"{fo}/{len(f2p)}", "p2p": f"{po}/{len(p2p)}", "status": status, "build_s": int(time.time()-t0)}), encoding="utf-8")
