#!/usr/bin/env python3
"""mac 专项:TextEdit 自动大写到底怎么关。每种设置下新建纯文本文档敲 'alpha\\nbeta\\ngamma' 存盘看字节。"""
import json, pathlib, subprocess, time, pyautogui
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True); F = pathlib.Path.home() / "envshift-maccap"; R = {"trials": []}
def osa(s, t=30):
    try: return subprocess.run(["osascript", "-e", s], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return "ERR " + str(e)
def dw(dom, key, val="false"): subprocess.run(["defaults", "write", dom, key, "-bool", val], capture_output=True)
KEYS = ("NSAutomaticCapitalizationEnabled", "NSAutomaticSpellingCorrectionEnabled", "NSAutomaticQuoteSubstitutionEnabled", "NSAutomaticDashSubstitutionEnabled", "NSAutomaticTextReplacementEnabled", "NSAutomaticPeriodSubstitutionEnabled")
def trial(name, setup):
    osa('tell application "TextEdit" to quit saving no'); time.sleep(2)
    F.mkdir(parents=True, exist_ok=True); p = F / (name + ".txt")
    if p.exists(): p.unlink()
    setup()
    subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(8); osa('tell application "TextEdit" to activate'); time.sleep(1.5)
    pyautogui.hotkey("command", "n"); time.sleep(2); pyautogui.click(600, 400); time.sleep(1); pyautogui.hotkey("command", "shift", "t"); time.sleep(1)
    for i, ln in enumerate(("alpha", "beta", "gamma")):
        if i: pyautogui.press("enter"); time.sleep(.15)
        pyautogui.typewrite(ln, interval=.06); time.sleep(.3)
    time.sleep(1); pyautogui.hotkey("command", "s"); time.sleep(2.5); pyautogui.hotkey("command", "shift", "g"); time.sleep(1.5)
    pyautogui.typewrite(str(F), interval=.02); time.sleep(.8); pyautogui.press("enter"); time.sleep(1.5); pyautogui.hotkey("command", "a"); pyautogui.typewrite(p.name, interval=.03); time.sleep(.5); pyautogui.press("enter"); time.sleep(3)
    pyautogui.screenshot(str(OUT / (name + ".png")))
    raw = p.read_bytes().decode("utf-8", "replace") if p.exists() else "(未保存)"
    R["trials"].append({"name": name, "disk": raw, "lowercase_ok": raw == "alpha\nbeta\ngamma"}); print(name, repr(raw), flush=True)
    osa('tell application "TextEdit" to quit saving no'); time.sleep(2)
def s_baseline(): pass
def s_global():
    for k in KEYS: dw("-g", k)
    subprocess.run(["killall", "cfprefsd"], capture_output=True); time.sleep(2)
def s_app():
    for k in KEYS: dw("com.apple.TextEdit", k)
    for k in ("SmartQuotes", "SmartDashes", "SmartCopyPaste", "CorrectSpellingAutomatically", "CheckSpellingWhileTyping", "SmartLinks", "DataDetectors", "TextReplacement"): dw("com.apple.TextEdit", k)
    subprocess.run(["killall", "cfprefsd"], capture_output=True); time.sleep(2)
def s_menu():
    # 启动后经 System Events 逐个取消 Edit ▸ Spelling and Grammar / Substitutions 里勾着的项
    subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(8); osa('tell application "TextEdit" to activate'); time.sleep(1.5)
    pyautogui.hotkey("command", "n"); time.sleep(2)
    for sub in ("Spelling and Grammar", "Substitutions"):
        out = osa('''tell application "System Events" to tell process "TextEdit"
  set names to {}
  repeat with mi in menu items of menu 1 of menu item "%s" of menu 1 of menu bar item "Edit" of menu bar 1
    try
      if value of attribute "AXMenuItemMarkChar" of mi is not "" then
        click mi
        set end of names to (name of mi as string)
      end if
    end try
  end repeat
  return names
end tell''' % sub, 40)
        R.setdefault("menu_unchecked", {})[sub] = out
    osa('tell application "TextEdit" to quit saving no'); time.sleep(2)
def s_capitalization_only():
    dw("-g", "NSAutomaticCapitalizationEnabled"); dw("com.apple.TextEdit", "NSAutomaticCapitalizationEnabled")
    subprocess.run(["defaults", "write", "-g", "NSAutomaticCapitalizationEnabled", "-int", "0"], capture_output=True)
    subprocess.run(["killall", "cfprefsd"], capture_output=True); time.sleep(2)
for name, fn in (("baseline", s_baseline), ("global_defaults", s_global), ("app_defaults", s_app), ("menu_uncheck", s_menu), ("cap_int0", s_capitalization_only)):
    try: trial(name, fn)
    except Exception as e: R["trials"].append({"name": name, "error": str(e)}); print("!!", name, e, flush=True)
R["global_now"] = subprocess.run(["defaults", "read", "-g", "NSAutomaticCapitalizationEnabled"], capture_output=True, text=True).stdout.strip()
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); print("MACCAP-DONE", flush=True)
