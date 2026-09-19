#!/usr/bin/env python3
"""mac 专用探针:TextEdit 纯文本模式下,无扩展名文件名怎样才能不被补 .txt。多种变体各试一次,输出每种落盘的文件名。"""
import json, os, pathlib, shutil, subprocess, sys, time
import pyautogui, mss
from PIL import Image
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
DOCS = pathlib.Path.home() / "Documents" / "envshift-probe2"
def shot(n):
    with mss.mss() as s:
        raw = s.grab(s.monitors[1]); Image.frombytes("RGB", raw.size, raw.rgb).save(OUT / (n + ".png"))
def osa(script):
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=20); return (r.returncode, r.stdout.strip(), r.stderr.strip()[:200])
CB = 'tell application "System Events" to tell process "TextEdit" to tell sheet 1 of window 1 to '
R = {}
VARIANTS = {
    "A_uncheck_enter": ("uncheck", "enter"),
    "B_uncheck_clicksave": ("uncheck", "button"),
    "C_uncheck_refocus_enter": ("uncheck_refocus", "enter"),
    "D_default_enter": ("none", "enter"),
    "E_name_trailing_dot": ("none", "enter_dot"),
    "F_uncheck_via_value": ("setvalue", "button"),
}
for tag, (cb, how) in VARIANTS.items():
    shutil.rmtree(DOCS, ignore_errors=True); DOCS.mkdir(parents=True)
    info = {}
    try:
        osa('tell application "TextEdit" to quit saving no'); time.sleep(1)
        subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(4); pyautogui.hotkey("command", "n"); time.sleep(2)
        pyautogui.click(600, 400); time.sleep(.5); pyautogui.hotkey("command", "shift", "t"); time.sleep(1)
        subprocess.run(["pbcopy"], input=b"FROM python:3.12-slim\nWORKDIR /app\n"); pyautogui.hotkey("command", "v"); time.sleep(.8)
        pyautogui.hotkey("command", "s"); time.sleep(2.5)
        pyautogui.hotkey("command", "shift", "g"); time.sleep(1.2); pyautogui.typewrite(str(DOCS), interval=.02); time.sleep(.8); pyautogui.press("enter"); time.sleep(1.5)
        pyautogui.hotkey("command", "a"); pyautogui.typewrite("Dockerfile." if how == "enter_dot" else "Dockerfile", interval=.03); time.sleep(.5)
        info["cb_before"] = osa(CB + 'get value of (first checkbox whose title contains "extension")')
        if cb == "uncheck" or cb == "uncheck_refocus":
            info["click"] = osa(CB + 'if value of (first checkbox whose title contains "extension") is 1 then click (first checkbox whose title contains "extension")'); time.sleep(.8)
        elif cb == "setvalue":
            info["setvalue"] = osa(CB + 'set value of (first checkbox whose title contains "extension") to 0'); time.sleep(.8)
        if cb == "uncheck_refocus":
            info["refocus"] = osa(CB + 'set focused of text field 1 to true'); time.sleep(.5)
        info["cb_after"] = osa(CB + 'get value of (first checkbox whose title contains "extension")')
        shot(tag + "-dialog")
        if how == "button": info["save"] = osa(CB + 'click button "Save"')
        else: pyautogui.press("enter")
        time.sleep(2.5); shot(tag + "-after")
        info["alert"] = osa('tell application "System Events" to tell process "TextEdit" to get name of every button of sheet 1 of window 1')
        if info["alert"][0] == 0 and info["alert"][1]:
            info["alert_handled"] = osa('tell application "System Events" to tell process "TextEdit" to tell sheet 1 of window 1 to click (first button whose name does not contain ".txt" and name is not "Cancel")'); time.sleep(2); shot(tag + "-after2")
        info["files"] = sorted(p.name for p in DOCS.iterdir())
    except Exception as e:
        info["error"] = "%s: %s" % (type(e).__name__, e)
    R[tag] = info
osa('tell application "TextEdit" to quit saving no')
print("NSPROBE2 " + json.dumps(R, ensure_ascii=False))
