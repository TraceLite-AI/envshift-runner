#!/usr/bin/env python3
"""Coding 机制探针(纯 Python,无模型):十条候选,三系统同一套动作,只记事实。"""
import json, os, pathlib, platform, shutil, stat, subprocess, sys, tempfile, zipfile, random, glob
OUT = pathlib.Path("probe_out"); OUT.mkdir(exist_ok=True)
SYS = platform.system(); R = {"platform": platform.platform(), "python": sys.version.split()[0], "cwd": os.getcwd(), "checks": {}}
W = pathlib.Path(tempfile.mkdtemp(prefix="envshift-cprobe-"))
def rec(k, v): R["checks"][k] = v; print(k, json.dumps(v, ensure_ascii=False)[:300], flush=True)
def safe(fn):
    try: return fn()
    except Exception as e: return "%s: %s" % (type(e).__name__, str(e)[:80])
# 1 文本模式写换行
p = W / "nl.txt"; open(p, "w").write("a\nb\n"); raw = p.read_bytes()
p2 = W / "crlf.txt"; p2.write_bytes(b"k=v\r\nx=y\r\n")
rec("1_newline", {"write_text_bytes": repr(raw), "read_text_of_crlf": repr(open(p2).read()), "split_n_of_crlf": repr(open(p2).read().split("\n")),
                  "read_newline_empty": repr(open(p2, newline="").read())})
# 2 MAX_PATH
deep = W / ("d" * 60) / ("e" * 60) / ("f" * 60) / ("g" * 60) / ("h" * 60)
info = {"path_len": len(str(deep / "x.txt"))}
info["makedirs"] = safe(lambda: (os.makedirs(deep, exist_ok=True), "ok")[1])
info["write"] = safe(lambda: (open(deep / "x.txt", "w").write("1"), "ok")[1])
info["exists"] = safe(lambda: os.path.exists(deep / "x.txt")); info["exists_prefixed"] = safe(lambda: os.path.exists("\\\\?\\" + str(deep / "x.txt"))) if SYS == "Windows" else "n/a"
info["rglob_count"] = safe(lambda: len(list(W.rglob("x.txt")))); info["os_walk_found"] = safe(lambda: any("x.txt" in f for _, _, f in os.walk(W)))
rec("2_max_path", info)
# 3 X_OK
t = W / "notes.txt"; t.write_text("hi"); s = W / "tool.sh"; s.write_text("#!/bin/sh\necho ok\n"); os.chmod(s, 0o755); os.chmod(t, 0o644)
rec("3_x_ok", {"txt_X_OK": os.access(t, os.X_OK), "sh_X_OK": os.access(s, os.X_OK), "txt_mode": oct(stat.S_IMODE(t.stat().st_mode)), "which_python3": shutil.which("python3"), "which_python": shutil.which("python")})
# 4 环境变量大小写
env = dict(os.environ); env["path"] = "ZZZ"; r4 = subprocess.run([sys.executable, "-c", "import os;print(os.environ.get('PATH','')[:10], '|', os.environ.get('path','')[:10])"], env=env, capture_output=True, text=True)
rec("4_env_case", {"child_PATH_and_path": r4.stdout.strip(), "keys_with_path": [k for k in os.environ if k.lower() == "path"]})
# 5 非法字符
res5 = {}
for name in ("a:b.txt", "a?b.txt", "a*b.txt", "a|b.txt", "a<b.txt", 'a"b.txt', "trail.", "trail ", "con.txt", "aux.log"):
    res5[name] = safe(lambda: (open(W / name, "w").write("x"), sorted(x.name for x in W.iterdir() if x.name.startswith(name[:2]) and x.is_file())[:3])[1])
rec("5_illegal_chars", res5)
# 6 /tmp realpath
td = tempfile.gettempdir(); rec("6_tmp_realpath", {"gettempdir": td, "realpath": os.path.realpath(td), "equal": td == os.path.realpath(td), "cwd_vs_realpath": os.getcwd() == os.path.realpath(os.getcwd())})
# 7 可执行位
def mode(p): return oct(stat.S_IMODE(os.stat(p).st_mode))
shutil.copy(s, W / "c1.sh"); shutil.copyfile(s, W / "c2.sh"); (W / "c3.sh").write_bytes(s.read_bytes())
with zipfile.ZipFile(W / "p.zip", "w") as z: z.write(s, "tool.sh")
with zipfile.ZipFile(W / "p.zip") as z: z.extractall(W / "unz")
def run(p):
    try: r = subprocess.run([str(p)], capture_output=True, text=True, timeout=10); return "rc=%s %s" % (r.returncode, (r.stdout + r.stderr).strip()[:30])
    except Exception as e: return type(e).__name__
rec("7_exec_bit", {"src": mode(s), "copy": mode(W / "c1.sh"), "copyfile": mode(W / "c2.sh"), "write_bytes": mode(W / "c3.sh"), "zip_extract": mode(W / "unz" / "tool.sh"), "run_copyfile": run(W / "c2.sh"), "run_src": run(s)})
# 8 CRLF 配置解析
cfg = W / "app.cfg"; cfg.write_bytes(b"name=intake\r\nport=8081\r\n")
kv = dict(l.split("=", 1) for l in open(cfg).read().split("\n") if "=" in l)
rec("8_crlf_config", {"port_repr": repr(kv.get("port")), "port_equals_8081": kv.get("port") == "8081", "splitlines_ok": dict(l.split("=", 1) for l in open(cfg).read().splitlines() if "=" in l).get("port") == "8081"})
# 9 文件名字节长度
res9 = {}
for n in (80, 100, 120):
    name = ("报" * n) + ".txt"; res9["cjk_%d_chars_%d_bytes" % (n, len(name.encode("utf-8")))] = safe(lambda: (open(W / name, "w").write("x"), "ok")[1])
res9["ascii_250"] = safe(lambda: (open(W / ("a" * 250 + ".txt"), "w").write("x"), "ok")[1])
rec("9_name_bytes", res9)
# 10 listdir 顺序
d10 = W / "order"; d10.mkdir(); names = ["f%02d.txt" % i for i in range(20)]; random.seed(7); random.shuffle(names)
for n in names: (d10 / n).write_text("x")
ld = os.listdir(d10); rec("10_listdir_order", {"is_sorted": ld == sorted(ld), "first5": ld[:5], "glob_is_sorted": (lambda g: g == sorted(g))([os.path.basename(x) for x in glob.glob(str(d10 / "*"))])})
# 11 PATHEXT / which
(W / "mytool.bat").write_text("@echo off\necho bat\n"); (W / "mytool").write_text("#!/bin/sh\necho sh\n"); os.chmod(W / "mytool", 0o755)
rec("11_which_pathext", {"which_mytool_in_W": shutil.which("mytool", path=str(W)), "PATHEXT": os.environ.get("PATHEXT", "")[:60]})
(OUT / "result.json").write_text(json.dumps(R, ensure_ascii=False, indent=2), encoding="utf-8"); print("CPROBE-DONE", SYS, flush=True)
