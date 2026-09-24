#!/usr/bin/env python3
"""机制探针(无模型):五个候选,三系统同一套动作,只记事实。
A 编辑器原地自动保存(靶 mac):打开已有文件、键入、不保存,过 90 s 与关窗后盘上变没变
B 打开中的文件能否改名(靶 Windows):LibreOffice Writer 开着 doc.txt 时 os.rename + 锁文件
C 文件管理器里"敲文件名选中 + F2 改名"(Windows 习惯)在三系统的结果(靶 Linux/mac)
D 记事本新建文件的换行字节(靶 Windows)
E 复制/解压后可执行位(靶 Linux+mac)
"""
import json, os, pathlib, platform, shutil, stat, subprocess, sys, time, zipfile
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
SYS = platform.system(); HOME = pathlib.Path.home(); F = HOME / "envshift-mechprobe"
R = {"platform": platform.platform(), "system": SYS, "checks": {}}
MAC, WIN = SYS == "Darwin", SYS == "Windows"; MOD = "command" if MAC else "ctrl"
def log(*a): print(*a, flush=True)
def reset():
    shutil.rmtree(F, ignore_errors=True); F.mkdir(parents=True)
try:
    import pyautogui; pyautogui.FAILSAFE = False
    def shot(n):
        try: pyautogui.screenshot(str(OUT / (n + ".png")))
        except Exception as e: log("shot fail", n, e)
except Exception as e:
    pyautogui = None; log("pyautogui 不可用", e)
    def shot(n): pass
def osa(s, t=25):
    try: return subprocess.run(["osascript", "-e", s], capture_output=True, text=True, timeout=t).stdout.strip()
    except Exception as e: return "ERR " + str(e)
def kill_editor():
    if MAC: osa('tell application "TextEdit" to quit saving no')
    elif WIN: subprocess.run(["taskkill", "/F", "/IM", "notepad.exe"], capture_output=True)
    else: subprocess.run(["pkill", "-f", "gedit"], capture_output=True)
    time.sleep(2)
def open_editor(path):
    kill_editor()
    if MAC:
        for k in ("NSAutomaticCapitalizationEnabled", "NSAutomaticQuoteSubstitutionEnabled", "NSAutomaticSpellingCorrectionEnabled"):
            subprocess.run(["defaults", "write", "-g", k, "-bool", "false"], capture_output=True)
            subprocess.run(["defaults", "write", "com.apple.TextEdit", k, "-bool", "false"], capture_output=True)
        subprocess.Popen(["open", "-a", "TextEdit", str(path)]); time.sleep(9); osa('tell application "TextEdit" to activate'); time.sleep(2)
    elif WIN: subprocess.Popen(["notepad.exe", str(path)]); time.sleep(6)
    else: subprocess.Popen(["gedit", "--new-window", str(path)]); time.sleep(7)
    pyautogui.click(600, 400); time.sleep(1.5)

# ---------- A 自动保存 ----------
def check_autosave():
    reset(); p = F / "notes.txt"; p.write_bytes(b"alpha\nbeta\n")
    open_editor(p); pyautogui.hotkey(MOD, "end") if not MAC else pyautogui.hotkey("command", "down"); time.sleep(.5)
    pyautogui.typewrite("ZZZ", interval=.08); time.sleep(1); shot("A-typed")
    time.sleep(90); after_wait = p.read_bytes()
    pyautogui.hotkey(MOD, "w"); time.sleep(4); shot("A-after-close")
    # gedit/记事本会弹"要保存吗"——记录弹没弹,然后选不保存
    if not MAC:
        if WIN: pyautogui.press("n")
        else: pyautogui.press("enter") if False else pyautogui.hotkey("alt", "w")   # gedit: "Close without Saving" 的助记键 w
        time.sleep(3)
    after_close = p.read_bytes(); kill_editor()
    R["checks"]["A_autosave"] = {"initial": "alpha\\nbeta\\n", "typed": "ZZZ",
        "disk_after_90s": after_wait.decode("utf-8", "replace"), "changed_after_90s": after_wait != b"alpha\nbeta\n",
        "disk_after_close_without_save": after_close.decode("utf-8", "replace"), "changed_after_close": after_close != b"alpha\nbeta\n"}
    log("A", json.dumps(R["checks"]["A_autosave"], ensure_ascii=False))

