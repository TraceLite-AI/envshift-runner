#!/usr/bin/env python3
"""★必须用 shell: python 跑,不能经 Git Bash:xz 包 base64 以 / 开头,MSYS 会把它当 POSIX 路径转换,Windows 上多出 4159 个字符。
从分片 secret 还原 GUI 题包(Native v2 导出包 + tools/ci_benchmark.py),核对指纹后解到 guibench/。题目材料不进这个公开仓。"""
import base64, hashlib, io, os, pathlib, sys, tarfile
for _s in (sys.stdout, sys.stderr):
    try: _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
parts = []
i = 0
while True:
    v = os.environ.get("%s_%02d" % (os.environ.get("BUNDLE_PREFIX", "GUIB"), i), "").strip()
    if not v: break
    parts.append(v); i += 1
if not parts:
    print("没有 %s_00" % os.environ.get("BUNDLE_PREFIX", "GUIB")); sys.exit(2)
import re
joined = "".join(parts)
bad = sorted(set(re.findall(r"[^A-Za-z0-9+/=]", joined)))
print("分片长度 %s 非 base64 字符 %r" % ([len(x) for x in parts], bad[:20]))
raw = base64.b64decode(re.sub(r"[^A-Za-z0-9+/=]", "", joined))
got = hashlib.sha256(raw).hexdigest()
want = (sys.argv[1] if len(sys.argv) > 1 else os.environ.get("BUNDLE_SHA256", "")).strip()
print("题包指纹 %s (%d 片)" % (got, len(parts)))
if want and got != want:
    print("★指纹对不上,应为 %s" % want); sys.exit(3)
dest = pathlib.Path("guibench")
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:xz") as t:
    t.extractall(".")
pathlib.Path("gui_export").rename(dest)
print("还原题目 %d 道" % len(list((dest / "tasks").glob("G*"))))
