#!/usr/bin/env python3
"""三系统行为定向探针(第三轮):只测第二轮筛出来「疑似静默、需再确认」的点。

★与第二轮的两点不同:
1. shell 探针一律显式找 sh / bash 可执行文件(Windows 上是 Git 自带的),不用 shell=True——
   第二轮 shell=True 在 Windows 落到 cmd.exe,把一堆 cmd 的响错当成了 sh 的差异。
2. 工作流**不设 PYTHONUTF8**,量 Windows 默认编码下 open()/subprocess text=True 的真实行为;
   本脚本只把自己的 stdout 钉成 UTF-8 免得报告本身崩掉。
"""
import os, sys, shutil, subprocess, tempfile, pathlib, stat, time, signal, glob, locale, json

for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

IS_WIN = os.name == "nt"
OUT = []
W = pathlib.Path(tempfile.mkdtemp(prefix="probe3_"))

def rec(k, v): OUT.append((k, str(v).replace("\n", "\\n").replace("\t", " ")[:160]))
def probe(k, fn):
    try: rec(k, fn())
    except Exception as e: rec(k, f"<{type(e).__name__}: {str(e)[:80]}>")

def find_shell(name):
    p = shutil.which(name)
    if p: return p
    for c in [rf"C:\Program Files\Git\usr\bin\{name}.exe", rf"C:\Program Files\Git\bin\{name}.exe"]:
        if os.path.exists(c): return c
    return None

SH, BASH = find_shell("sh"), find_shell("bash")
rec("S00_sh_path", SH); rec("S00_bash_path", BASH)

def sh(script, shell=None, cwd=None, env_extra=None):
    exe = shell or SH
    if not exe: return "<无 sh>"
    env = dict(os.environ); env.update(env_extra or {})
    r = subprocess.run([exe, "-c", script], capture_output=True, timeout=60, cwd=cwd or str(W), env=env)
    o = r.stdout.decode("utf-8", "replace").strip()
    e = r.stderr.decode("utf-8", "replace").strip()
    return (o if o else "") + (f" [stderr:{e[:70]}]" if e else "") + (f" [rc={r.returncode}]" if r.returncode else "")

# ── S: /bin/sh 方言(Linux=dash, mac=bash3.2 sh 模式, Win=Git bash) ─────────
probe("S01_sh_brace_expand", lambda: sh('echo {1..3} x{a,b}'))
probe("S02_sh_echo_dash_e", lambda: sh('echo -e "a\\tb"'))
probe("S03_sh_echo_backslash_plain", lambda: sh('echo "a\\tb"'))
probe("S04_sh_RANDOM_len", lambda: sh('printf "%s" "$RANDOM" | wc -c | tr -d " "'))
probe("S05_sh_substring", lambda: sh('x=hello; echo ${x:0:3}'))
probe("S06_sh_double_eq", lambda: sh('x=1; [ "$x" == 1 ] && echo eq'))
probe("S07_sh_pipefail", lambda: sh('set -o pipefail 2>/dev/null && echo ok || echo no'))
probe("S08_sh_printf_octal08", lambda: sh('printf "%d\\n" 08'))
probe("S09_sh_dollar_quote", lambda: sh("printf '%s' $'a\\nb' | wc -l | tr -d ' '"))
probe("S10_sh_local_arrays", lambda: sh('a=(1 2); echo ${a[1]}'))
probe("S11_sh_version_hint", lambda: sh('echo "${BASH_VERSION:-no-bash}"'))
probe("S12_bash_version", lambda: sh('echo "$BASH_VERSION"', shell=BASH))
probe("S13_bash_assoc", lambda: sh('declare -A m; m[k]=v; echo ${m[k]}', shell=BASH))
probe("S14_bash_lowercase_op", lambda: sh('x=ABC; echo ${x,,}', shell=BASH))
probe("S15_bash_mapfile", lambda: sh('printf "a\\nb\\n" | { mapfile -t L; echo ${#L[@]}; }', shell=BASH))

