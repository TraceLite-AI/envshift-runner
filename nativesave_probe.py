#!/usr/bin/env python3
"""探针:三系统原生文本编辑器"另存为"的真实行为。用 pyautogui 驱动记事本 / TextEdit / gedit,
输入两行文本,按快捷键另存,在文件名栏输入完整路径(名字带 .csv / .json / 无扩展名),回车,
然后看目标目录里落了什么文件、字节是什么。每步截图。输出一行 JSON。"""
import json, os, pathlib, platform, shutil, subprocess, sys, time
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import pyautogui, mss
from PIL import Image
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
DOCS = pathlib.Path.home() / "Documents" / "envshift-probe"; shutil.rmtree(DOCS, ignore_errors=True); DOCS.mkdir(parents=True)
TEXT = "id,name\n1,caf" + chr(0xE9) + "\n"
def shot(name):
    with mss.mss() as s:
        raw = s.grab(s.monitors[1]); Image.frombytes("RGB", raw.size, raw.rgb).save(OUT / (name + ".png"))
def launch():
    if sys.platform == "darwin":
        p = subprocess.Popen(["open", "-a", "TextEdit", "-n", "-W"]) if False else subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(4)
        # 新窗口:关掉可能的文件选择面板,Cmd+N 新建
        pyautogui.hotkey("command", "n"); time.sleep(2)
    elif os.name == "nt":
        p = subprocess.Popen(["notepad.exe"]); time.sleep(4)
    else:
        p = subprocess.Popen(["gedit", "--new-window"]); time.sleep(5)
    return p
R = {"platform": sys.platform, "release": platform.platform(), "docs": str(DOCS)}
for tag, name in (("csv", "probe1.csv"), ("json", "probe2.json"), ("noext", "probe3")):
    try:
        proc = launch(); shot(tag + "-0-launched")
        pyautogui.click(600, 400); time.sleep(.5)
        pyautogui.typewrite(TEXT.replace(chr(0xE9), "e"), interval=.03); time.sleep(.5)   # ASCII 输入,避开输入法
        if sys.platform == "darwin": pyautogui.hotkey("command", "shift", "s")            # TextEdit: Save As
        else: pyautogui.hotkey("ctrl", "shift", "s") if os.name != "nt" else pyautogui.hotkey("ctrl", "s")
        time.sleep(2.5); shot(tag + "-1-dialog")
        target = str(DOCS / name)
        if sys.platform == "darwin":
            pyautogui.hotkey("command", "shift", "g"); time.sleep(1.2); pyautogui.typewrite(str(DOCS), interval=.02); time.sleep(.8); pyautogui.press("enter"); time.sleep(1.5)
            pyautogui.hotkey("command", "a"); pyautogui.typewrite(name, interval=.03); time.sleep(.5)
        else:
            pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(target, interval=.02); time.sleep(.5)
        shot(tag + "-2-typed"); pyautogui.press("enter"); time.sleep(2.5); shot(tag + "-3-after-enter")
        # 可能的追问对话框(TextEdit: 用 .txt 还是 .csv? / 记事本: 编码等):再截一张,按一次 enter 试试
        pyautogui.press("enter"); time.sleep(2); shot(tag + "-4-after-enter2")
        files = {}
        for p in sorted(DOCS.iterdir()):
            b = p.read_bytes(); files[p.name] = {"bytes": len(b), "head": b[:40].decode("utf-8", "replace"), "is_rtf": b.startswith(b"{\\rtf"), "exact": b == TEXT.replace(chr(0xE9), "e").encode()}
        R[tag] = {"asked": name, "files_after": files}
        for p in DOCS.iterdir(): p.unlink()
    except Exception as e:
        R[tag] = {"error": "%s: %s" % (type(e).__name__, e)}
    finally:
        try:
            if sys.platform == "darwin": subprocess.run(["osascript", "-e", 'tell application "TextEdit" to quit saving no'], timeout=10)
            else: proc.kill()
        except Exception: pass
        time.sleep(1.5)
print("NATIVESAVEPROBE " + json.dumps(R, ensure_ascii=False))
