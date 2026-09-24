"""第三轮 Coding 机制探针(数据触发型候选):每条打印 装置读数,三系统对照。"""
import os, sys, json, subprocess, shutil, stat, tempfile, platform, pathlib, errno
R = {}
def rec(k, v): R[k] = v; print(f"{k}: {v!r}", flush=True)
rec("os", platform.platform()); rec("py", sys.version.split()[0]); rec("PYTHONUTF8", os.environ.get("PYTHONUTF8")); rec("PYTHONIOENCODING", os.environ.get("PYTHONIOENCODING"))
T = pathlib.Path(tempfile.mkdtemp(prefix="probe3-"))
# M14 大小写错的名字能不能查到/打开
(T / "README.md").write_text("x")
rec("M14 exists(README.MD)", os.path.exists(T / "README.MD")); rec("M14 isfile(readme.md)", os.path.isfile(T / "readme.md"))
try: rec("M14 open(readme.MD)", open(T / "readme.MD").read())
except OSError as e: rec("M14 open(readme.MD)", type(e).__name__)
try: rec("M14 samefile(README.md, readme.md)", os.path.samefile(T / "README.md", T / "readme.md"))
except OSError as e: rec("M14 samefile", type(e).__name__)
rec("M14 listdir 里的名字", sorted(os.listdir(T)))
# M39 normcase
rec("M39 normcase('Data/Report.CSV')", os.path.normcase("Data/Report.CSV"))
# M21 只读文件:删除/改名/rmtree
d = T / "ro"; d.mkdir(); f = d / "pack.idx"; f.write_text("x"); os.chmod(f, 0o444)
try: os.remove(f); rec("M21 remove(只读文件)", "ok")
except OSError as e: rec("M21 remove(只读文件)", f"{type(e).__name__} errno={e.errno}")
f2 = d / "pack2.idx"; f2.write_text("y"); os.chmod(f2, 0o444)
try: os.replace(f2, d / "moved.idx"); rec("M21 replace(只读文件)", "ok")
except OSError as e: rec("M21 replace(只读文件)", f"{type(e).__name__} errno={e.errno}")
f3 = d / "pack3.idx"; f3.write_text("z"); os.chmod(f3, 0o444)
try: shutil.rmtree(d); rec("M21 rmtree(含只读)", "ok" if not d.exists() else "目录还在")
except OSError as e: rec("M21 rmtree(含只读)", f"{type(e).__name__} errno={e.errno} 目录还在={d.exists()}")
try:
    f4 = T / "ro2.txt"; f4.write_text("a"); os.chmod(f4, 0o444); open(f4, "w").write("b"); rec("M21 open('w')(只读文件)", "ok " + f4.read_text())
except OSError as e: rec("M21 open('w')(只读文件)", f"{type(e).__name__} errno={e.errno}")
# M2 名字里的非法字符:冒号是否变成 ADS(静默)
for name in ["log 12:30.txt", "q?.txt", "a*b.txt", 'say"hi".txt', "a<b>.txt", "x|y.txt", "end.", "end ", "tab\tname.txt"]:
    p = T / name
    try:
        p.write_text("hello"); back = p.read_text() if p.exists() else None
        rec(f"M2 write({name!r})", {"exists": p.exists(), "listdir命中": name in os.listdir(T), "read": back})
    except OSError as e: rec(f"M2 write({name!r})", f"{type(e).__name__} errno={e.errno}")
rec("M2 listdir 后", sorted(os.listdir(T)))
# M28 管道编码:子进程 print 非 ASCII
child = "import sys; print('José'); print('张三')"
r = subprocess.run([sys.executable, "-c", child], capture_output=True)
rec("M28 子进程 stdout 原始字节", r.stdout); rec("M28 子进程 stderr 尾", r.stderr[-160:])
r2 = subprocess.run([sys.executable, "-c", "print('José')"], capture_output=True, text=True)
rec("M28 text=True 解码结果", r2.stdout.strip())
# M44/M45 目录当文件打开/删除:异常类型
dd = T / "adir"; dd.mkdir()
try: open(dd).read(); rec("M44 open(目录)", "ok")
except OSError as e: rec("M44 open(目录)", f"{type(e).__name__} errno={e.errno}")
try: os.remove(dd); rec("M45 remove(目录)", "ok")
except OSError as e: rec("M45 remove(目录)", f"{type(e).__name__} errno={e.errno}")
# M60 文件名大小写不同的两条记录落盘后剩几个文件(C240 型,补读数)
e = T / "tags"; e.mkdir()
for n in ["Work", "work", "WORK"]: (e / n).mkdir(exist_ok=True)
rec("M60 三个大小写 tag 目录实际个数", len(os.listdir(e)))
print("PROBE3-JSON " + json.dumps({k: (v if isinstance(v, (str, int, bool, list, dict, type(None))) else repr(v)) for k, v in R.items()}, ensure_ascii=False, default=repr))
