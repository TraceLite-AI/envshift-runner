#!/usr/bin/env python3
"""三系统行为大探针(第二轮):一次量一百多个行为点,专找「静默差异」当造题机制。

第一轮只量了 40 个维度,已用掉 5 条。题量的瓶颈是机制数量不是造题速度,所以先扩机制库。
每行输出 `KEY\t值`,三系统并排后取「三者不同或两者不同」且属静默的。
输出通道先加固(UTF-8),上一轮 Windows 整列丢失就是 cp1252 崩的。
"""
import os, sys, platform, subprocess, tempfile, pathlib, shutil, stat, time, json, glob, unicodedata, locale

for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

OUT = []
W = pathlib.Path(tempfile.mkdtemp(prefix="probe2_"))
IS_WIN = os.name == "nt"

def rec(k, v): OUT.append((k, str(v).replace("\n", "\\n").replace("\t", " ")[:150]))
def probe(k, fn):
    try: rec(k, fn())
    except Exception as e: rec(k, f"<{type(e).__name__}: {str(e)[:70]}>")

def mk(name, data=b"x"):
    p = W / name; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); return p

# ── A 路径与文件名语义 ──────────────────────────────────────────
probe("A01_realpath_dot", lambda: os.path.realpath(str(W / "." / "a" / ".." )) == str(W))
probe("A02_abspath_trailing_sep", lambda: os.path.abspath(str(W) + os.sep) == str(W))
probe("A03_name_trailing_space", lambda: (mk("sp ").name, sorted(p.name for p in W.iterdir() if p.name.startswith("sp"))))
probe("A04_name_trailing_dot", lambda: (mk("dot.").name, sorted(p.name for p in W.iterdir() if p.name.startswith("dot"))))
probe("A05_case_collide", lambda: (mk("Cc.txt", b"A"), mk("cc.txt", b"B"), sum(1 for p in W.iterdir() if p.name.lower() == "cc.txt"))[-1])
probe("A06_nfc_nfd_collide", lambda: (mk(unicodedata.normalize("NFC", "é1.txt"), b"A"),
                                      mk(unicodedata.normalize("NFD", "é1.txt"), b"B"),
                                      sum(1 for p in W.iterdir() if p.name.startswith(("é1", "e"))))[-1])
probe("A07_sep", lambda: repr(os.sep) + " altsep=" + repr(os.altsep))
probe("A08_join_mixed_sep", lambda: os.path.normpath("a/b\\c"))
probe("A09_case_sensitive_open", lambda: (mk("CaseOpen.txt", b"z"), (W / "caseopen.txt").exists())[-1])
probe("A10_colon_in_name", lambda: (mk("a:b.txt").name, True)[-1])
probe("A11_max_component", lambda: len((mk("z" * 200)).name))
probe("A12_symlink", lambda: (os.symlink(str(mk("lt.txt")), str(W / "ln1")), os.path.islink(str(W / "ln1")))[-1])
probe("A13_hardlink", lambda: (os.link(str(mk("hl.txt")), str(W / "hl2")), (W / "hl2").stat().st_nlink)[-1])
probe("A14_relpath_case", lambda: os.path.relpath(str(W / "Cc.txt"), str(W)))

# ── B 文件操作语义 ──────────────────────────────────────────────
def atomic_replace():
    a, b = mk("ar_a.txt", b"AAA"), mk("ar_b.txt", b"BBB")
    os.replace(str(a), str(b)); return b.read_bytes().decode()
probe("B01_os_replace_overwrite", atomic_replace)
def rename_onto_open():
    a, b = mk("ro_a.txt", b"A"), mk("ro_b.txt", b"B")
    fh = open(b, "r")
    try: os.replace(str(a), str(b)); return "可以"
    except OSError as e: return f"不行({e.strerror})"
    finally: fh.close()
probe("B02_rename_onto_open", rename_onto_open)
def unlink_open():
    p = mk("uo.txt"); fh = open(p, "r")
    try: os.unlink(p); return "可以"
    except OSError as e: return f"不行({e.strerror})"
    finally: fh.close()
probe("B03_unlink_open", unlink_open)
def rmdir_cwd():
    d = W / "cwdtest"; d.mkdir(exist_ok=True); old = os.getcwd()
    try:
        os.chdir(d); os.rmdir(str(d)); return "可以"
    except OSError as e: return f"不行({e.strerror})"
    finally:
        os.chdir(old)
probe("B04_rmdir_cwd", rmdir_cwd)
probe("B05_truncate_grow", lambda: (lambda p: (os.truncate(p, 100), p.stat().st_size)[-1])(mk("tr.txt", b"ab")))
probe("B06_copy_preserves_mode", lambda: (lambda s: (os.chmod(s, 0o640), shutil.copy(str(s), str(W / "cp1.txt")),
                                                     oct(stat.S_IMODE((W / "cp1.txt").stat().st_mode)))[-1])(mk("cpm.txt")))
probe("B07_copy2_preserves_mtime", lambda: (lambda s: (os.utime(s, (1000000, 1000000)), shutil.copy2(str(s), str(W / "cp2.txt")),
                                                       int((W / "cp2.txt").stat().st_mtime))[-1])(mk("cpt.txt")))
probe("B08_utime_ns_roundtrip", lambda: (lambda p: (os.utime(p, ns=(1234567891234567890, 1234567891234567890)),
                                                    p.stat().st_mtime_ns)[-1])(mk("ut.txt")))
