#!/usr/bin/env python3
"""实测:大小写只差的名字,在这台机器上到底是一个文件还是两个。

背景:7 道已确认的 Windows badcase 都压在「pathlib.Path 在 Windows 上把 k/K 当同一个键」上。
但判据的真值是按 (st_dev, st_ino) 从真实文件系统推的——
如果 Windows 上两个名字本来就撞成一个文件,那期望值也跟着变成「两名同内容」,
朴素实现反而该过。实测结果却是 Windows 0/5。这个矛盾只能上真机解。
"""
import functools, json, os, pathlib, sys, tempfile
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

KELVIN = chr(0x212A)
out = {"platform": sys.platform, "os_name": os.name}

def scenario(tag, n1, n2):
    d = pathlib.Path(tempfile.mkdtemp(prefix="pid_"))
    r = {"name1": n1, "name2": n2}
    try:
        (d / n1).write_bytes(b"AAA")
        try:
            (d / n2).write_bytes(b"BBB")
            r["second_write"] = "ok"
        except OSError as e:
            r["second_write"] = "OSError: %s" % e
        entries = sorted(p.name for p in d.iterdir())
        r["dir_entries"] = entries
        r["entry_count"] = len(entries)
        for lbl, n in (("n1", n1), ("n2", n2)):
            try:
                st = (d / n).stat()
                r[lbl + "_ino"] = st.st_ino
                r[lbl + "_bytes"] = (d / n).read_bytes().decode()
            except OSError as e:
                r[lbl + "_ino"] = None
                r[lbl + "_bytes"] = "ERR %s" % type(e).__name__
        r["same_inode"] = (r.get("n1_ino") is not None
                           and r.get("n1_ino") == r.get("n2_ino"))
        r["path_eq"] = (d / n1) == (d / n2)

        # 朴素实现:lru_cache 吃 Path
        @functools.lru_cache(maxsize=None)
        def cached(p):
            return Path(p).read_bytes().decode()
        r["cached_n1"] = cached(d / n1)
        r["cached_n2"] = cached(d / n2)
        r["cache_hits"] = cached.cache_info().hits
        # 正确实现:用 str 当键
        @functools.lru_cache(maxsize=None)
        def cached_str(p):
            return Path(p).read_bytes().decode()
        r["strkey_n1"] = cached_str(str(d / n1))
        r["strkey_n2"] = cached_str(str(d / n2))
        r["strkey_hits"] = cached_str.cache_info().hits
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    out[tag] = r

scenario("ascii_kK", "k.json", "K.json")
scenario("kelvin", "k.json", KELVIN + ".json")
scenario("sharp_s", "ß.json", "ẞ.json")

# zip 虚拟命名空间(不碰文件系统)——H45/H46 走的是这条
import zipfile, io
buf = io.BytesIO()
with zipfile.ZipFile(buf, "w") as z:
    z.writestr("k.txt", "AAA"); z.writestr("K.txt", "BBB")
with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
    members = [i.filename for i in z.infolist()]
@functools.lru_cache(maxsize=None)
def zpay(archive_key, member):
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zz:
        return zz.read(member.as_posix()).decode()
vals = [zpay("A", pathlib.Path(n)) for n in members]
out["zip_namespace"] = {"members": members, "values_via_Path_key": vals,
                        "cache_hits": zpay.cache_info().hits,
                        "collapsed": len(set(vals)) == 1 and len(members) == 2}

print("PATHID_PROBE " + json.dumps(out, ensure_ascii=False))