# ---------- B 打开中的文件改名 ----------
def check_lock():
    reset(); p = F / "doc.txt"; p.write_bytes(b"body\n")
    soffice = shutil.which("soffice") or shutil.which("libreoffice") or ("/Applications/LibreOffice.app/Contents/MacOS/soffice" if MAC else None) or (r"C:\Program Files\LibreOffice\program\soffice.exe" if WIN else None)
    info = {"soffice": soffice}
    if not soffice or not pathlib.Path(soffice).exists():
        R["checks"]["B_lock"] = dict(info, skipped="LibreOffice 不在"); log("B skip"); return
    proc = subprocess.Popen([soffice, "--writer", "--norestore", str(p)]); time.sleep(25); shot("B-open")
    info["lock_files"] = sorted(x.name for x in F.iterdir() if x.name.startswith(".~lock"))
    try: os.rename(p, F / "renamed.txt"); info["os_rename"] = "ok"
    except Exception as e: info["os_rename"] = "%s: %s" % (type(e).__name__, str(e)[:80])
    try: os.remove(F / "renamed.txt") if (F / "renamed.txt").exists() else None; info["delete_after"] = "n/a"
    except Exception as e: info["delete_after"] = type(e).__name__
    info["files_after"] = sorted(x.name for x in F.iterdir())
    proc.kill(); subprocess.run(["pkill", "-f", "soffice"] if not WIN else ["taskkill", "/F", "/IM", "soffice.bin"], capture_output=True); time.sleep(2)
    R["checks"]["B_lock"] = info; log("B", json.dumps(info, ensure_ascii=False))

# ---------- C 文件管理器敲名选中 + F2 ----------
def check_typeahead():
    reset(); (F / "alpha.txt").write_bytes(b"a\n"); (F / "beta.txt").write_bytes(b"b\n"); (F / "gamma.txt").write_bytes(b"g\n")
    if MAC: osa('tell application "Finder" to close every window'); subprocess.run(["open", str(F)]); time.sleep(4); osa('tell application "Finder" to activate'); time.sleep(1.5)
    elif WIN: subprocess.Popen(["explorer.exe", str(F)]); time.sleep(6)
    else: subprocess.Popen(["nautilus", "--new-window", str(F)]); time.sleep(7)
    pyautogui.click(600, 400); time.sleep(1); pyautogui.typewrite("beta", interval=.12); time.sleep(1.5); shot("C-after-typing")
    pyautogui.press("f2"); time.sleep(1.2); shot("C-after-f2"); pyautogui.hotkey(MOD, "a"); pyautogui.typewrite("delta.txt", interval=.05); pyautogui.press("enter"); time.sleep(2.5); shot("C-final")
    if MAC: pyautogui.press("enter"); time.sleep(1.5)   # 若弹 Keep/Use 追问
    files = sorted(x.name for x in F.iterdir())
    R["checks"]["C_typeahead_f2"] = {"files_after": files, "beta_renamed_to_delta": "delta.txt" in files and "beta.txt" not in files}
    if MAC: osa('tell application "Finder" to close every window')
    elif WIN: subprocess.run(["taskkill", "/F", "/IM", "explorer.exe"], capture_output=True); time.sleep(1); subprocess.Popen(["explorer.exe"])
    else: subprocess.run(["pkill", "-f", "nautilus"], capture_output=True)
    time.sleep(2); log("C", json.dumps(R["checks"]["C_typeahead_f2"], ensure_ascii=False))

