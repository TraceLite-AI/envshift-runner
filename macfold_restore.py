#!/usr/bin/env python3
"""从 secret 还原 macfold 题包并核对指纹。题目材料不进这个公开仓。

指纹核对是硬闸门:对不上就退非零。栽过——secret 没写完就派 run,
runner 用的是旧题包,症状是「全体两臂满分」,整轮白跑。
"""
import base64, hashlib, io, os, pathlib, sys, tarfile

b64 = os.environ.get("MACFOLD_B64", "").strip()
want = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
if not b64:
    print("没有 MACFOLD_B64"); sys.exit(2)
raw = base64.b64decode(b64)
got = hashlib.sha256(raw).hexdigest()
print("题包指纹 %s" % got)
if want and got != want:
    print("★指纹对不上,应为 %s —— 跑的可能是旧题包,直接退出" % want); sys.exit(3)
dest = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "macfold")
dest.mkdir(parents=True, exist_ok=True)
with tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz") as t:
    t.extractall(dest)
print("还原题目 %d 道" % len(list((dest / "tasks").glob("*"))))
