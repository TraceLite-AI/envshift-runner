#!/usr/bin/env python3
"""机制探针第二轮(无模型,只记事实):
U 文件在编辑器里开着时在文件管理器改名,再回编辑器改内容保存 → 存到旧名还是新名?(靶 Windows)
L 显示扩展名时把 .txt 改成 .yaml,弹确认框后只按回车 → 改成了没?(靶 Windows)
G 保存框的文件名栏直接敲绝对路径 → 文件落在哪、叫什么?(靶 mac)
"""
import json, os, pathlib, platform, shutil, subprocess, time
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
SYS = platform.system(); HOME = pathlib.Path.home(); F = HOME / "envshift-mechprobe2"
R = {"platform": platform.platform(), "system": SYS, "checks": {}}
MAC, WIN = SYS == "Darwin", SYS == "Windows"; MOD = "command" if MAC else "ctrl"
def log(*a): print(*a, flush=True)
import pyautogui; pyautogui.FAILSAFE = False
def shot(n):
    try: pyautogui.screenshot(str(OUT / (n + ".png")))
    except Exception as e: log("shot fail", n, e)
def osa(s, t=25):
    try: return subprocess.run(["osascript", "-e", s], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return "ERR " + str(e)
def reset(): shutil.rmtree(F, ignore_errors=True); F.mkdir(parents=True)
def kill_editor():
    if MAC: osa('tell application "TextEdit" to quit saving no')
    elif WIN: subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
    else: subprocess.run(["pkill", "-f", "gedit"], capture_output=True)
    time.sleep(2)
def mac_prefs():
    for k in ("NSAutomaticCapitalizationEnabled", "NSAutomaticQuoteSubstitutionEnabled", "NSAutomaticSpellingCorrectionEnabled", "NSAutomaticDashSubstitutionEnabled"):
        subprocess.run(["defaults", "write", "-g", k, "-bool", "false"], capture_output=True); subprocess.run(["defaults", "write", "com.apple.TextEdit", k, "-bool", "false"], capture_output=True)
def open_editor(path=None):
    kill_editor()
    if MAC:
        mac_prefs(); subprocess.Popen(["open", "-a", "TextEdit"] + ([str(path)] if path else [])); time.sleep(9); osa('tell application "TextEdit" to activate'); time.sleep(2)
        if path is None: pyautogui.hotkey("command", "n"); time.sleep(2)
    elif WIN: subprocess.Popen(["notepad.exe"] + ([str(path)] if path else [])); time.sleep(6)
    else: subprocess.Popen(["gedit", "--new-window"] + ([str(path)] if path else [])); time.sleep(7)
    pyautogui.click(600, 400); time.sleep(1.5)
    if MAC and path is None: pyautogui.hotkey("command", "shift", "t"); time.sleep(1)
def open_fm():
    if MAC: osa('tell application "Finder" to close every window'); subprocess.run(["open", str(F)]); time.sleep(4); osa('tell application "Finder" to activate'); time.sleep(1.5)
    elif WIN: subprocess.Popen(["explorer.exe", str(F)]); time.sleep(6)
    else: subprocess.Popen(["nautilus", "--new-window", str(F)]); time.sleep(7)
    pyautogui.click(600, 400); time.sleep(1)
def close_fm():
    if MAC: osa('tell application "Finder" to close every window')
    elif WIN: subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True); time.sleep(1); subprocess.Popen(["explorer.exe"])
    else: subprocess.run(["pkill", "-f", "nautilus"], capture_output=True)
    time.sleep(2)
def rename_in_fm(old, new):
    """三系统各自的改名动作:选中 → 改名键 → 全选 → 敲新名 → 回车。"""
    if MAC:
        osa('tell application "Finder" to select file "%s" of folder (POSIX file "%s" as alias)' % (old, str(F))); time.sleep(1); pyautogui.press("enter")
    elif WIN:
        pyautogui.typewrite(old.split(".")[0][:6], interval=.1); time.sleep(.8); pyautogui.press("f2")
    else:
        pyautogui.click(640, 450); time.sleep(.8); pyautogui.press("home"); time.sleep(.6); pyautogui.press("f2")
    time.sleep(1.2); pyautogui.hotkey(MOD, "a"); pyautogui.typewrite(new, interval=.05); time.sleep(.5); pyautogui.press("enter"); time.sleep(2.5)

