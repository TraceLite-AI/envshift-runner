#!/usr/bin/env python3
"""探针:找"正确答案客观、无需向 agent 解释规则"的新跨 OS 机制。"""
import json, os, fnmatch, glob, ntpath, posixpath, pathlib, shutil, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
OUT = {"platform": sys.platform}

# A. 超长路径 >260:能否写入/读回
def probe_longpath():
    r = {}
    d = pathlib.Path(tempfile.mkdtemp(prefix="lp_"))
    try:
        seg = "d" * 40
        deep = d
        for _ in range(8): deep = deep / seg
        deep.mkdir(parents=True, exist_ok=True)
        f = deep / "leaf.txt"
        try:
            f.write_bytes(b"X"); r["写入"] = "ok"; r["路径长度"] = len(str(f))
            r["exists"] = f.exists(); r["读回"] = f.read_bytes().decode()
            r["撒谎"] = not (f.exists() and f.read_bytes() == b"X")
        except OSError as e:
            r["写入"] = "ERR " + type(e).__name__; r["撒谎"] = True
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    return r

# B. fnmatch 大小写:README.TXT 能否匹配 readme.txt 模式
def probe_fnmatch():
    return {"fnmatch('README.TXT','readme.txt')": fnmatch.fnmatch("README.TXT", "readme.txt"),
            "fnmatch('data.CSV','*.csv')": fnmatch.fnmatch("data.CSV", "*.csv"),
            "fnmatchcase('data.CSV','*.csv')": fnmatch.fnmatchcase("data.CSV", "*.csv"),
            "撒谎": fnmatch.fnmatch("data.CSV", "*.csv")}

# C. glob 大小写:目录里 Report.CSV,glob('*.csv') 能否命中
def probe_glob():
    d = pathlib.Path(tempfile.mkdtemp(prefix="gl_"))
    try:
        (d / "Report.CSV").write_bytes(b"x"); (d / "notes.csv").write_bytes(b"y")
        hits = sorted(p.name for p in d.glob("*.csv"))
        return {"glob('*.csv')命中": hits, "撒谎": "Report.CSV" in hits}
    finally:
        shutil.rmtree(d, ignore_errors=True)

# D. os.path.normcase
def probe_normcase():
    return {"normcase('Foo/Bar.TXT')": os.path.normcase("Foo/Bar.TXT"),
            "撒谎": os.path.normcase("Foo/Bar.TXT") != "Foo/Bar.TXT"}

# E. os.path.normpath 分隔符
def probe_normpath():
    return {"normpath('a/b/c')": os.path.normpath("a/b/c"),
            "撒谎": os.path.normpath("a/b/c") != "a/b/c"}

for name, fn in (("A_longpath", probe_longpath), ("B_fnmatch", probe_fnmatch),
                 ("C_glob_case", probe_glob), ("D_normcase", probe_normcase), ("E_normpath", probe_normpath)):
    try: OUT[name] = fn()
    except Exception as e: OUT[name] = {"error": "%s: %s" % (type(e).__name__, e)}
print("CLUSTERPROBE " + json.dumps(OUT, ensure_ascii=False))
