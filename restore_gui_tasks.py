#!/usr/bin/env python3
"""从 secret 还原 GUI / 办公题目清单(分片 base64 → tar.gz → 三个 json)。题目不进 git。

与 restore_tasks.py 同一套办法,只是还原的是 gui_tasks.json / gui30_tasks.json / office_tasks.json
这三个被 gui_run.py、office_run.py、gui_table.py、delivery_check.py 直接读取的清单文件。
本地要用这些脚本时,先设好 GUI_TASKS_B64_* 跑一遍本脚本即可。
"""
import base64, io, os, pathlib, sys, tarfile

parts = [os.environ.get(f"GUI_TASKS_B64_{i}", "").strip() for i in range(1, 9)]
parts = [p for p in parts if p]
if not parts:
    print("没有 GUI_TASKS_B64_* secret,无法还原题目清单"); sys.exit(2)
here = pathlib.Path(__file__).resolve().parent
with tarfile.open(fileobj=io.BytesIO(base64.b64decode("".join(parts))), mode="r:gz") as tf:
    tf.extractall(here)
got = [n for n in ("gui_tasks.json", "gui30_tasks.json", "office_tasks.json") if (here / n).exists()]
print(f"已还原题目清单: {' '.join(got)}")