probe("B09_st_ino_nonzero", lambda: mk("ino.txt").stat().st_ino != 0)
probe("B10_st_ctime_meaning", lambda: (lambda p: (os.chmod(p, 0o600), time.sleep(0.01),
                                                  "ctime变" if p.stat().st_ctime >= p.stat().st_mtime else "ctime不变")[-1])(mk("ct.txt")))
probe("B11_mtime_subsecond", lambda: round(mk("sub.txt").stat().st_mtime % 1, 6))

# ── C 目录遍历顺序 ──────────────────────────────────────────────
def order_probe():
    d = W / "ord"; d.mkdir(exist_ok=True)
    for n in ["b", "A", "c", "B", "a", "C", "10", "2"]:
        try: (d / n).write_bytes(b"x")
        except OSError: pass
    return os.listdir(d)
probe("C01_listdir_order", order_probe)
probe("C02_listdir_is_sorted", lambda: (lambda l: l == sorted(l))(os.listdir(W / "ord")))
probe("C03_glob_order", lambda: [os.path.basename(p) for p in glob.glob(str(W / "ord" / "*"))][:8])
probe("C04_scandir_order", lambda: [e.name for e in os.scandir(W / "ord")][:8])
probe("C05_walk_order", lambda: next(iter(os.walk(str(W / "ord"))))[2][:8])
probe("C06_pathlib_glob_order", lambda: [p.name for p in (W / "ord").glob("*")][:8])

# ── D 文本与编码 ────────────────────────────────────────────────
probe("D01_preferred_encoding", lambda: locale.getpreferredencoding(False))
probe("D02_fs_encoding", lambda: sys.getfilesystemencoding())
probe("D03_text_write_newline", lambda: (lambda p: (open(p, "w", encoding="utf-8").write("a\nb\n"), p.read_bytes())[-1])(W / "nl.txt"))
probe("D04_text_read_universal", lambda: (lambda p: (p.write_bytes(b"a\r\nb\r\n"), open(p, encoding="utf-8").read())[-1])(W / "nl2.txt"))
probe("D05_csv_default_lineterm", lambda: (lambda p: (__import__("csv").writer(open(p, "w", encoding="utf-8")).writerow(["a", "b"]), p.read_bytes())[-1])(W / "c.csv"))
probe("D06_upper_turkish_i", lambda: "i".upper() + "|" + "I".lower())
probe("D07_locale_strcoll", lambda: locale.strcoll("a", "A"))
probe("D08_json_dumps_ensure", lambda: json.dumps({"k": "café"}, ensure_ascii=False))

# ── E 进程与环境 ────────────────────────────────────────────────
probe("E01_env_name_case", lambda: (os.environ.__setitem__("Probe2Var", "1"), os.environ.get("PROBE2VAR", "(取不到)"))[-1])
probe("E02_pathsep", lambda: repr(os.pathsep))
probe("E03_mp_start_method", lambda: __import__("multiprocessing").get_start_method())
probe("E04_argv_maxlen", lambda: "32767" if IS_WIN else str(os.sysconf("SC_ARG_MAX")))
probe("E05_exit_code_neg", lambda: subprocess.run([sys.executable, "-c", "import sys;sys.exit(3)"]).returncode)
probe("E06_shell_true_prog", lambda: subprocess.run("echo hi", shell=True, capture_output=True).stdout.decode("utf-8", "replace").strip())
probe("E07_cwd_after_chdir_symlink", lambda: os.getcwd() == os.path.realpath(os.getcwd()))
probe("E08_umask", lambda: oct(os.umask(os.umask(0o22))))
probe("E09_chmod_effective", lambda: (lambda p: (os.chmod(p, 0o600), oct(stat.S_IMODE(p.stat().st_mode)))[-1])(mk("pm.txt")))
probe("E10_tempdir", lambda: tempfile.gettempdir())
probe("E11_tempfile_mode", lambda: (lambda p: oct(stat.S_IMODE(os.stat(p).st_mode)))(tempfile.mkstemp()[1]))
probe("E12_home_mode", lambda: oct(stat.S_IMODE(os.stat(os.path.expanduser("~")).st_mode)))

# ── F shell 行为 ────────────────────────────────────────────────
def sh(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True)
    return (r.stdout or r.stderr).decode("utf-8", "replace").strip()[:90]
probe("F01_sort_default", lambda: sh("printf 'b\\nA\\na\\nB\\n' | sort | tr '\\n' ' '"))
probe("F02_sort_C", lambda: sh("printf 'b\\nA\\na\\nB\\n' | LC_ALL=C sort | tr '\\n' ' '"))
probe("F03_glob_expand", lambda: sh("echo " + str(W / "ord" / "*")))
probe("F04_echo_backslash", lambda: sh("echo 'a\\tb'"))
probe("F05_which_sh", lambda: sh("command -v sh"))
probe("F06_sh_version", lambda: sh("sh --version 2>&1 | head -1"))
probe("F07_printf_float", lambda: sh("printf '%.2f\\n' 3.14159"))
probe("F08_date_iso", lambda: sh("date +%Y-%m-%dT%H:%M:%S"))
probe("F09_stat_flavor", lambda: sh(f"stat -c %s {W / 'ino.txt'} 2>&1 | head -1"))
probe("F10_ls_order", lambda: sh(f"ls {W / 'ord'} | tr '\\n' ' '"))
probe("F11_find_order", lambda: sh(f"find {W / 'ord'} -maxdepth 1 -type f | head -4 | tr '\\n' ' '"))
probe("F12_xargs_empty", lambda: sh("printf '' | xargs echo EMPTY"))

print("== ENVSHIFT-PROBE2 ==")
for k, v in OUT: print(f"{k}\t{v}")
print("== END ==")
shutil.rmtree(W, ignore_errors=True)
