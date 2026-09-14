#!/usr/bin/env python3
"""从 secret 还原题目材料(分片 base64 → tar.gz → tasks/)。题目不进 git。

★分片一律先落成文件再读:把 37 块(约 1.06 MB)同时塞进环境变量会撞破 macOS 的
1048576 字节参数上限,整个 job 以 "Argument list too long" 失败,连一行日志都没有。
Linux 的上限是 4194304 所以看不出来——这正是本项目要测的那类环境差异。
"""
import base64, hashlib, io, os, pathlib, sys, tarfile

here = pathlib.Path(__file__).resolve().parent
blob = here / "tasks_b64.txt"

if blob.exists():
    b64 = blob.read_text().strip()
else:
    parts = []
    for i in range(1, 13):
        v = os.environ.get(f"TASKS_B64_{i}", "")
        if v:
            parts.append(v.strip())
    b64 = "".join(parts)

if not b64:
    print("没有题包分片,无法还原题目")
    sys.exit(2)

print("题包指纹", hashlib.sha256(b64.encode()).hexdigest()[:12])
raw = base64.b64decode(b64)
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as tf:
    tf.extractall(here)
n = len(list((here / "tasks").glob("*")))
print(f"还原题目 {n} 道")
