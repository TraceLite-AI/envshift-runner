#!/usr/bin/env python3
"""探针 2:对 .txt(Windows 隐藏扩展名的注册类型)做三种改名,三系统对比;Windows 再试键盘打开"文件扩展名"显示后重做。"""
import json, os, pathlib, shutil, subprocess, sys, time
import pyautogui, mss
from PIL import Image
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
D = pathlib.Path.home() / "Documents" / "envshift-fm2"; shutil.rmtree(D, ignore_errors=True); D.mkdir(parents=True)
def shot(n):
    with mss.mss() as s:
        raw = s.grab(s.monitors[1]); Image.frombytes("RGB", raw.size, raw.rgb).save(OUT / (n + ".png"))
def osa(script): return subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20).stdout.strip()
R = {"platform": sys.platform}
VARIANTS = [("same", "report.txt", "report_final.txt"), ("newext", "notes.txt", "notes_old.md"), ("noext", "LICENSE.txt", "LICENSE")]
def rename_once(tag, old, new, extra=""):
    for p in D.iterdir(): p.unlink()
    (D / old).write_bytes(b"x\n")
    info = {"typed": new}
    try:
        if sys.platform == "darwin":
            osa('tell application "Finder" to close every window'); subprocess.run(["open", str(D)]); time.sleep(4)
            osa('tell application "Finder" to select file "%s" of folder (POSIX file "%s" as alias)' % (old, str(D))); time.sleep(1); osa('tell application "Finder" to activate'); time.sleep(.8)
            pyautogui.press("enter"); time.sleep(1); shot(tag + extra + "-1-editing"); pyautogui.hotkey("command", "a"); pyautogui.typewrite(new, interval=.04); time.sleep(.5); pyautogui.press("enter"); time.sleep(2); shot(tag + extra + "-3-after")
            info["dialog_buttons"] = osa('tell application "System Events" to tell process "Finder" to get name of every button of window 1')[:120]
            if "Keep" in info["dialog_buttons"] or "Use" in info["dialog_buttons"] or "Remove" in info["dialog_buttons"]:
                info["default_choice_result_first"] = True; pyautogui.press("enter"); time.sleep(1.5); shot(tag + extra + "-4-after-dialog")
        elif os.name == "nt":
            subprocess.Popen(["explorer.exe", str(D)]); time.sleep(5)
            pyautogui.click(600, 400); time.sleep(.5); pyautogui.hotkey("ctrl", "a"); time.sleep(.5)
            pyautogui.press("f2"); time.sleep(1); shot(tag + extra + "-1-editing"); pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(new, interval=.04); time.sleep(.5); pyautogui.press("enter"); time.sleep(2); shot(tag + extra + "-3-after")
            pyautogui.press("enter"); time.sleep(1.5); shot(tag + extra + "-4-after-enter2")   # 若有"确定改扩展名?"对话框,默认 Yes
        else:
            subprocess.Popen(["nautilus", "--new-window", str(D)]); time.sleep(6)
            pyautogui.click(640, 450); time.sleep(.5); pyautogui.hotkey("ctrl", "a"); time.sleep(.5)
            pyautogui.press("f2"); time.sleep(1); shot(tag + extra + "-1-editing"); pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(new, interval=.04); time.sleep(.5); pyautogui.press("enter"); time.sleep(2); shot(tag + extra + "-3-after")
        info["files_after"] = sorted(p.name for p in D.iterdir())
    except Exception as e:
        info["error"] = "%s: %s" % (type(e).__name__, e)
    try:
        if sys.platform == "darwin": osa('tell application "Finder" to close every window')
        elif os.name == "nt": pyautogui.hotkey("alt", "f4"); time.sleep(2)
        else: subprocess.run(["pkill", "-f", "nautilus"], capture_output=True)
    except Exception: pass
    time.sleep(1); return info
for tag, old, new in VARIANTS: R[tag] = rename_once(tag, old, new)
if os.name == "nt":
    import winreg
    try:
        # 键盘打开"文件扩展名":View 选项卡(Alt, V) → 文件扩展名(HF)
        subprocess.Popen(["explorer.exe", str(D)]); time.sleep(5); pyautogui.press("alt"); time.sleep(.5); pyautogui.press("v"); time.sleep(1); shot("toggle-1-viewtab"); pyautogui.press("h"); pyautogui.press("f"); time.sleep(1.5); shot("toggle-2-after")
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"); R["HideFileExt_after_toggle"] = winreg.QueryValueEx(k, "HideFileExt")[0]
        pyautogui.hotkey("alt", "f4"); time.sleep(2)
    except Exception as e: R["toggle_error"] = str(e)
    for tag, old, new in VARIANTS: R[tag + "_shown"] = rename_once(tag, old, new, "-shown")
print("FMRENAME2 " + json.dumps(R, ensure_ascii=False))
