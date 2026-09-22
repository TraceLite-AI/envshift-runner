#!/usr/bin/env python3
"""探针 v2:找「以 Linux 为目标」的 GUI 机制(全部走「打开已有 .txt→改→原地保存」,mac 才不会变 RTF)(现有 20 道 GUI 里 Linux 全是对照,0 道靶子)。

只测事实,不下判断;每条都三系统同一套动作,结果人读。四个候选:
  A 大小写路径:盘上是 report.txt,在打开对话框里输 Report.txt —— Win/mac 文件系统不敏感应能打开,Linux GTK 应失败
  B 保存时补尾换行:输入不带结尾换行的文本,保存后看盘上字节是否多出 \n
  C 自动缩进:逐字符键入带缩进的多行文本,看落盘内容是否被累积缩进污染
  D 偏好项可达性:B/C 若成立,编辑器偏好里是否有开关可关掉(决定参考解能不能做出来)
用法: python3 linuxgui_probe.py   → probe_out/{result.json,*.png,*.txt}
"""
import json, os, pathlib, platform, subprocess, sys, time

import pyautogui
pyautogui.FAILSAFE = False
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
SYS = platform.system()
HOME = pathlib.Path.home()
FOLDER = HOME / "envshift-linuxprobe"
R = {"platform": platform.platform(), "system": SYS, "screen": list(pyautogui.size()), "checks": {}}
MOD = "command" if SYS == "Darwin" else "ctrl"


def log(*a):
    print(*a, flush=True)


def shot(name):
    try: pyautogui.screenshot(str(OUT / (name + ".png")))
    except Exception as e: log("shot fail", name, e)


def reset_folder():
    import shutil
    shutil.rmtree(FOLDER, ignore_errors=True); FOLDER.mkdir(parents=True)


def quit_editor():
    if SYS == "Darwin":
        subprocess.run(["osascript", "-e", 'tell application "TextEdit" to quit saving no'], capture_output=True, timeout=20)
    elif SYS == "Windows":
        subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
    else:
        subprocess.run(["pkill", "-f", "gedit"], capture_output=True)
    time.sleep(2)


def open_editor(path=None):
    """打开原生编辑器(可带文件);返回是否起得来。"""
    quit_editor()
    if SYS == "Darwin":
        cmd = ["open", "-a", "TextEdit"] + ([str(path)] if path else [])
    elif SYS == "Windows":
        cmd = ["notepad.exe"] + ([str(path)] if path else [])
    else:
        cmd = ["gedit"] + ([str(path)] if path else [])
    subprocess.Popen(cmd)
    time.sleep(6)
    if SYS == "Darwin" and not path:
        pyautogui.hotkey("command", "n"); time.sleep(2)
    return True


def focus():
    """照抄 batch9 参考解:打字前必须点一下窗口,否则 mac 上按键全丢。"""
    pyautogui.click(600, 400); time.sleep(0.8)
    if SYS == "Darwin":
        pyautogui.hotkey("command", "shift", "t"); time.sleep(1)   # 强制纯文本,别存成 RTF


def type_text(s):
    pyautogui.typewrite(s, interval=0.02)


def save_as(path):
    """另存为到指定路径(三系统各自的路径输入方式)。"""
    pyautogui.hotkey(MOD, "s"); time.sleep(3)
    if SYS == "Darwin":
        pyautogui.hotkey("command", "shift", "g"); time.sleep(1.5)
        type_text(str(path)); time.sleep(0.5); pyautogui.press("enter"); time.sleep(1.5); pyautogui.press("enter"); time.sleep(3)
    elif SYS == "Windows":
        type_text('"%s"' % path); time.sleep(0.5); pyautogui.press("enter"); time.sleep(3)
    else:
        type_text(str(path.name)); time.sleep(0.5)
        # GTK 保存框:先进目录再填名字最稳;这里直接用 Ctrl+A 覆盖再输全名
        pyautogui.hotkey("ctrl", "a"); time.sleep(0.3); type_text(str(path)); time.sleep(0.5)
        pyautogui.press("enter"); time.sleep(3)
    time.sleep(2)


# ---------------- A:大小写路径 ----------------
def check_case_path():
    reset_folder()
    disk = FOLDER / "report.txt"; disk.write_text("line one\n", encoding="utf-8")
    given = FOLDER / "Report.txt"          # 题面会给这个(盘上不存在,只有大小写不同的)
    open_editor(); focus()
    pyautogui.hotkey(MOD, "o"); time.sleep(3)
    if SYS == "Darwin":
        pyautogui.hotkey("command", "shift", "g"); time.sleep(1.5)
    elif SYS == "Linux":
        pyautogui.hotkey("ctrl", "l"); time.sleep(1.5)
    type_text(str(given)); time.sleep(0.8); pyautogui.press("enter"); time.sleep(4)
    shot("A-after-open")
    pyautogui.click(600, 400); time.sleep(0.8)
    # 判断是否真的打开了盘上文件:在窗口里追加一行再原地保存,看 report.txt 是否变化
    marker = "PROBE-A-APPENDED"
    pyautogui.hotkey(MOD, "a"); time.sleep(0.5); pyautogui.press("delete"); time.sleep(0.5)
    type_text(marker); time.sleep(1)
    pyautogui.hotkey(MOD, "s"); time.sleep(4)
    if SYS == "Darwin": pyautogui.press("enter"); time.sleep(2)
    shot("A-after-save")
    after = {p.name: p.read_bytes()[:80].decode("utf-8", "replace") for p in sorted(FOLDER.iterdir()) if p.is_file()}
    quit_editor()
    R["checks"]["A_case_path"] = {
        "given_path_in_prompt": str(given), "disk_file": str(disk),
        "folder_after": after,
        "opened_disk_file": marker in after.get("report.txt", ""),
        "created_new_file": "Report.txt" in after,
    }
    log("A", json.dumps(R["checks"]["A_case_path"], ensure_ascii=False))


