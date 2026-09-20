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

base, model, outdir = sys.argv[1], sys.argv[2], pathlib.Path(sys.argv[3]).resolve()   # ★必须绝对路径:gateway 的 cwd 是 ws,相对的 OPENCLAW_CONFIG_PATH 解析不到 → "Missing config"(v2 探针三系统全倒在这)
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
       "tools": {"alsoAllow": ["computer"], "deny": ["web_search", "web_fetch", "browser"]},
       # 直接在配置里启用插件:`openclaw plugins enable` 会改写配置文件,第一版探针里改写后 gateway 报 "missing gateway.mode" 起不来
       "plugins": {"entries": {"cua-computer": {"enabled": True}}}}
cfg["agents"]["defaults"]["skipBootstrap"] = True   # 关掉首次运行的"给我起名"bootstrap 回合
(st / "openclaw.json").write_text(json.dumps(cfg), encoding="utf-8")
def rewrite_cfg():
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
run(["plugins", "list"])
run(["doctor", "--lint"], timeout=300)   # 文档里的 --only cua-computer/driver-artifacts 在 2026.9.4 报 Unknown health check id,改跑全量 lint 看输出
print("config after CLI calls has gateway.mode:", "gateway" in json.loads((st / "openclaw.json").read_text()) and "mode" in json.loads((st / "openclaw.json").read_text())["gateway"])
rewrite_cfg()

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
# 配对:device 请求 → 批准;node 命令面请求 → 批准。requestId 从 CLI 文本里正则抠("Run openclaw nodes approve <uuid>"),
#      `nodes pending --json` 输出后面带非 JSON 尾巴,直接 json.loads 会失败(本机坐实)。
import re
approved = set()
for i in range(6):
    txt = run(["devices", "list"]) + run(["nodes", "pending"]) + run(["nodes", "status"])
    run(["devices", "approve", "--latest"])
    for rid in set(re.findall(r"nodes approve ([0-9a-f-]{36})", txt)) - approved:
        run(["nodes", "approve", rid]); approved.add(rid)
    if approved and "pending" not in run(["nodes", "status"]).lower():
        break
    time.sleep(6)
# v3 结论:Linux/Windows 的 node 已宣告 computer.act + screen.snapshot,但 agent 说自己工具集里没有 computer——
#   批准后 node 要重连、gateway 才把能力算进工具目录;agent 起得太早。等一等,再直接用 CLI 调一次 screen.snapshot 验驱动。
time.sleep(45)
run(["nodes", "status"])
run(["nodes", "describe", "--node", "probe-node"])
run(["nodes", "invoke", "--node", "probe-node", "--command", "screen.snapshot", "--params", "{}"], timeout=120, label="nodes invoke screen.snapshot")
# 最后:让模型自己用 computer 工具
prompt = ("You have a `computer` tool. Use it exactly once to take a screenshot of the desktop, then reply with one line: "
          "the screenshot width and height in pixels and the names of any windows you can see. Do not click or type anything.")
out = run(["agent", "--session-id", "cu-probe", "--message", prompt, "--thinking", "off", "--timeout", "300", "--json"], timeout=420, label="agent")
if "frameId" not in out and "width" not in out.lower():
    print("first agent attempt saw no computer tool; waiting 60s and retrying in a fresh session")
    time.sleep(60); run(["nodes", "describe", "--node", "probe-node"])
    run(["agent", "--session-id", "cu-probe-2", "--message", prompt, "--thinking", "off", "--timeout", "300", "--json"], timeout=420, label="agent2")
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
