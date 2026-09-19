#!/usr/bin/env python3
"""探针:os.listdir / Path.iterdir / os.scandir 的返回顺序在三台真机上是不是字母序(NTFS 是,ext4 不是,APFS 待测)。"""
import json, os, pathlib, random, shutil, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
OUT = {"platform": sys.platform}
for trial in range(3):
    d = pathlib.Path(tempfile.mkdtemp(prefix="lso_"))
    names = ["snap-%03d.json" % i for i in random.sample(range(1, 60), 12)]
    for n in names: (d / n).write_bytes(b"x")
    ls = os.listdir(d)
    OUT["trial%d" % trial] = {"创建序": names[:6], "listdir": ls[:6], "listdir是字母序": ls == sorted(ls), "listdir是创建序": ls == names,
                              "scandir是字母序": [e.name for e in os.scandir(d)] == sorted(ls), "iterdir是字母序": [p.name for p in d.iterdir()] == sorted(ls)}
    shutil.rmtree(d, ignore_errors=True)
OUT["撒谎(依赖字母序的代码会错)"] = not all(OUT["trial%d" % i]["listdir是字母序"] for i in range(3))
print("LSORDERPROBE " + json.dumps(OUT, ensure_ascii=False))