# ---------- U 编辑器跟不跟文件走 ----------
def check_follow_rename():
    reset(); p = F / "draft.txt"; p.write_bytes(b"line one\n")
    open_editor(p); shot("U-opened")
    open_fm(); rename_in_fm("draft.txt", "final.txt"); shot("U-renamed"); close_fm()
    files_mid = sorted(x.name for x in F.iterdir())
    # 回编辑器:聚焦、跳到末尾、追加一行、保存
    if MAC: osa('tell application "TextEdit" to activate'); time.sleep(1.5)
    elif WIN: subprocess.run(["powershell", "-c", "(New-Object -ComObject WScript.Shell).AppActivate('Notepad')"], capture_output=True); time.sleep(1.5)
    else: subprocess.run(["wmctrl", "-a", "gedit"], capture_output=True); time.sleep(1.5)
    pyautogui.click(600, 400); time.sleep(1)
    pyautogui.hotkey("command", "down") if MAC else pyautogui.hotkey("ctrl", "end"); time.sleep(.4)
    pyautogui.press("enter"); pyautogui.typewrite("line two", interval=.06); time.sleep(.8); pyautogui.hotkey(MOD, "s"); time.sleep(3); shot("U-after-save")
    pyautogui.press("enter"); time.sleep(2)   # 若弹保存框/确认,默认键
    files = {x.name: x.read_bytes().decode("utf-8", "replace") for x in F.iterdir() if x.is_file()}
    kill_editor()
    R["checks"]["U_follow_rename"] = {"files_after_rename": files_mid, "files_after_save": files,
        "saved_to_new_name": files.get("final.txt", "").count("line two") == 1, "old_name_recreated": "draft.txt" in files}
    log("U", json.dumps(R["checks"]["U_follow_rename"], ensure_ascii=False))

# ---------- L 改扩展名确认框默认键 ----------
def check_ext_change_dialog():
    reset(); (F / "spec.txt").write_bytes(b"kept\n"); (F / "readme.txt").write_bytes(b"r\n")
    if WIN:
        subprocess.run(["reg", "add", r"HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced", "/v", "HideFileExt", "/t", "REG_DWORD", "/d", "0", "/f"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True); time.sleep(1.5); subprocess.Popen(["explorer.exe"]); time.sleep(4)
    open_fm(); rename_in_fm("spec.txt", "spec.yaml"); shot("L-after-enter")
    files_after_enter = sorted(x.name for x in F.iterdir())
    pyautogui.press("enter"); time.sleep(2); shot("L-after-second-enter")   # 再按一次回车(默认键)
    files_after_2 = sorted(x.name for x in F.iterdir()); close_fm()
    R["checks"]["L_ext_change_dialog"] = {"after_first_enter": files_after_enter, "after_second_enter": files_after_2,
        "renamed_by_default_key": "spec.yaml" in files_after_2 and "spec.txt" not in files_after_2}
    log("L", json.dumps(R["checks"]["L_ext_change_dialog"], ensure_ascii=False))

# ---------- G 保存框敲绝对路径 ----------
def check_abs_path_in_save():
    reset(); target = F / "out" ; target.mkdir(); dest = target / "report.txt"
    open_editor(); pyautogui.typewrite("hello", interval=.06); time.sleep(.5); pyautogui.hotkey(MOD, "s"); time.sleep(3); shot("G-save-dialog")
    pyautogui.hotkey(MOD, "a"); pyautogui.typewrite(str(dest), interval=.02); time.sleep(.8); shot("G-typed"); pyautogui.press("enter"); time.sleep(3); shot("G-after-enter")
    pyautogui.press("enter"); time.sleep(2)   # 追问(如 Use .txt)默认
    found = sorted(str(x.relative_to(HOME)) for x in HOME.rglob("report*") if "envshift" in str(x) or x.parent == HOME)
    kill_editor()
    R["checks"]["G_abs_path_in_save"] = {"typed": str(dest), "landed_at_target": dest.exists(), "report_files_found": found[:10],
        "folder_listing": sorted(str(x.relative_to(F)) for x in F.rglob("*"))}
    log("G", json.dumps(R["checks"]["G_abs_path_in_save"], ensure_ascii=False))

for name, fn in (("L", check_ext_change_dialog), ("U", check_follow_rename), ("G", check_abs_path_in_save)):
    try: fn()
    except Exception as e:
        R["checks"].setdefault("errors", {})[name] = "%s: %s" % (type(e).__name__, e); log("!!", name, e)
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); log("PROBE2-DONE", SYS)