# ---------- D 新建文件换行 ----------
def check_newline():
    reset(); target = F / "new.txt"
    kill_editor()
    if MAC: subprocess.Popen(["open", "-a", "TextEdit"]); time.sleep(8); osa('tell application "TextEdit" to activate'); time.sleep(1.5); pyautogui.hotkey("command", "n"); time.sleep(2); pyautogui.click(600, 400); time.sleep(1); pyautogui.hotkey("command", "shift", "t"); time.sleep(1)
    elif WIN: subprocess.Popen(["notepad.exe"]); time.sleep(6); pyautogui.click(600, 400); time.sleep(1)
    else: subprocess.Popen(["gedit", "--new-window"]); time.sleep(7); pyautogui.click(600, 400); time.sleep(1)
    for i, ln in enumerate(("one", "two", "three")):
        if i: pyautogui.press("enter"); time.sleep(.1)
        pyautogui.typewrite(ln, interval=.06)
    time.sleep(1); pyautogui.hotkey(MOD, "s"); time.sleep(3)
    if MAC:
        pyautogui.hotkey("command", "shift", "g"); time.sleep(1.5); pyautogui.typewrite(str(F), interval=.02); time.sleep(.8); pyautogui.press("enter"); time.sleep(1.5)
        pyautogui.hotkey("command", "a"); pyautogui.typewrite("new.txt", interval=.03); time.sleep(.5); pyautogui.press("enter"); time.sleep(3)
    elif WIN: pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite('"%s"' % target, interval=.02); time.sleep(.5); pyautogui.press("enter"); time.sleep(3)
    else: pyautogui.hotkey("ctrl", "a"); pyautogui.typewrite(str(target), interval=.02); time.sleep(.5); pyautogui.press("enter"); time.sleep(3)
    shot("D-saved"); raw = target.read_bytes() if target.exists() else b""; kill_editor()
    R["checks"]["D_newline"] = {"bytes": repr(raw), "crlf": b"\r\n" in raw, "files": sorted(x.name for x in F.iterdir())}
    log("D", json.dumps(R["checks"]["D_newline"], ensure_ascii=False))

# ---------- E 可执行位 ----------
def check_execbit():
    reset(); src = F / "tool.sh"; src.write_text("#!/bin/sh\necho ok\n"); os.chmod(src, 0o755)
    def mode(p): return oct(stat.S_IMODE(os.stat(p).st_mode))
    info = {"src": mode(src)}
    shutil.copy(src, F / "copy_plain.sh"); info["shutil.copy"] = mode(F / "copy_plain.sh")
    shutil.copy2(src, F / "copy2.sh"); info["shutil.copy2"] = mode(F / "copy2.sh")
    (F / "copy_bytes.sh").write_bytes(src.read_bytes()); info["write_bytes"] = mode(F / "copy_bytes.sh")
    with zipfile.ZipFile(F / "pkg.zip", "w") as z: z.write(src, "tool.sh")
    with zipfile.ZipFile(F / "pkg.zip") as z: z.extractall(F / "unz")
    info["zip_extract"] = mode(F / "unz" / "tool.sh")
    for name in ("copy_plain.sh", "copy_bytes.sh", "unz/tool.sh"):
        p = F / name
        try: r = subprocess.run([str(p)], capture_output=True, text=True, timeout=10); info["run " + name] = "rc=%s %s" % (r.returncode, (r.stdout + r.stderr).strip()[:40])
        except Exception as e: info["run " + name] = type(e).__name__
    info["access_X_OK copy_plain"] = os.access(F / "copy_plain.sh", os.X_OK)
    R["checks"]["E_execbit"] = info; log("E", json.dumps(info, ensure_ascii=False))

for name, fn in (("E", check_execbit), ("D", check_newline), ("A", check_autosave), ("C", check_typeahead), ("B", check_lock)):
    try: fn()
    except Exception as e:
        R["checks"].setdefault("errors", {})[name] = "%s: %s" % (type(e).__name__, e); log("!!", name, e)
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); log("PROBE-DONE", SYS)