# ── T: 常用命令的 GNU/BSD 分叉 ───────────────────────────────────────────
probe("T01_date_N", lambda: sh('date +%s%N | tail -c 4'))
probe("T02_date_d", lambda: sh('date -u -d @86400 +%Y-%m-%d 2>&1'))
probe("T03_xargs_empty", lambda: sh('printf "" | xargs echo EMPTY'))
probe("T04_xargs_r", lambda: sh('printf "" | xargs -r echo EMPTY; echo rc=$?'))
probe("T05_sort_default_under_sh", lambda: sh('printf "b\\nA\\na\\nB\\n" | sort | tr "\\n" " "'))
probe("T06_sort_C_under_sh", lambda: sh('printf "b\\nA\\na\\nB\\n" | LC_ALL=C sort | tr "\\n" " "'))
probe("T07_locale_env", lambda: sh('echo "LANG=$LANG LC_ALL=$LC_ALL LC_COLLATE=$LC_COLLATE LC_CTYPE=$LC_CTYPE"'))
probe("T08_sort_which", lambda: sh('command -v sort; sort --version 2>&1 | head -1'))
probe("T09_sed_i_noarg", lambda: sh('printf "a\\n" > f1; sed -i "s/a/b/" f1 2>&1; cat f1; ls f1* | tr "\\n" " "'))
probe("T10_readlink_f", lambda: sh('readlink -f . 2>&1 | tail -c 40'))
probe("T11_cp_trailing_slash", lambda: sh('mkdir -p src dst; echo x > src/f; cp -r src/ dst; find dst -type f | sort | tr "\\n" " "'))
probe("T12_ln_sf_onto_dirlink", lambda: sh('mkdir -p d1 d2; ln -s d1 L; ln -sf d2 L; readlink L; ls d1 | tr "\\n" " "'))
probe("T13_tar_entries", lambda: sh('mkdir -p td; echo x > td/f; tar czf t.tgz td; tar tzf t.tgz | tr "\\n" " "; tar --version 2>&1 | head -1 | cut -c1-20'))
probe("T14_timeout_cmd", lambda: sh('timeout 1 sleep 0 2>&1; echo rc=$?'))
probe("T15_sha256sum", lambda: sh('printf "" | sha256sum 2>&1 | cut -c1-12'))
probe("T16_md5", lambda: sh('printf "" | md5sum 2>&1 | cut -c1-12; printf "" | md5 2>&1 | cut -c1-12'))
probe("T17_stat_size", lambda: sh('echo abc > sf; stat -c %s sf 2>&1; stat -f %z sf 2>&1'))
probe("T18_pwd_P_tmp", lambda: sh('cd "$(dirname "$(mktemp -u)")" && echo "$(pwd) | $(pwd -P)"'))
probe("T19_mktemp_shape", lambda: sh('mktemp -d | sed "s/[A-Za-z0-9_]*$/X/"'))
probe("T20_rev_cmd", lambda: sh('printf abc | rev 2>&1'))
probe("T21_grep_P", lambda: sh('echo a1 | grep -oP "\\d" 2>&1'))
probe("T22_du_b", lambda: sh('du -sb . 2>&1 | head -c 30'))
probe("T23_touch_d", lambda: sh('touch tf; touch -d "2020-01-02 03:04:05" tf 2>&1; ls -l tf | awk "{print \\$6,\\$7,\\$8}"'))
probe("T24_find_mixed_sep", lambda: sh('mkdir -p fd; touch fd/g; find fd -type f'))
probe("T25_trailing_space_name_bash", lambda: sh('echo hi > "sp1 "; ls | grep -c "^sp1"; ls sp1* | od -c | head -1 | cut -c1-40'))
probe("T26_which_python", lambda: sh('command -v python3 python | tr "\\n" " "'))
probe("T27_python_platform_via_sh", lambda: sh('python3 -c "import sys;print(sys.platform)" 2>&1 || python -c "import sys;print(sys.platform)"'))
probe("T28_head_c_neg", lambda: sh('printf abcdef | head -c -2 2>&1'))
probe("T29_seq_fmt", lambda: sh('seq -w 1 3 | tr "\\n" " "'))
probe("T30_cut_output_delim", lambda: sh('echo "a b" | cut -d" " -f1,2 --output-delimiter=, 2>&1'))
probe("T31_awk_version", lambda: sh('awk --version 2>&1 | head -1 | cut -c1-30; awk -W version 2>&1 | head -1 | cut -c1-30'))
probe("T32_awk_asort", lambda: sh('echo | awk "{a[1]=3;a[2]=1; n=asort(a); print n, a[1]}" 2>&1'))
probe("T33_sed_E_vs_r", lambda: sh('echo aab | sed -E "s/a+/X/" 2>&1; echo aab | sed -r "s/a+/X/" 2>&1'))
probe("T34_sed_insert_i", lambda: sh('printf "x\\n" | sed "1i\\\\\\nhead" 2>&1 | tr "\\n" "|"'))
probe("T35_echo_n_in_sh", lambda: sh('echo -n abc | od -c | head -1 | cut -c1-30'))
probe("T36_ls_color_default", lambda: sh('touch lsx; ls lsx | od -c | head -1 | cut -c1-40'))
probe("T37_getconf_argmax", lambda: sh('getconf ARG_MAX 2>&1'))
probe("T38_uname", lambda: sh('uname -s'))

