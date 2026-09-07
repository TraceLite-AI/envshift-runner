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
    q = urllib.request.quote(f'"{a.instance}"')
    u = f"https://datasets-server.huggingface.co/filter?dataset=SWE-bench/SWE-bench_Verified&config=default&split=test&where=instance_id={q}"
    row = json.load(urllib.request.urlopen(u, timeout=120))["rows"][0]["row"]
# ---- 官方构建器:改 ubuntu 版本(这是官方模板自带的参数),架构随宿主 ----
import swebench.harness.constants as C
for name in dir(C):
    v = getattr(C, name)
    if isinstance(v, dict) and v.get("ubuntu_version"):
        v["ubuntu_version"] = a.ubuntu; print(f"官方模板参数 {name}.ubuntu_version -> {a.ubuntu}")
from swebench.harness.test_spec.test_spec import make_test_spec
import docker
client = docker.from_env()
ts = make_test_spec(row, base_image_tag=a.tag, env_image_tag=a.tag, instance_image_tag=a.tag)
print("宿主架构:", platform.machine(), "| 官方 spec 架构:", ts.arch, ts.platform)
print("镜像名:", ts.base_image_key, "|", ts.env_image_key, "|", ts.instance_image_key)
from swebench.harness import docker_build as DB
import logging; logging.basicConfig(level=logging.INFO)
t0 = time.time()
# 官方三层构建:base → env → instance(用官方函数,按签名自适应)
def call(fn, **kw):
    sig = inspect.signature(fn); use = {k: v for k, v in kw.items() if k in sig.parameters}
    return fn(**use)
call(DB.build_base_images, client=client, dataset=[row], force_rebuild=False, tag=a.tag)
call(DB.build_env_images, client=client, dataset=[row], force_rebuild=False, max_workers=2, tag=a.tag)
logger = logging.getLogger("build")
call(DB.build_instance_image, test_spec=ts, client=client, logger=logger, nocache=False)
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
f2p = json.loads(row["FAIL_TO_PASS"]); p2p = json.loads(row["PASS_TO_PASS"])
fo = sum(status.get(x) == "PASSED" for x in f2p); po = sum(status.get(x) == "PASSED" for x in p2p)
res = int(fo == len(f2p) and po == len(p2p) and len(f2p) > 0)
print(f"RESULT {a.instance} arch={ts.arch} ubuntu={a.ubuntu} resolved={res} f2p={fo}/{len(f2p)} p2p={po}/{len(p2p)}")
pathlib.Path(f"rebuild_{ts.arch}_u{a.ubuntu}.json").write_text(json.dumps({"instance": a.instance, "arch": ts.arch, "ubuntu": a.ubuntu, "resolved": res, "f2p": f"{fo}/{len(f2p)}", "p2p": f"{po}/{len(p2p)}", "status": status, "build_s": int(time.time()-t0)}), encoding="utf-8")
