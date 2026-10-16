#!/usr/bin/env python3
"""环境维度标准 v1.0-draft 的配套工具（仅标准库，Python 3.8+）。

子命令：
  schema              生成环境声明的 JSON Schema
  check  SPEC         校验一份环境声明（取值合法、覆盖完整、组合约束）
  probe               在当前环境里实测能自动读出的子维度，输出 JSON
  verify SPEC PROBE   比对声明与实测，不一致即不合格
  expand POP          把"钉死 + 要变化"的总体声明展开成一批具体环境声明
  table               打印子维度一览（Markdown）
"""
import json, os, sys, itertools, random, platform, shutil, subprocess, socket, tempfile, time, locale as _locale, unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
REG = json.load(open(os.path.join(HERE, "dimensions.json"), encoding="utf-8"))
SD = {s["id"]: s for s in REG["subdimensions"]}
GUI_CHANNELS = {"gui-screenshot", "a11y-tree", "web-dom"}
STAGED_LAYER = "E5"          # 边界层允许按阶段取不同值
STAGES = ("setup", "agent", "verifier")


# ---------- 声明的读取与归一 ----------
def load(path):
    txt = open(path, encoding="utf-8").read()
    if path.endswith((".yaml", ".yml")):
        import yaml  # 可选依赖
        return yaml.safe_load(txt)
    return json.loads(txt)

def entry(v):
    """一个子维度的声明可以写成字符串，或 {value, concrete, by_stage, note}。"""
    return v if isinstance(v, dict) else {"value": v}

def in_scope(sid, env):
    scope = SD[sid]["scope"]
    ch = entry(env.get("E7.1.channel", SD["E7.1.channel"]["baseline"]))["value"]
    acc = entry(env.get("E1.2.type", "none"))["value"]
    if scope == "gui":  return ch in GUI_CHANNELS
    if scope == "web":  return ch in GUI_CHANNELS or ch == "api" and False
    if scope == "gpu":  return acc != "none"
    return True

def resolve(spec):
    """套上 OS 默认档：声明了 E2.1.os 但没写的捆绑子维度，取该 OS 的默认值。"""
    env = dict(spec.get("env", {}))
    osv = entry(env.get("E2.1.os", {"value": None}))["value"]
    filled = []
    for k, v in REG["os_profiles"].get(osv, {}).items():
        if k not in env:
            env[k] = {"value": v, "source": "os_profile"}; filled.append(k)
    return env, filled


# ---------- check ----------
def check(spec):
    errs, warns = [], []
    env, filled = resolve(spec)
    unspecified = set(spec.get("unspecified", []))
    for k in list(env) + list(unspecified):
        if k not in SD: errs.append(f"{k}: 不是标准里的子维度编号")
    for k, raw in env.items():
        if k not in SD: continue
        e, s = entry(raw), SD[k]
        vals = [e["value"]] + list((e.get("by_stage") or {}).values())
        for v in vals:
            if v not in s["values"] and not str(v).startswith("x-"):
                errs.append(f"{k}={v}: 不在取值表 {s['values']} 里。取值是类别，具体值（如 Asia/Shanghai、python3.8）写进 concrete；确实不在表里的用 x- 开头")
        if e.get("by_stage"):
            if s["layer"] != STAGED_LAYER: errs.append(f"{k}: 只有 E5 边界层可以按阶段取值")
            bad = set(e["by_stage"]) - set(STAGES)
            if bad: errs.append(f"{k}: 未知阶段 {sorted(bad)}，只能是 {STAGES}")
    # 完整性：范围内的核心子维度必须声明或显式列为未声明
    for k, s in SD.items():
        if not in_scope(k, env): continue
        if k in env or k in unspecified: continue
        (errs if s["status"] == "core" else warns).append(
            f"{k}（{s['dimension']}·{s['name']}）: 没声明，也没列进 unspecified")
    # 组合约束
    val = lambda k: entry(env[k])["value"] if k in env else None
    osv = val("E2.1.os")
    prof = REG["os_profiles"].get(osv, {})
    for k, v in prof.items():
        if SD[k]["settable"] == "host" and val(k) not in (None, v):
            errs.append(f"{k}={val(k)}: 只能换宿主改变，{osv} 上必然是 {v}")
    if val("E2.2.isolation") == "wsl" and osv != "linux":
        errs.append("E2.2.isolation=wsl: WSL 里跑的是 linux，E2.1.os 应写 linux，并在 note 里写明宿主是 Windows")
    if val("E3.3.shell") in ("powershell-5", "cmd") and osv != "windows":
        errs.append(f"E3.3.shell={val('E3.3.shell')}: 只存在于 Windows")
    if val("E3.3.toolchain") == "windows-native" and osv != "windows":
        errs.append("E3.3.toolchain=windows-native: 只存在于 Windows")
    if val("E1.1.arch") == "emulated-cross-arch":
        warns.append("E1.1.arch=emulated-cross-arch: 在 note 里写明宿主架构和模拟层（qemu / Rosetta）")
    for k in ("E3.1.version",):
        if k in env and val(k) != "current" and not entry(env[k]).get("concrete"):
            warns.append(f"{k}={val(k)}: 相对取值，建议在 concrete 里写具体版本（如 python3.8）")
    cand = [k for k in env if k in SD and SD[k]["status"] == "candidate"]
    if cand:
        warns.append(f"声明了 {len(cand)} 个候选子维度（{', '.join(cand)}）：可以用，但它们上面的结论不作为核心证据")
    return errs, warns, filled