# ── P: Python 层静默点 ─────────────────────────────────────────────────────
probe("P01_tempdir_is_canonical", lambda: (tempfile.gettempdir(), str(pathlib.Path(tempfile.gettempdir()).resolve()) == tempfile.gettempdir()))
probe("P02_realpath_of_tempdir", lambda: os.path.realpath(tempfile.gettempdir()))
probe("P03_relpath_resolve_vs_raw", lambda: os.path.relpath(str((W / "z.txt").resolve()), str(W)) if (W / "z.txt").write_bytes(b"1") or True else "")
probe("P04_preferred_encoding_noutf8", lambda: locale.getpreferredencoding(False))
def enc_roundtrip(s):
    p = W / "enc.txt"
    with open(p, "w") as f: f.write(s)
    raw = p.read_bytes()
    return f"{raw!r} back_utf8={raw.decode('utf-8', 'replace')!r}"
probe("P05_open_default_write_e_acute", lambda: enc_roundtrip("café"))
probe("P06_open_default_write_cjk", lambda: enc_roundtrip("中文"))
def sub_text_decode():
    r = subprocess.run([sys.executable, "-c", "import sys;sys.stdout.buffer.write('caf\\u00e9\\n'.encode('utf-8'))"], capture_output=True, text=True)
    return repr(r.stdout.strip())
probe("P07_subprocess_text_decode_utf8_child", sub_text_decode)
def sub_bytes_newline():
    r = subprocess.run([sys.executable, "-c", "print('x')"], capture_output=True)
    return repr(r.stdout)
probe("P08_subprocess_stdout_bytes_newline", sub_bytes_newline)
probe("P09_path_eq_case", lambda: len({pathlib.Path("A.txt"), pathlib.Path("a.txt")}))
probe("P10_glob_case", lambda: ((W / "gc.txt").write_bytes(b"1"), [os.path.basename(x) for x in glob.glob(str(W / "GC.TXT"))])[-1])
probe("P11_fnmatch_case", lambda: __import__("fnmatch").fnmatch("a.txt", "A.TXT"))
probe("P12_isabs_slash", lambda: os.path.isabs("/data"))
probe("P13_expandvars_styles", lambda: os.path.expandvars("$HOME|%HOME%")[:60])
def killed_rc():
    p = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
    time.sleep(0.5); os.kill(p.pid, signal.SIGTERM); return p.wait(timeout=10)
probe("P14_sigterm_returncode", killed_rc)
def kill_rc():
    p = subprocess.Popen([sys.executable, "-c", "import time;time.sleep(30)"])
    time.sleep(0.5); p.kill(); return p.wait(timeout=10)
probe("P15_popen_kill_returncode", kill_rc)
def child_exit_neg():
    r = subprocess.run([sys.executable, "-c", "import sys;sys.exit(-1)"]); return r.returncode
