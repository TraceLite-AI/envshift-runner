#!/usr/bin/env python3
"""OpenClaw 2026.9.4 Computer Use 三系统可行性探针(不跑题,不进成绩)。

问的问题只有一个:在 GitHub 托管 runner 上,OpenClaw 自带的 `computer` 工具(截图+键鼠)能不能起来?
步骤:写 openclaw.json(OpenAI 兼容 provider,tools.alsoAllow computer)→ 启用 cua-computer 插件 → doctor 校验驱动
     → 起 gateway(loopback token)→ 起 node host → 批准 device/node 配对 → 看 node 是否宣告 computer.act
     → 让模型用 computer 工具截一张图并描述。每一步原文打到 stdout,不做判断;判断人读日志。
用法: ENVSHIFT_API_KEY=<key> python3 oc_cu_probe.py <base_url> <model> <outdir>
"""
import json, os, pathlib, platform, shutil, socket, subprocess, sys, time

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

base, model, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3])
outdir.mkdir(parents=True, exist_ok=True)
key = os.environ.get("ENVSHIFT_API_KEY", "")
if not key:
    print("NO-API-KEY"); sys.exit(6)
home = outdir / "home"; st = outdir / "state"
for d in (home, st): d.mkdir(parents=True, exist_ok=True)
token = os.urandom(24).hex()
ws = outdir / "ws"; ws.mkdir(exist_ok=True)
cfg = {"models": {"providers": {"gw": {"baseUrl": base, "apiKey": key, "api": "openai-completions", "models": [{"id": model, "name": model}]}}},
       "agents": {"defaults": {"workspace": str(ws).replace("\\", "/"), "model": {"primary": f"gw/{model}"}, "models": {f"gw/{model}": {"alias": model}}}},
       "gateway": {"mode": "local", "bind": "loopback", "port": 18789, "auth": {"mode": "token", "token": token}},
       "tools": {"alsoAllow": ["computer"], "deny": ["web_search", "web_fetch", "browser"]}}
(st / "openclaw.json").write_text(json.dumps(cfg), encoding="utf-8")
env = dict(os.environ, HOME=str(home), USERPROFILE=str(home), OPENCLAW_STATE_DIR=str(st), OPENCLAW_CONFIG_PATH=str(st / "openclaw.json"),
           OPENCLAW_CONFIG=str(st / "openclaw.json"), OPENCLAW_WORKSPACE_DIR=str(ws), OPENCLAW_GATEWAY_TOKEN=token,
           OPENCLAW_EXEC_SHELL_SNAPSHOT="off", NO_PROXY="127.0.0.1,localhost", no_proxy="127.0.0.1,localhost")
env.pop("ENVSHIFT_API_KEY", None)

oc = None; node = shutil.which("node")
for r_ in subprocess.run(["npm", "root", "-g"], capture_output=True, text=True, shell=(os.name == "nt")).stdout.split():
    m = pathlib.Path(r_) / "openclaw" / "openclaw.mjs"
    if node and m.exists(): oc = [node, str(m)]; break
if oc is None:
    print("NO-OPENCLAW"); sys.exit(6)


def run(args, timeout=120, label=None):
    label = label or " ".join(args)
    try:
        r = subprocess.run(oc + args, capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, cwd=str(ws), timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as e:
        r = None; out = "TIMEOUT " + str(e)
    print(f"\n$ openclaw {label}\n  rc={getattr(r, 'returncode', 'T')}\n" + "\n".join("  | " + ln for ln in out.strip().splitlines()[-40:]))
    (outdir / (label.replace(" ", "_").replace("/", "_")[:60] + ".log")).write_text(out, encoding="utf-8")
    return out


print("PLATFORM", platform.platform(), "| DISPLAY", os.environ.get("DISPLAY"), "| oc", oc[1])
run(["--version"])
run(["plugins", "enable", "cua-computer"])
run(["plugins", "list"])
run(["doctor", "--lint", "--only", "cua-computer/driver-artifacts"], timeout=300)

gw = subprocess.Popen(oc + ["gateway", "run", "--bind", "loopback", "--port", "18789", "--auth", "token"],
                      stdout=open(outdir / "gateway.log", "w"), stderr=subprocess.STDOUT, env=env, cwd=str(ws))
ok = False
for _ in range(90):
    if gw.poll() is not None: break
    try: socket.create_connection(("127.0.0.1", 18789), timeout=1).close(); ok = True; break
    except OSError: time.sleep(1)
print("GATEWAY", "up" if ok else "NOT-READY")
if not ok:
    print(open(outdir / "gateway.log", errors="replace").read()[-1500:]); gw.kill(); sys.exit(3)

nd = subprocess.Popen(oc + ["node", "run", "--host", "127.0.0.1", "--port", "18789", "--display-name", "probe-node"],
                      stdout=open(outdir / "node.log", "w"), stderr=subprocess.STDOUT, env=env, cwd=str(ws))
time.sleep(15)
# 配对:device 请求 → 批准;node 命令面请求 → 批准(各试几轮,输出原文)
for i in range(4):
    run(["devices", "list"])
    run(["devices", "approve", "--latest"])
    p = run(["nodes", "pending"])
    for tok in p.replace(",", " ").split():
        if len(tok) >= 8 and tok.replace("-", "").isalnum() and any(c.isdigit() for c in tok) and tok.lower() not in ("pending",):
            pass
    run(["nodes", "pending", "--json"])
    time.sleep(8)
# 尝试从 --json 里拿 requestId 批准
pj = run(["nodes", "pending", "--json"])
try:
    data = json.loads(pj[pj.index("{"):]) if "{" in pj else json.loads(pj[pj.index("["):])
    reqs = []
    def walk(x):
        if isinstance(x, dict):
            if "requestId" in x: reqs.append(x["requestId"])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(data)
    for rid in reqs: run(["nodes", "approve", rid])
except Exception as e:
    print("nodes pending --json parse:", type(e).__name__, e)
time.sleep(5)
run(["nodes", "status"])
run(["nodes", "status", "--json"])
run(["nodes", "describe", "--node", "probe-node"])
# 最后:让模型自己用 computer 工具
prompt = ("You have a `computer` tool. Use it exactly once to take a screenshot of the desktop, then reply with one line: "
          "the screenshot width and height in pixels and the names of any windows you can see. Do not click or type anything.")
run(["agent", "--session-id", "cu-probe", "--message", prompt, "--thinking", "off", "--timeout", "300", "--json"], timeout=420, label="agent")
try:
    aj = (outdir / "agent.log").read_text(encoding="utf-8")
    print("AGENT-USED-COMPUTER-TOOL:", ("computer" in aj and ("screenshot" in aj or "frameId" in aj)))
except Exception: pass
print("\n---- node.log 尾部 ----"); print(open(outdir / "node.log", errors="replace").read()[-2500:])
print("\n---- gateway.log 尾部 ----"); print(open(outdir / "gateway.log", errors="replace").read()[-2500:])
for pr in (nd, gw):
    pr.kill()
if os.name == "nt":
    subprocess.run(["taskkill", "/F", "/IM", "node.exe"], capture_output=True)
try: (st / "openclaw.json").unlink()
except OSError: pass
print("PROBE-DONE")
