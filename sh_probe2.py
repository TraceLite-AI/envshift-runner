#!/usr/bin/env python3
"""Windows 上 shell 交付物为什么跑不出正确结果:这次把 stderr 一起收回来。

上一轮探针只看 rc 和 stdout,得出「bash 原样路径 rc=0」的结论,于是我判定启动方式没问题。
但真门一里 M4/M22/M25 三批 shell 题的参考解在 Windows 上全挂在第一条判据。
差别在:探针用的是极简脚本,真题的脚本里有 here-doc、函数、case、$(...) 和中文注释。
这次照真题的形态造脚本,并把 stderr 收回来。
"""
import os, pathlib, shutil, subprocess, sys, tempfile

for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

W = pathlib.Path(tempfile.mkdtemp(prefix="shp2_"))
(W / "store").mkdir()
for i in range(1, 5):
    (W / "store" / f"doc{i}.txt").write_text(f"doc{i}|{i:03d}", encoding="utf-8", newline="")
(W / "ledger.jsonl").write_text(
    "\n".join('{"seq": %d, "name": "doc%d", "size": 8}' % (i, i) for i in range(1, 5)) + "\n",
    encoding="utf-8", newline="")

# 照真题形态:中文注释 + 函数 + case + $() + 算术展开
SCRIPT = '''#!/bin/sh
# X-probe 参考解:用 POSIX 的 while 循环生成序号。与朴素解只差 seqs() 那一处。
ROOT="$1"
seqs() {
  i=1
  while [ $i -le 4 ]; do
    echo $i
    i=$((i + 1))
  done
}
names() {
  for i in $(seqs); do
    if [ -f "$ROOT/store/doc$i.txt" ]; then
      echo "doc$i"
    fi
  done
}
case "${2:-}" in
  --list)
    names
    ;;
  --bytes)
    T=0
    for n in $(names); do
      S=$(wc -c < "$ROOT/store/$n.txt" | tr -d ' ')
      T=$((T + S))
    done
    echo "$T"
    ;;
  *)
    echo "expected,4"
    echo "found,$(names | grep -c . )"
    ;;
esac
'''
script = W / "rollcall.sh"
# 关键:和 fixture 一样用 newline="" 写,保证是 LF
with open(script, "w", encoding="utf-8", newline="") as fh:
    fh.write(SCRIPT)
try:
    os.chmod(script, 0o755)
except OSError:
    pass

raw = script.read_bytes()
print("脚本字节数", len(raw), "含 CR:", b"\r" in raw)
print("首行:", raw.split(b"\n")[0])

BASH = shutil.which("bash") or r"C:\Program Files\Git\bin\bash.EXE"
SH = shutil.which("sh") or r"C:\Program Files\Git\usr\bin\sh.EXE"
print("bash =", BASH)
print("sh   =", SH)

def posix(p):
    p = str(p).replace("\\", "/")
    if len(p) > 1 and p[1] == ":":
        p = "/" + p[0].lower() + p[2:]
    return p

TRIES = [
    ("bash 原样", [BASH, str(script), str(W)]),
    ("bash posix脚本+原样数据", [BASH, posix(script), str(W)]),
    ("bash 全 posix", [BASH, posix(script), posix(W)]),
    ("sh 原样", [SH, str(script), str(W)]),
    ("sh 全 posix", [SH, posix(script), posix(W)]),
]
for name, cmd in TRIES:
    try:
        p = subprocess.run(cmd, capture_output=True, timeout=60)
        o = p.stdout.decode("utf-8", "replace").strip().replace("\n", "|")
        e = p.stderr.decode("utf-8", "replace").strip().replace("\n", "|")
        print(f"[{name}] rc={p.returncode}")
        print(f"    stdout={o[:110]!r}")
        print(f"    stderr={e[:200]!r}")
    except Exception as ex:
        print(f"[{name}] 启动失败 {type(ex).__name__}: {str(ex)[:120]}")

# 再试:把数据根目录也换成 posix 形式传给脚本内部使用
print("--- 加试:数据根目录用 posix 形式 ---")
p = subprocess.run([BASH, str(script), posix(W), "--list"], capture_output=True, timeout=60)
print("  --list rc=", p.returncode, "out=", p.stdout.decode("utf-8", "replace").strip().replace("\n", "|")[:80],
      "err=", p.stderr.decode("utf-8", "replace").strip()[:150])
shutil.rmtree(W, ignore_errors=True)
