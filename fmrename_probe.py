#!/usr/bin/env python3
"""探针:三系统默认文件管理器里"把 data.csv 改名成 data_old.csv"的真实结果(资源管理器默认隐藏已知扩展名 → 双扩展名?Finder 追问?)。
用 pyautogui 驱动:打开文件夹窗口 → 选中文件 → 进入改名 → 全选 → 输入新名 → 回车 → 看盘上文件名。每步截图。"""
import json, os, pathlib, platform, shutil, subprocess, sys, time
import pyautogui, mss
from PIL import Image
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
D = pathlib.Path.home() / "Documents" / "envshift-fm"; shutil.rmtree(D, ignore_errors=True); D.mkdir(parents=True)
def shot(n):
    with mss.mss() as s:
        raw = s.grab(s.monitors[1]); Image.frombytes("RGB", raw.size, raw.rgb).save(OUT / (n + ".png"))
R = {"platform": sys.platform}
VARIANTS = [("full", "data_old.csv"), ("stem", "data_old"), ("newext", "data_old.txt")]
for tag, newname in VARIANTS:
    for p in D.iterdir(): p.unlink()
    (D / "data.csv").write_bytes(b"a,b\n1,2\n"); (D / "zz-other.txt").write_bytes(b"x")
    info = {"typed": newname}
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", 'tell application "Finder" to close every window'], capture_output=True); subprocess.run(["open", str(D)]); time.sleep(4)
            subprocess.run(["osascript", "-e", 'tell application "Finder" to select file "data.csv" of folder (POSIX file "%s" as alias)' % str(D)], capture_output=True); time.sleep(1)
            subprocess.run(["osascript", "-e", 'tell application "Finder" to activate'], capture_output=True); time.sleep(.8)
            shot(tag + "-0-selected"); pyautogui.press("enter"); time.sleep(1); shot(tag + "-1-editing")
            pyautogui.hotkey("command", "a"); pyautogui.typewrite(newname, interval=.04); time.sleep(.5); shot(tag + "-2-typed"); pyautogui.press("enter"); time.sleep(2); shot(tag + "-3-after")
            info["dialog_buttons"] = subprocess.run(["osascript", "-e", 'tell application "System Events" to tell process "Finder" to get name of every button of window 1'], capture_output=True, text=True).stdout.strip()[:120]
            if "Keep" in info["dialog_buttons"] or "Use" in info["dialog_buttons"]:
                pyautogui.press("enter"); time.sleep(1.5); shot(tag + "-4-after-dialog")
        elif os.name == "nt":
            subprocess.Popen(["explorer.exe", str(D)]); time.sleep(5)
            pyautogui.click(600, 400); time.sleep(.5); pyautogui.hotkey("ctrl", "a"); time.sleep(.3)   # 先全选再点第一项
            pyautogui.press("home"); time.sleep(.5); shot(tag + "-0-selected")
            pyautogui.press("f2"); time.sleep(1); shot(tag + "-1-editing")
            pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(newname, interval=.04); time.sleep(.5); shot(tag + "-2-typed"); pyautogui.press("enter"); time.sleep(2); shot(tag + "-3-after")
        else:
            subprocess.Popen(["nautilus", "--new-window", str(D)]); time.sleep(6)
            pyautogui.click(640, 450); time.sleep(.5); pyautogui.hotkey("ctrl", "a"); pyautogui.press("home"); time.sleep(.5); shot(tag + "-0-selected")
            pyautogui.press("f2"); time.sleep(1); shot(tag + "-1-editing")
            pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(newname, interval=.04); time.sleep(.5); shot(tag + "-2-typed"); pyautogui.press("enter"); time.sleep(2); shot(tag + "-3-after")
        info["files_after"] = sorted(p.name for p in D.iterdir())
    except Exception as e:
        info["error"] = "%s: %s" % (type(e).__name__, e)
    R[tag] = info
    try:
        if sys.platform == "darwin": subprocess.run(["osascript", "-e", 'tell application "Finder" to close every window'], capture_output=True)
        elif os.name == "nt": subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True); time.sleep(2); subprocess.Popen(["explorer.exe"]); time.sleep(3)
        else: subprocess.run(["pkill", "-f", "nautilus"], capture_output=True)
    except Exception: pass
    time.sleep(1)
print("FMRENAMEPROBE " + json.dumps(R, ensure_ascii=False))