# ---------- expand ----------
def expand(pop):
    """pop = {name, base:{env,unspecified}, vary:{sid:[values]}, mode:grid|random, n, seed, exclude:[{sid:v,...}]}"""
    base = pop["base"]
    if "$from" in base:  # 从一份具体声明继承底座
        b = load(os.path.join(pop.get("_dir", "."), base["$from"]))
        base = {"env": b.get("env", {}), "unspecified": b.get("unspecified", [])}
    vary = pop.get("vary", {})
    varies = pop.get("varies_unenumerated", [])  # 在总体里会变、但取值没枚举（如 1 万个基础镜像带来的版本）
    keys = sorted(vary)
    combos = list(itertools.product(*[vary[k] for k in keys]))
    if pop.get("mode", "grid") == "random":
        random.Random(pop.get("seed", 0)).shuffle(combos); combos = combos[: pop.get("n", len(combos))]
    out = []
    for c in combos:
        env = dict(base.get("env", {}))
        for k, v in zip(keys, c):
            env[k] = v
        if any(all(entry(env.get(k, {"value": None}))["value"] == v for k, v in ex.items()) for ex in pop.get("exclude", [])):
            continue
        name = pop["name"] + "/" + ",".join(f"{k}={v}" for k, v in zip(keys, c))
        spec = {"spec_version": REG["version"], "name": name, "env": env,
                "unspecified": list(base.get("unspecified", [])) + list(varies)}
        e, _, _ = check(spec)
        out.append({"spec": spec, "valid": not e, "errors": e})
    return out


# ---------- probe：只读出能自动判定的子维度 ----------
def _run(cmd, t=5):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=t, shell=isinstance(cmd, str))
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as ex:
        return None, repr(ex)

