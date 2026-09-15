#!/usr/bin/env python3
"""名字身份的层间缺口探针。

造题原理(2026-09-15 从 7 道已确认 Windows badcase 里反推出来的):
  bug 不住在「某个 API 在不同系统上行为不同」,而住在
  **同一台机器上两个抽象层对「这两个名字是不是同一个」的判定不一致**的地方。

  已坐实的一例:Windows 上 NTFS 保留开尔文符号 U+212A 与 k 的区别(盘上两个文件),
  而 pathlib.Path 把它俩折成同一个键 → 缓存静默复用错误文件。
  Linux 两层都说「不同」、macOS 两层都说「相同」,所以只有 Windows 出错。

本探针把候选字符对 × 判定层做成矩阵,找出所有这类缺口。
每个缺口 = 一个候选机制(不是现有机制的变体)。
"""
import json, os, pathlib, shutil, sys, tempfile, unicodedata, zipfile, io

for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

PAIRS = [
    ("ascii_kK",      "k",              "K"),
    ("kelvin",        "k",              "K"),
    ("sharp_s",       "ß",         "ẞ"),      # ß / ẞ
    ("long_s",        "s",              "ſ"),      # s / ſ  casefold 会合并
    ("turkish_dotI",  "i",              "İ"),      # i / İ
    ("turkish_dotless","i",             "ı"),      # i / ı
    ("nfc_nfd",       "café",      "café"),  # é 的两种写法
    ("ohm",           "Ω",         "Ω"),      # 希腊Ω / 欧姆符号
    ("angstrom",      "Å",         "Å"),      # Å / 埃符号
    ("fullwidth",     "k",              "ｋ"),      # k / 全角ｋ
    ("roman_I",       "I",              "Ⅰ"),      # I / 罗马数字Ⅰ
    ("trailing_dot",  "name",           "name."),       # Windows 吞尾点
    ("trailing_space","name",           "name "),       # Windows 吞尾空格
]

def fs_verdict(a, b):
    """文件系统怎么看:能不能同时存在两个、是不是同一个 inode。"""
    d = pathlib.Path(tempfile.mkdtemp(prefix="ng_"))
    try:
        try:
            (d / (a + ".txt")).write_bytes(b"AAA")
        except OSError as e:
            return {"ok": False, "why": "第一个就建不出: %s" % type(e).__name__}
        try:
            (d / (b + ".txt")).write_bytes(b"BBB")
        except OSError as e:
            return {"ok": True, "same": None, "n_entries": 1,
                    "why": "第二个建不出: %s" % type(e).__name__}
        n = len(list(d.iterdir()))
        try:
            ia = (d / (a + ".txt")).stat().st_ino
            ib = (d / (b + ".txt")).stat().st_ino
            same = (ia == ib)
        except OSError:
            same = None
        return {"ok": True, "same": same, "n_entries": n}
    finally:
        shutil.rmtree(d, ignore_errors=True)

def layers(a, b):
    pa, pb = a + ".txt", b + ".txt"
    out = {}
    out["pathlib"]   = pathlib.Path(pa) == pathlib.Path(pb)
    out["normcase"]  = os.path.normcase(pa) == os.path.normcase(pb)
    out["lower"]     = pa.lower() == pb.lower()
    out["casefold"]  = pa.casefold() == pb.casefold()
    out["NFC"]       = unicodedata.normalize("NFC", pa) == unicodedata.normalize("NFC", pb)
    out["NFKC"]      = unicodedata.normalize("NFKC", pa) == unicodedata.normalize("NFKC", pb)
    out["str_eq"]    = (pa == pb)
    return out

def zip_verdict(a, b):
    """虚拟命名空间(zip 成员名):永远区分大小写,看用 Path 当键会不会塌。"""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(a + ".txt", "AAA"); z.writestr(b + ".txt", "BBB")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as z:
        names = [i.filename for i in z.infolist()]
    keyed = {pathlib.Path(n) for n in names}
    return {"members": len(names), "as_path_keys": len(keyed)}

def env_verdict(a, b):
    """环境变量名:Windows 不区分大小写,os.environ 在各平台行为不同。"""
    ka, kb = "NGPROBE_" + a.upper().encode("ascii","replace").decode(), None
    try:
        os.environ["NGPROBE_" + a] = "AAA"
        os.environ["NGPROBE_" + b] = "BBB"
        got_a = os.environ.get("NGPROBE_" + a)
        n = len([k for k in os.environ if k.startswith("NGPROBE_")])
        return {"n_keys": n, "a_value": got_a}
    except Exception as e:
        return {"error": type(e).__name__}
    finally:
        for k in [k for k in list(os.environ) if k.startswith("NGPROBE_")]:
            os.environ.pop(k, None)

rows = []
for tag, a, b in PAIRS:
    r = {"pair": tag,
         "a": "U+" + "+".join("%04X" % ord(c) for c in a),
         "b": "U+" + "+".join("%04X" % ord(c) for c in b),
         "fs": fs_verdict(a, b), "layers": layers(a, b),
         "zip": zip_verdict(a, b), "env": env_verdict(a, b)}
    rows.append(r)

print("NAMEGAP " + json.dumps({"platform": sys.platform, "rows": rows}, ensure_ascii=False))
