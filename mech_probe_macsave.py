#!/usr/bin/env python3
"""mac 专项:TextEdit 存储表里直接敲绝对路径会怎样(朴素路线),以及 Cmd+Shift+G 再填名(正确路线)。mss 截图。"""
import json, pathlib, subprocess, time, pyautogui, mss
from PIL import Image
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True); F = pathlib.Path.home() / "envshift-macsave"; R = {}
def shot(n):
    try:
        with mss.mss() as cap: raw = cap.grab(cap.monitors[1]); Image.frombytes("RGB", raw.size, raw.rgb).save(OUT / (n + ".png"))
    except Exception as e: print("shot fail", n, e)
def osa(s, t=30):
    try: return subprocess.run(["osascript", "-e", s], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return "ERR " + str(e)
def fresh():
    osa('tell application "TextEdit" to quit saving no'); time.sleep(2)
    subprocess.run(["rm", "-rf", str(F)]); (F / "out").mkdir(parents=True)
    for k in ("NSAutomaticCapitalizationEnabled", "NSAutomaticQuoteSubstitutionEnabled", "NSAutomaticSpellingCorrectionEnabled"):
        subprocess.run(["defaults", "write", "-g", k, "-bool", "false"], capture_output=True)
    subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(8); osa('tell application "TextEdit" to activate'); time.sleep(1.5)
    pyautogui.hotkey("command", "n"); time.sleep(2); pyautogui.click(600, 400); time.sleep(1); pyautogui.hotkey("command", "shift", "t"); time.sleep(1)
    pyautogui.typewrite("hello", interval=.06); time.sleep(.5); pyautogui.hotkey("command", "s"); time.sleep(3)
def listing(): return sorted(str(x.relative_to(F)) for x in F.rglob("*"))
dest = F / "out" / "report.txt"
# 朴素:在文件名栏直接敲绝对路径
fresh(); shot("naive-0-sheet")
pyautogui.hotkey("command", "a"); pyautogui.typewrite(str(dest), interval=.02); time.sleep(1); shot("naive-1-typed")
pyautogui.press("enter"); time.sleep(3); shot("naive-2-after-enter")
pyautogui.press("enter"); time.sleep(3); shot("naive-3-after-enter2")
R["naive"] = {"landed": dest.exists(), "listing": listing(), "textedit_windows": osa('tell application "TextEdit" to get name of every window')}
osa('tell application "TextEdit" to quit saving no'); time.sleep(2)
# 正确:Cmd+Shift+G 输目录 → 回车 → 填文件名 → 回车(→ 若追问扩展名再回车)
fresh(); pyautogui.hotkey("command", "shift", "g"); time.sleep(1.5); shot("oracle-0-goto")
pyautogui.typewrite(str(F / "out"), interval=.02); time.sleep(.8); pyautogui.press("enter"); time.sleep(1.5); shot("oracle-1-navigated")
pyautogui.hotkey("command", "a"); pyautogui.typewrite("report.txt", interval=.03); time.sleep(.5); pyautogui.press("enter"); time.sleep(3); shot("oracle-2-saved")
R["oracle"] = {"landed": dest.exists(), "listing": listing()}
osa('tell application "TextEdit" to quit saving no')
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); print(json.dumps(R, ensure_ascii=False)); print("MACSAVE-DONE")