def probe(workdir=None):
    wd = tempfile.mkdtemp(prefix="envprobe-", dir=workdir)
    R = {}
    def put(k, v, raw=None): R[k] = {"value": v, "raw": raw}
    sysname = platform.system().lower()
    osv = {"linux": "linux", "darwin": "macos", "windows": "windows"}.get(sysname, sysname)
    if osv == "linux" and (os.path.exists("/system/build.prop") or "ANDROID_ROOT" in os.environ): osv = "android"
    put("E2.1.os", osv, platform.platform())
    m = platform.machine().lower()
    put("E1.1.arch", {"amd64": "x86_64", "x86_64": "x86_64", "aarch64": "arm64", "arm64": "arm64", "riscv64": "riscv64"}.get(m, "x-" + m), m)
    # 跨架构模拟：macOS Rosetta
    if osv == "macos":
        c, o = _run(["sysctl", "-n", "sysctl.proc_translated"])
        if o.strip() == "1": put("E1.1.arch", "emulated-cross-arch", "rosetta")
    # 加速器
    if shutil.which("nvidia-smi"):
        c, o = _run(["nvidia-smi", "--query-gpu=name,driver_version", "--format=csv,noheader"])
        gpus = [l for l in o.splitlines() if l.strip()] if c == 0 else []
        put("E1.2.type", "nvidia" if gpus else "none", o[:200])
        if gpus: put("E1.2.count", "multi" if len(gpus) > 1 else "single", len(gpus))
    elif shutil.which("rocm-smi"):
        put("E1.2.type", "amd-rocm", _run(["rocm-smi", "--showproductname"])[1][:200])
    elif osv == "macos" and m == "arm64":
        put("E1.2.type", "apple-metal", "apple silicon")
    else:
        put("E1.2.type", "none")
    # 文件系统语义（在工作目录上测）
    a = os.path.join(wd, "CaseProbe"); open(a, "w").close()
    put("E2.3.case", "insensitive" if os.path.exists(os.path.join(wd, "caseprobe")) else "sensitive")
    nfc = unicodedata.normalize("NFC", "é"); nfd = unicodedata.normalize("NFD", "é")
    try:
        open(os.path.join(wd, "u" + nfc), "w").close()
        listed = [n for n in os.listdir(wd) if n.startswith("u")][0]
        hit = os.path.exists(os.path.join(wd, "u" + nfd))
        if listed == "u" + nfd: v = "nfd-normalizing"
        elif hit: v = "normalization-insensitive"
        else: v = "none"
        put("E2.3.unicode", v, {"listed_is_nfc": listed == "u" + nfc, "nfd_lookup_hits": hit})
    except (OSError, UnicodeError) as ex:  # a non-UTF-8 file-system encoding cannot name the test file
        put("E2.3.unicode", None, repr(ex))
    try:
        open(os.path.join(wd, "a" * 256), "w").close(); ln = "long"
    except OSError:
        ln = "name-255-bytes"
    if osv == "windows":
        c, o = _run('reg query HKLM\\SYSTEM\\CurrentControlSet\\Control\\FileSystem /v LongPathsEnabled')
        if "0x0" in o: ln = "win-max-path-260"
    put("E2.3.length", ln)
    try:
        open(os.path.join(wd, "aux.txt"), "w").close(); sn = "posix"
    except OSError:
        sn = "win-reserved"
    put("E2.3.special_names", sn)
    put("E2.4.line_ending", "crlf" if os.linesep == "\r\n" else "lf")
    put("E2.4.path_sep", "backslash" if os.sep == "\\" else "slash")
    if osv in ("linux", "android"):
        caps = [("no-nested-virt", "/dev/kvm"), ("no-fuse", "/dev/fuse"), ("no-loop-mount", "/dev/loop-control")]
        missing = [v for v, p in caps if not os.path.exists(p)]
        put("E2.5.kernel_caps", missing[0] if missing else "full", {"missing": missing})
    # 软件栈
    put("E3.1.version", None, {"python": platform.python_version(), "note": "相对取值，verify 时与声明里的 concrete 比"})
    ent = {n: bool(shutil.which(n)) for n in ("python", "python3", "pip", "pip3", "node", "npm")}
    put("E3.1.entry_name", "canonical" if ent["python"] and ent["python3"] else "alias-missing", ent)
    idx = os.environ.get("PIP_INDEX_URL") or _run([sys.executable, "-m", "pip", "config", "get", "global.index-url"])[1]
    idx = idx if idx and idx.startswith("http") else None
    put("E3.2.package_source", "internal-mirror" if idx and "pypi.org" not in idx and idx.startswith("http") else "public-registry", idx[:200] if idx else None)
    bt = {n: bool(shutil.which(n)) for n in ("cc", "gcc", "clang", "make", "cl")}
    put("E3.2.build_tools", "present" if bt["make"] and (bt["cc"] or bt["gcc"] or bt["clang"] or bt["cl"]) else "absent", bt)
    if osv == "windows" and not shutil.which("sed"): tc = "windows-native"
    else:
        c, o = _run("sed --version")
        # BusyBox 的 sed --version 输出 "This is not GNU sed"，必须先判 BusyBox
        rp = os.path.realpath(shutil.which("sed") or "")
        if "toybox" in rp or "toybox" in o.lower(): tc = "toybox"
        elif "busybox" in rp or "BusyBox" in o or "not GNU" in o: tc = "busybox"
        elif "GNU" in o: tc = "gnu"
        else: tc = "bsd" if shutil.which("sed") else "x-none"
    put("E3.3.toolchain", tc)
    if osv == "windows":
        sh = "powershell-7" if "PowerShell\\7" in os.environ.get("PSModulePath", "") else ("powershell-5" if os.environ.get("PSModulePath") else "cmd")
    else:
        sh = os.path.basename(os.environ.get("SHELL", "sh"))
        sh = {"bash": "bash", "zsh": "zsh", "fish": "fish", "dash": "sh-dash", "sh": "sh-dash", "mksh": "mksh", "pwsh": "powershell-7"}.get(sh, "x-" + sh)
    put("E3.3.shell", sh, {"SHELL": os.environ.get("SHELL"), "note": "读的是登录 shell；harness 实际用哪个 shell 执行命令要看 harness"})
    # 执行上下文
    enc = _locale.getpreferredencoding(False).lower().replace("_", "-")
    put("E4.1.encoding", {"utf-8": "utf-8", "cp1252": "cp1252", "gbk": "gbk", "cp936": "gbk", "cp950": "cp950", "big5": "cp950"}.get(enc, "x-" + enc), enc)
    lc = os.environ.get("LC_ALL") or os.environ.get("LC_CTYPE") or os.environ.get("LANG") or ""
    lcv = "C.UTF-8" if lc in ("", "C", "POSIX", "C.UTF-8", "C.utf8", "UTF-8") else next((v for v in ("en_US", "de_DE", "tr_TR", "zh_CN") if lc.startswith(v)), "x-" + lc)
    put("E4.1.locale", lcv, lc)
    off = [time.altzone, time.timezone]
    if time.timezone == 0 and not time.daylight: tz = "UTC"
    elif time.timezone % 3600: tz = "half-hour-offset-zone"
    elif time.daylight: tz = "dst-zone"
    else: tz = "fixed-offset-zone"
    put("E4.1.timezone", tz, {"tzname": time.tzname, "offset_s": -time.timezone, "TZ": os.environ.get("TZ")})
    if hasattr(os, "geteuid"):
        put("E4.2.identity", "root" if os.geteuid() == 0 else "unprivileged-user", os.geteuid())
    else:
        c, o = _run("net session")
        put("E4.2.identity", "root" if c == 0 else "unprivileged-user", "windows admin" if c == 0 else "non-admin")
    put("E4.2.tty", "pty" if sys.stdin.isatty() else "no-tty")
    # 边界
    if osv in ("linux", "macos", "android"):
        if os.geteuid() == 0: pv = "full"
        elif shutil.which("sudo") and _run(["sudo", "-n", "true"])[0] == 0: pv = "sudo-nopasswd"
        else: pv = "no-sudo"
        put("E5.1.permissions", pv)
        t = os.path.join(tempfile.gettempdir(), "envprobe_exec.sh")
        try:
            open(t, "w").write("#!/bin/sh\nexit 0\n"); os.chmod(t, 0o755)
            put("E5.1.mount", "normal" if _run([t])[0] == 0 else "tmp-noexec"); os.remove(t)
        except OSError as ex:
            put("E5.1.mount", None, repr(ex))
    def reach(host, port=443, t=4):
        try:
            socket.create_connection((host, port), timeout=t).close(); return True
        except OSError:
            return False
    try:
        socket.getaddrinfo("pypi.org", 443); dns_ok = True
    except OSError:
        dns_ok = False
    targets = {h: reach(h) for h in ("pypi.org", "github.com", "example.com")}
    if all(targets.values()): eg = "online"
    elif not any(targets.values()): eg = "proxy-required" if os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy") else "offline"
    else: eg = "allowlist"
    put("E5.2.egress", eg, targets)
    put("E5.2.dns", "normal" if dns_ok else "servfail", dns_ok)
    # 时钟：联网时和 HTTP Date 头比（走 http：时钟偏了 https 证书校验本身会失败），离线读不出
    skew = None
    if targets.get("example.com"):
        try:
            import urllib.request, email.utils
            d = urllib.request.urlopen("http://example.com", timeout=5).headers["Date"]
            skew = time.time() - email.utils.parsedate_to_datetime(d).timestamp()
        except Exception:
            pass
    t1 = time.time(); time.sleep(0.2); frozen = time.time() - t1 < 0.05
    if frozen: cv = "frozen"
    elif skew is None: cv = None
    elif skew > 180 * 86400: cv = "future+1y"
    elif skew < -180 * 86400: cv = "past-1y"
    elif abs(skew) < 300: cv = "synced"
    else: cv = "x-skew-%ds" % int(skew)
    put("E5.3.clock", cv, {"skew_s": skew})
    shutil.rmtree(wd, ignore_errors=True)
    return {"standard": REG["version"], "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "readings": R}


# ---------- verify ----------
def verify(spec, pr, stage="agent"):
    env, _ = resolve(spec)
    rows, fails = [], 0
    for k, r in pr["readings"].items():
        if k not in env:
            rows.append((k, "（未声明）", r["value"], "—")); continue
        e = entry(env[k]); want = (e.get("by_stage") or {}).get(stage, e["value"])
        got = r["value"]
        if k == "E3.1.version":
            c = e.get("concrete"); ok = None if not c else (r["raw"]["python"].startswith(c.replace("python", "").strip()) if "python" in c else None)
        elif got is None: ok = None
        else: ok = (got == want)
        if k == "E3.1.version": got = "python" + r["raw"]["python"]
        if ok is False: fails += 1
        rows.append((k, want, got, {True: "一致", False: "不一致", None: "读不出"}[ok]))
    return fails, rows


def table():
    print("| 编号 | 维度 | 子维度 | 取值（首个为基准） | 准入 | 设置方式 | 自动探测 | 被当自变量 |")
    print("|---|---|---|---|---|---|---|---|")
    for s in REG["subdimensions"]:
        print(f"| {s['id']} | {s['dimension']} | {s['name']} | {' / '.join(s['values'])} | {'核心' if s['status']=='core' else '候选'} | {s['settable']} | {'是' if s['probe']=='auto' else '否'} | {'★' if s['varied_as_iv'] else ''} |")


def schema():
    props = {}
    for s in REG["subdimensions"]:
        enum = {"anyOf": [{"enum": s["values"]}, {"type": "string", "pattern": "^x-"}]}
        props[s["id"]] = {"description": f"{s['layer']} {s['dimension']}·{s['name']}（{s['status']}）",
            "anyOf": [enum, {"type": "object", "required": ["value"], "properties": {
                "value": enum, "concrete": {"type": "string"}, "note": {"type": "string"},
                **({"by_stage": {"type": "object", "propertyNames": {"enum": list(STAGES)}, "additionalProperties": enum}} if s["layer"] == STAGED_LAYER else {})},
                "additionalProperties": False}]}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": "Agent 环境声明 " + REG["version"],
        "type": "object", "required": ["spec_version", "name", "env"],
        "properties": {"spec_version": {"const": REG["version"]}, "name": {"type": "string"}, "note": {"type": "string"},
            "env": {"type": "object", "properties": props, "additionalProperties": False},
            "unspecified": {"type": "array", "items": {"enum": list(SD)}}},
        "additionalProperties": False}


