#!/usr/bin/env python3
"""探针:找「只有 macOS 撒谎」的机制。三台真机各跑一次,输出一行 JSON。

A. 临时目录符号链接:mac 的 /tmp、/var 指向 /private/…。chdir 进去后 getcwd 回来的字符串前缀对不上,
   路径穿越防护 startswith(base) 会把所有文件当外来。
B. 大小写折叠表差异:APFS 按 Unicode 9.0 折叠,NTFS 用老 upcase 表。晚加进 Unicode 的字母只有 mac 合并。
   每对:写两个只差大小写(或折叠关系)的名字,数目录里有几个文件。
"""
import json, os, pathlib, shutil, sys, tempfile
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
OUT = {"platform": sys.platform}

def probe_tmp_symlink():
    r = {}
    d = tempfile.mkdtemp(prefix="mp_")
    prev = os.getcwd()
    try:
        os.chdir(d)
        r["mkdtemp 给的"] = d
        r["chdir 后 getcwd"] = os.getcwd()
        r["realpath"] = os.path.realpath(d)
        r["abspath==getcwd"] = os.path.abspath(d) == os.getcwd()
        r["getcwd 以 mkdtemp 前缀开头"] = os.getcwd().startswith(d)
        pathlib.Path(d, "a.txt").write_bytes(b"x")
        full = os.path.join(os.getcwd(), "a.txt")
        r["startswith 防护放行"] = full.startswith(os.path.abspath(d) + os.sep)
        r["撒谎"] = not r["startswith 防护放行"]
        r["gettempdir"] = tempfile.gettempdir()
        r["/tmp 是链接"] = os.path.islink("/tmp") if os.path.exists("/tmp") else None
    except Exception as e:
        r["error"] = "%s: %s" % (type(e).__name__, e)
    finally:
        os.chdir(prev); shutil.rmtree(d, ignore_errors=True)
    return r

PAIRS = {
    "cherokee_13A0_AB70": (chr(0x13A0), chr(0xAB70)),
    "cyrillic_0512_0513": (chr(0x0512), chr(0x0513)),
    "cyrillic_0528_0529": (chr(0x0528), chr(0x0529)),   # Unicode 7.0
    "latin_A7B3_AB53": (chr(0xA7B3), chr(0xAB53)),        # Unicode 8.0
    "latin_A79A_A79B": (chr(0xA79A), chr(0xA79B)),        # Unicode 6.0
    "latin_A7AA_0266": (chr(0xA7AA), chr(0x0266)),        # Unicode 6.1
    "sharp_1E9E_00DF": (chr(0x1E9E), chr(0x00DF)),
    "kelvin_212A_006B": (chr(0x212A), "k"),
    "greek_final_03C2_03A3": (chr(0x03C2), chr(0x03A3)),
    "greek_03C3_03A3": (chr(0x03C3), chr(0x03A3)),
    "dz_01C5_01C4": (chr(0x01C5), chr(0x01C4)),
    "turkish_0130_0069": (chr(0x0130), "i"),
    "ascii_A_a": ("A", "a"),
    "eacute_00C9_00E9": (chr(0x00C9), chr(0x00E9)),
    "georgian_10D0_1C90": (chr(0x10D0), chr(0x1C90)),     # Unicode 11
    "nfc_nfd_cafe": ("caf" + chr(0xE9), "cafe" + chr(0x301)),
}
def probe_pairs():
    r = {}
    for tag, (a, b) in PAIRS.items():
        d = pathlib.Path(tempfile.mkdtemp(prefix="cp_"))
        try:
            (d / (a + "-x")).write_bytes(b"A")
            (d / (b + "-x")).write_bytes(b"B")
            names = os.listdir(d)
            r[tag] = {"文件数": len(names), "第一个读回": (d / (a + "-x")).read_bytes().decode()}
        except Exception as e:
            r[tag] = {"error": "%s: %s" % (type(e).__name__, e)}
        finally:
            shutil.rmtree(d, ignore_errors=True)
    return r

OUT["A_tmp_symlink"] = probe_tmp_symlink()
OUT["B_case_pairs"] = probe_pairs()
print("MACFSPROBE " + json.dumps(OUT, ensure_ascii=False))