probe("P16_child_exit_minus1", child_exit_neg)
def child_exit_256():
    r = subprocess.run([sys.executable, "-c", "import sys;sys.exit(256)"]); return r.returncode
probe("P17_child_exit_256", child_exit_256)
def append_tell():
    p = W / "ap.txt"; p.write_bytes(b"12345")
    with open(p, "a") as f: return f.tell()
probe("P18_append_mode_tell", append_tell)
def sleep_granularity():
    t = time.perf_counter()
    for _ in range(10): time.sleep(0.001)
    return round((time.perf_counter() - t) * 1000, 1)
probe("P19_sleep_1ms_x10_ms", sleep_granularity)
probe("P20_long_path_300", lambda: ((W / ("d" * 120) / ("e" * 120) / "f.txt").parent.mkdir(parents=True, exist_ok=True), (W / ("d" * 120) / ("e" * 120) / "f.txt").write_bytes(b"1"), "ok")[-1])
probe("P21_normcase", lambda: os.path.normcase("A/B.TXT"))
probe("P22_mtime_ns_roundtrip_100ns", lambda: (lambda p: (os.utime(p, ns=(1234567891234567891, 1234567891234567891)), p.stat().st_mtime_ns)[-1])((W / "ut.txt")) if (W / "ut.txt").write_bytes(b"1") or True else "")
probe("P23_env_pathsep_split", lambda: (os.pathsep, os.pathsep.join([str(W), str(W / "x")]).split(":")[:3]))
probe("P24_shutil_which_no_ext", lambda: (shutil.which("python") or "")[-14:])
def case_lookup():
    (W / "CaseLook.txt").write_bytes(b"1")
    return (W / "caselook.txt").exists(), sorted(x.name for x in W.iterdir() if x.name.lower() == "caselook.txt")
probe("P25_case_lookup_and_listing", case_lookup)
def case_collide_content():
    (W / "Col.txt").write_bytes(b"FIRST"); (W / "col.txt").write_bytes(b"SECOND")
    return (W / "Col.txt").read_bytes().decode(), sum(1 for x in W.iterdir() if x.name.lower() == "col.txt")
probe("P26_case_collide_content", case_collide_content)
probe("P27_os_environ_key_case_get", lambda: (os.environ.__setitem__("Probe3Key", "v"), os.environ.get("PROBE3KEY"), "Probe3Key" in dict(os.environ), sorted(k for k in os.environ if k.lower() == "probe3key"))[1:])
def env_dup_keys_to_child():
    env = dict(os.environ); env["PROBE3DUP"] = "upper"; env["probe3dup"] = "lower"
    r = subprocess.run([sys.executable, "-c", "import os;print(os.environ.get('PROBE3DUP'), os.environ.get('probe3dup'))"], capture_output=True, text=True, env=env)
    return r.stdout.strip() or r.stderr.strip()[:80]
probe("P28_env_dup_case_keys_child", env_dup_keys_to_child)
probe("P29_argv_backslash_to_bash", lambda: sh('printf "%s" "$1"', shell=BASH) if False else (subprocess.run([BASH, "-c", 'printf "%s" "$1"', "_", r"a\x41\\b\"c"], capture_output=True).stdout.decode("utf-8", "replace") if BASH else "<无 bash>"))
probe("P30_argv_quotes_to_bash", lambda: subprocess.run([BASH, "-c", 'printf "%s" "$1"', "_", 'say "hi" it\'s'], capture_output=True).stdout.decode("utf-8", "replace") if BASH else "<无 bash>")
probe("P31_argv_script_to_bash_c", lambda: subprocess.run([BASH, "-c", 'printf "%s\\n" "x\\ty" | od -c | head -1 | cut -c1-30'], capture_output=True).stdout.decode("utf-8", "replace").strip() if BASH else "<无 bash>")

print("== ENVSHIFT-PROBE3 ==")
for k, v in OUT: print(f"{k}\t{v}")
print("== END ==")
shutil.rmtree(W, ignore_errors=True)
