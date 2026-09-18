#!/usr/bin/env python3
"""探针:Chrome 文本框里,Windows/Linux 的键盘习惯在 macOS 上是不是静默地做了别的事。
每项:用 CDP 预置字段值并聚焦,再用 pyautogui 按真实键,最后用 CDP 读回值。输出一行 JSON。
"""
import json, os, pathlib, platform, shutil, subprocess, sys, tempfile, time, urllib.request
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import websocket, pyautogui
pyautogui.FAILSAFE = False
HTML = """<!doctype html><html><body style="font:16px sans-serif;margin:40px">
<p>a <input id=a size=40></p><p>b <input id=b size=40></p>
<p>t <textarea id=t rows=6 cols=50></textarea></p></body></html>"""
temp = pathlib.Path(tempfile.mkdtemp(prefix="macgui-"))
page = temp / "p.html"; page.write_text(HTML, encoding="utf-8")
url = page.as_uri()
if sys.platform == "darwin": chrome = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
elif os.name == "nt": chrome = next(p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"] if pathlib.Path(p).exists())
else: chrome = shutil.which("google-chrome") or shutil.which("google-chrome-stable")
cmd = [chrome, "--user-data-dir=" + str(temp / "profile"), "--remote-debugging-port=0", "--remote-allow-origins=*", "--no-first-run",
       "--no-default-browser-check", "--disable-features=Translate", "--lang=en-US", "--window-position=0,0", "--window-size=1000,700", url]
if sys.platform.startswith("linux"): cmd += ["--no-sandbox", "--disable-dev-shm-usage"]
proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
for _ in range(60):
    try:
        port = int((temp / "profile/DevToolsActivePort").read_text().splitlines()[0])
        with urllib.request.urlopen("http://127.0.0.1:%d/json" % port, timeout=3) as r: tabs = json.load(r)
        target = next(t for t in tabs if t.get("url", "").startswith("file://")); break
    except Exception: time.sleep(1)
else: raise SystemExit("Chrome did not start")
ws = websocket.create_connection(target["webSocketDebuggerUrl"], timeout=10); rid = 0
def cdp(method, params=None):
    global rid
    rid += 1; ws.send(json.dumps({"id": rid, "method": method, "params": params or {}}))
    while True:
        r = json.loads(ws.recv())
        if r.get("id") == rid: return r.get("result", {})
def ev(code): return cdp("Runtime.evaluate", {"expression": code, "returnByValue": True}).get("result", {}).get("value")
cdp("Page.bringToFront"); time.sleep(1.5)
def setup(field, value, caret="end"):
    ev("(()=>{const e=document.getElementById(%r);e.value=%s;e.focus();const n=%s;e.setSelectionRange(n,n);return e.value})()" % (field, json.dumps(value), "e.value.length" if caret == "end" else "0"))
    time.sleep(.3)
def val(field): return ev("document.getElementById(%r).value" % field)
OUT = {"platform": sys.platform, "release": platform.platform()}
def probe(name, field, preset, keys_then_text, caret="end"):
    setup(field, preset, caret)
    for k in keys_then_text:
        if isinstance(k, tuple): pyautogui.hotkey(*k); time.sleep(.3)
        elif k.startswith("<"): pyautogui.press(k.strip("<>")); time.sleep(.3)
        else: pyautogui.write(k, interval=.05); time.sleep(.3)
    OUT[name] = {"预置": preset, "结果": val(field)}
probe("A_ctrl_a_替换", "a", "OLD-VALUE", [("ctrl", "a"), "NEW"])
probe("B_command_a_替换", "a", "OLD-VALUE", [("command", "a"), "NEW"])
# 剪贴板:a 里 全选+ctrl+c,再到 b 里 ctrl+v
setup("a", "COPYME"); pyautogui.hotkey("ctrl", "a"); time.sleep(.2); pyautogui.hotkey("ctrl", "c"); time.sleep(.3)
setup("b", ""); pyautogui.hotkey("ctrl", "v"); time.sleep(.4); OUT["C_ctrl_c_v_剪贴板"] = {"b 结果": val("b")}
setup("a", "COPYME2"); pyautogui.hotkey("command", "a"); time.sleep(.2); pyautogui.hotkey("command", "c"); time.sleep(.3)
setup("b", ""); pyautogui.hotkey("command", "v"); time.sleep(.4); OUT["D_command_c_v_剪贴板"] = {"b 结果": val("b")}
probe("E_ctrl_z_撤销", "a", "BASE", [" typed", ("ctrl", "z")])
probe("F_command_z_撤销", "a", "BASE", [" typed", ("command", "z")])
probe("G_home_后打字", "a", "OLD", ["<home>", "X"])
probe("H_end_后打字_光标在头", "a", "OLD", ["<end>", "X"], caret="start")
probe("I_ctrl_backspace_删词", "a", "hello world", [("ctrl", "backspace")])
probe("J_alt_backspace_删词", "a", "hello world", [("alt", "backspace")])
probe("K_textarea_ctrl_home_后打字", "t", "line1\nline2\nline3", [("ctrl", "home"), "X"])
probe("L_textarea_ctrl_end_后打字_光标在头", "t", "line1\nline2\nline3", [("ctrl", "end"), "X"], caret="start")
probe("M_shift_home_选到行首再打字", "a", "OLD-VALUE", [("shift", "home"), "NEW"])
probe("N_ctrl_shift_home_再打字", "t", "line1\nline2", [("ctrl", "shift", "home"), "NEW"])
probe("O_ctrl_a_在textarea", "t", "line1\nline2", [("ctrl", "a"), "NEW"])
ws.close(); proc.terminate()
print("MACGUIPROBE " + json.dumps(OUT, ensure_ascii=False))