# ---------------- B:打开已有无尾换行文件,改一处,原地保存 ----------------
def check_trailing_newline():
    reset_folder()
    target = FOLDER / "trail.txt"
    target.write_bytes(b"alpha\nbeta")      # 盘上本来就没有结尾换行
    open_editor(target); time.sleep(2); focus()
    pyautogui.hotkey(MOD, "a"); time.sleep(0.5); pyautogui.press("delete"); time.sleep(0.5)
    type_text("alpha\nbetaX")               # 仍然不以换行结尾
    time.sleep(1)
    pyautogui.hotkey(MOD, "s"); time.sleep(4); shot("B-after-save")
    files = {p.name: p.read_bytes() for p in sorted(FOLDER.iterdir()) if p.is_file()}
    raw = target.read_bytes() if target.exists() else b""
    quit_editor()
    R["checks"]["B_trailing_newline"] = {
        "on_disk_before": "alpha\\nbeta(无尾换行)", "typed": "alpha\\nbetaX(无尾换行)",
        "files": {k: repr(v[:60]) for k, v in files.items()},
        "target_bytes": repr(raw[:60]),
        "ends_with_newline": bool(raw) and raw.endswith(b"\n"),
        "stray_backup": [k for k in files if k.endswith("~") or k.startswith(".")],
    }
    log("B", json.dumps(R["checks"]["B_trailing_newline"], ensure_ascii=False))


# ---------------- C:自动缩进 ----------------
def check_auto_indent():
    reset_folder()
    target = FOLDER / "indent.yaml"
    body = "root:\n    child: 1\n    other: 2\nend: true\n"
    target.write_bytes(b"placeholder\n")     # 先有文件 → 打开已有文件编辑,mac 保持纯文本
    open_editor(target); time.sleep(2); focus()
    pyautogui.hotkey(MOD, "a"); time.sleep(0.5); pyautogui.press("delete"); time.sleep(0.5)
    type_text(body)
    time.sleep(1)
    pyautogui.hotkey(MOD, "s"); time.sleep(4)
    shot("C-after-save")
    files = {p.name: p.read_bytes() for p in sorted(FOLDER.iterdir()) if p.is_file()}
    got = None
    for k, v in files.items():
        if k.startswith("indent"): got = v.decode("utf-8", "replace")
    quit_editor()
    R["checks"]["C_auto_indent"] = {
        "typed": body, "files": list(files),
        "saved": got,
        "matches_typed": (got or "").replace("\r\n", "\n").rstrip("\n") == body.rstrip("\n"),
        "stray_backup": [k for k in files if k.endswith("~")],
    }
    log("C", json.dumps(R["checks"]["C_auto_indent"], ensure_ascii=False))


# ---------------- D:编辑器偏好里有没有开关 ----------------
def check_prefs():
    info = {}
    if SYS == "Linux":
        for key in ("auto-indent", "insert-spaces", "tabs-size"):
            r = subprocess.run(["gsettings", "get", "org.gnome.gedit.preferences.editor", key], capture_output=True, text=True)
            info[key] = (r.stdout or r.stderr).strip()
        r = subprocess.run(["gsettings", "list-keys", "org.gnome.gedit.preferences.editor"], capture_output=True, text=True)
        info["all_editor_keys"] = (r.stdout or "").split()
        r = subprocess.run(["gedit", "--version"], capture_output=True, text=True); info["gedit_version"] = (r.stdout or r.stderr).strip()
    elif SYS == "Darwin":
        r = subprocess.run(["defaults", "read", "com.apple.TextEdit"], capture_output=True, text=True); info["TextEdit_defaults"] = (r.stdout or r.stderr)[:2000]
    else:
        r = subprocess.run(["reg", "query", r"HKCU\Software\Microsoft\Notepad"], capture_output=True, text=True); info["Notepad_reg"] = (r.stdout or r.stderr)[:2000]
    R["checks"]["D_prefs"] = info
    log("D", json.dumps(info, ensure_ascii=False)[:600])


for name, fn in (("D", check_prefs), ("B", check_trailing_newline), ("C", check_auto_indent), ("A", check_case_path)):
    try:
        fn()
    except Exception as e:
        R["checks"].setdefault("errors", {})[name] = "%s: %s" % (type(e).__name__, e)
        log("!! %s 失败 %s" % (name, e))
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8")
log("PROBE-DONE", SYS)
