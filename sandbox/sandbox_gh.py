#!/usr/bin/env python3
"""Runner-side realisation and verification of the OS-level sandbox variants (env-suite, TraceLite).
  python sandbox_gh.py setup <id>            # variant-specific setup; prints KEY=VALUE lines for $GITHUB_ENV
  python sandbox_gh.py check <id> probe.json # compare probe readings with the expectation, run the extra check
Only the environment probe (envstd.py) and these settings live here; no benchmark tasks."""
import json, os, platform, subprocess, sys

V = {
 "gh-arm64":     {"expect": {"E1.1.arch": "arm64", "E2.1.os": "linux"}},
 "gh-macos":     {"expect": {"E2.1.os": "macos"}},
 "gh-windows":   {"expect": {"E2.1.os": "windows"}},
 "gh-unicode-ni":{"expect": {"E2.3.unicode": "normalization-insensitive"}},
 "gh-unicode-nfd":{"expect": {"E2.3.unicode": "nfd-normalizing"}},
 "gh-winmaxpath":{"expect": {"E2.3.length": "win-max-path-260"}},
 "gh-winreserved":{"expect": {"E2.3.special_names": "win-reserved"}},
 "gh-backslash": {"expect": {"E2.4.path_sep": "backslash"}},
 "gh-bsd":       {"expect": {"E3.3.toolchain": "bsd"}},
 "gh-winnative": {"expect": {"E3.3.toolchain": "windows-native"}},
 "gh-ps5":       {"expect": {"E3.3.shell": "powershell-5"}},
 "gh-cmd":       {"expect": {"E3.3.shell": "cmd"}},
 "gh-cp1252":    {"expect": {"E4.1.encoding": "cp1252"}},
 "gh-kc-full":   {"expect": {"E2.5.kernel_caps": "full"}},
 "gh-kc-nofuse": {"expect": {"E2.5.kernel_caps": "no-fuse"}},
 "gh-kc-noloop": {"expect": {"E2.5.kernel_caps": "no-loop-mount"}},
 "gh-bare":      {"expect": {"E2.1.os": "linux"}, "check": "bare"},
 "gh-wsl":       {"expect": {"E2.1.os": "linux"}, "check": "wsl"},
 "gh-vm":        {"expect": {"E2.1.os": "linux"}, "check": "vm"},
}

def setup(vid):
    out = []
    if vid == "gh-unicode-nfd":
        subprocess.run(["hdiutil", "create", "-size", "64m", "-fs", "HFS+", "-volname", "nfdvol", "/tmp/nfd.dmg"], check=True)
        subprocess.run(["hdiutil", "attach", "/tmp/nfd.dmg"], check=True)
        os.makedirs("/Volumes/nfdvol/tmp", exist_ok=True); out.append("TMPDIR=/Volumes/nfdvol/tmp")
    if vid == "gh-winmaxpath":
        subprocess.run('reg add HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled /t REG_DWORD /d 0 /f', shell=True, check=True)
    if vid == "gh-winnative":
        py = os.path.dirname(sys.executable)
        out.append(f"SANDBOX_PATH={py};{py}\\Scripts;C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\WindowsPowerShell\\v1.0")
    if vid == "gh-kc-full" and os.path.exists("/dev/kvm"):
        subprocess.run(["sudo", "chmod", "666", "/dev/kvm"])
    return out

def extra_check(kind):
    if kind == "bare":
        cg = open("/proc/1/cgroup").read() if os.path.exists("/proc/1/cgroup") else ""
        return (not os.path.exists("/.dockerenv")) and "docker" not in cg, "no container layer between the agent and the runner OS"
    if kind == "wsl":
        v = open("/proc/version").read(); return "microsoft" in v.lower(), v.strip()[:120]
    if kind == "vm":
        r = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True); return r.stdout.strip() in ("kvm", "qemu"), r.stdout.strip()
    return True, ""

def check(vid, probe_path):
    raw = json.load(open(probe_path, encoding="utf-8")); pr = raw["readings"]
    exp = V[vid]["expect"]; got = {k: pr.get(k, {}).get("value") for k in exp}
    ok = all(got[k] == v for k, v in exp.items())
    note = ""
    if V[vid].get("check") == "vm":            # read inside the guest, not on the runner (itself an Azure VM)
        c = raw.get("virt") in ("kvm", "qemu"); note = f"guest systemd-detect-virt={raw.get('virt')}"; ok = ok and c
    elif V[vid].get("check"):
        c, note = extra_check(V[vid]["check"]); ok = ok and c
    res = {"id": vid, "ok": ok, "expect": exp, "got": got, "note": note,
           "all_readings": {k: x.get("value") for k, x in pr.items()}, "platform": platform.platform()}
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open(f"verify-{vid}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 0 if ok else 1

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "setup": print("\n".join(setup(a[1])))
    elif a[0] == "check": sys.exit(check(a[1], a[2]))