def main(a):
    if not a: print(__doc__); return 1
    cmd = a[0]
    if cmd == "schema": print(json.dumps(schema(), ensure_ascii=False, indent=1)); return 0
    if cmd == "table": table(); return 0
    if cmd == "probe": print(json.dumps(probe(), ensure_ascii=False, indent=1)); return 0
    if cmd == "check":
        e, w, f = check(load(a[1]))
        if f: print("按 OS 默认档补上:", ", ".join(f))
        for x in e: print("错误 ", x)
        for x in w: print("提醒 ", x)
        print("合格" if not e else f"不合格（{len(e)} 个错误）"); return 1 if e else 0
    if cmd == "verify":
        stage = a[3] if len(a) > 3 else "agent"
        n, rows = verify(load(a[1]), load(a[2]), stage)
        print(f"| 子维度 | 声明（{stage} 阶段） | 实测 | 结论 |\n|---|---|---|---|")
        for r in rows: print("| " + " | ".join(str(x) for x in r) + " |")
        print("\n声明与实测一致" if not n else f"\n{n} 处不一致：这个环境不是它声明的那个"); return 1 if n else 0
    if cmd == "expand":
        pop = load(a[1]); pop["_dir"] = os.path.dirname(os.path.abspath(a[1]))
        out = expand(pop)
        bad = [o for o in out if not o["valid"]]
        for o in bad[:5]: print("不合法:", o["spec"]["name"], o["errors"][:3], file=sys.stderr)
        print(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"# 展开 {len(out)} 个，合法 {sum(o['valid'] for o in out)} 个", file=sys.stderr); return 0
    print(__doc__); return 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
