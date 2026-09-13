#!/usr/bin/env python3
"""EnvShift 裸机执行器(不依赖 Docker;给 GitHub 的 macOS/Windows/Linux runner 用)。
三阶段流程,与容器版执行器一致。"""
import argparse, json, os, pathlib, shutil, stat, subprocess, sys, tempfile, time
for _st in (sys.stdout, sys.stderr):
    try: _st.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
BIN = {
       "E10-dupes-extend": ("dupes.py", "E10"),
       "E11-export-extend": ("export.sh", "E11"),
       "E12-publish-extend": ("publish.sh", "E12"),
       "E3-archive-audit": ("audit", "E3"),
       "E4-vault-compliance": ("vault-archive", "E4"),
       "E5-retention-plan": ("retain", "E5"),
       "E6-contact-merge": ("merge.sh", "E6"),
       "E7-publish-shared": ("publish", "E7"),
       "E8-report-extend": ("report.py", "E8"),
       "E9-latest-extend": ("latest.py", "E9"),
       "X1-index-extend": ("index.py", "X1"),
       "X100-signup-m8": ("dropscan.py", "X100"),
       "X101-ticket-m8": ("sinkaudit.py", "X101"),
       "X102-stock-m8": ("settlecheck.py", "X102"),
       "X103-archive-m25": ("sumline.sh", "X103"),
       "X104-signup-m25": ("brief_line.sh", "X104"),
       "X105-ticket-m25": ("oneline.sh", "X105"),
       "X106-stock-m25": ("tagline.sh", "X106"),
       "X107-archive-m10b": ("tally_par.py", "X107"),
       "X108-signup-m10b": ("sum_par.py", "X108"),
       "X109-ticket-m10b": ("fold_par.py", "X109"),
       "X11-archive-m1": ("index.py", "X11"),
       "X110-stock-m10b": ("agg_par.py", "X110"),
       "X12-signup-m1": ("roster.py", "X12"),
       "X13-ticket-m1": ("queue.py", "X13"),
       "X14-stock-m1": ("tally.py", "X14"),
       "X15-archive-m5": ("emit.py", "X15"),
       "X16-signup-m5": ("deliver.py", "X16"),
       "X17-ticket-m5": ("dispatch.py", "X17"),
       "X18-stock-m5": ("issue.py", "X18"),
       "X19-archive-m3": ("pick.py", "X19"),
       "X2-emit-extend": ("emit.py", "X2"),
       "X20-signup-m3": ("select.py", "X20"),
       "X21-ticket-m3": ("resolve.py", "X21"),
       "X22-stock-m3": ("choose.py", "X22"),
       "X23-archive-m4": ("export.sh", "X23"),
       "X24-signup-m4": ("extract.sh", "X24"),
       "X25-ticket-m4": ("dump.sh", "X25"),
       "X26-stock-m4": ("listing.sh", "X26"),
       "X27-archive-m6": ("tally.py", "X27"),
       "X28-signup-m6": ("sheet.py", "X28"),
       "X29-ticket-m6": ("digest.py", "X29"),
       "X3-tally-extend": ("tally.py", "X3"),
       "X30-stock-m6": ("recount.py", "X30"),
       "X31-archive-m10": ("rollup.py", "X31"),
       "X32-signup-m10": ("sum.py", "X32"),
       "X33-ticket-m10": ("fold.py", "X33"),
       "X34-stock-m10": ("aggregate.py", "X34"),
       "X35-archive-m11": ("badge.py", "X35"),
       "X36-signup-m11": ("card.py", "X36"),
       "X37-ticket-m11": ("label.py", "X37"),
       "X38-stock-m11": ("tag.py", "X38"),
       "X39-archive-m13": ("sweep.py", "X39"),
       "X4-pick-extend": ("pick.py", "X4"),
       "X40-signup-m13": ("patrol.py", "X40"),
       "X41-ticket-m13": ("inspect.py", "X41"),
       "X42-stock-m13": ("canvass.py", "X42"),
       "X43-archive-m18": ("locate.py", "X43"),
       "X44-signup-m18": ("trace.py", "X44"),
       "X45-ticket-m18": ("seek.py", "X45"),
       "X46-stock-m18": ("hunt.py", "X46"),
       "X47-archive-m14": ("recon.py", "X47"),
       "X48-signup-m14": ("match.py", "X48"),
       "X49-ticket-m14": ("verify_sizes.py", "X49"),
       "X5-export-extend": ("export.sh", "X5"),
       "X50-stock-m14": ("balance.py", "X50"),
       "X51-archive-m16": ("guard.py", "X51"),
       "X52-signup-m16": ("supervise.py", "X52"),
       "X53-ticket-m16": ("watchdog.py", "X53"),
       "X54-stock-m16": ("runner.py", "X54"),
       "X55-archive-m20": ("scrub.py", "X55"),
       "X56-signup-m20": ("sweepdir.py", "X56"),
       "X57-ticket-m20": ("tidy.py", "X57"),
       "X58-stock-m20": ("reap.py", "X58"),
       "X59-archive-m12": ("report_names.py", "X59"),
       "X6-rollup-extend": ("rollup.py", "X6"),
       "X60-signup-m12": ("rollcall.py", "X60"),
       "X61-ticket-m12": ("brief.py", "X61"),
       "X62-stock-m12": ("digest_names.py", "X62"),
       "X63-archive-m17": ("stamps.py", "X63"),
       "X64-signup-m17": ("clockcheck.py", "X64"),
       "X65-ticket-m17": ("timepoints.py", "X65"),
       "X66-stock-m17": ("freshness.py", "X66"),
       "X67-archive-m21": ("toolcheck.py", "X67"),
       "X68-signup-m21": ("chainscan.py", "X68"),
       "X69-ticket-m21": ("kitaudit.py", "X69"),
       "X70-stock-m21": ("binsurvey.py", "X70"),
       "X71-archive-m2": ("handout.py", "X71"),
       "X72-signup-m2": ("issue_pack.py", "X72"),
       "X73-ticket-m2": ("split.py", "X73"),
       "X74-stock-m2": ("release.py", "X74"),
       "X75-archive-m15": ("fillin.py", "X75"),
       "X76-signup-m15": ("compose.py", "X76"),
       "X77-ticket-m15": ("stamp_tpl.py", "X77"),
       "X78-stock-m15": ("weave.py", "X78"),
       "X79-archive-m9": ("loadconf.py", "X79"),
       "X80-signup-m9": ("setup_env.py", "X80"),
       "X81-ticket-m9": ("applyconf.py", "X81"),
       "X82-stock-m9": ("bootconf.py", "X82"),
       "X83-archive-m22": ("rollcall.sh", "X83"),
       "X84-signup-m22": ("headcount.sh", "X84"),
       "X85-ticket-m22": ("muster.sh", "X85"),
       "X86-stock-m22": ("tick.sh", "X86"),
       "X87-archive-m23": ("closeout.sh", "X87"),
       "X88-signup-m23": ("wrapup.sh", "X88"),
       "X89-ticket-m23": ("settle.sh", "X89"),
       "X90-stock-m23": ("finalize.sh", "X90"),
       "X91-archive-m24": ("gather.sh", "X91"),
       "X92-signup-m24": ("collectup.sh", "X92"),
       "X93-ticket-m24": ("stage_files.sh", "X93"),
       "X94-stock-m24": ("haul.sh", "X94"),
       "X95-archive-m7": ("pubaudit.py", "X95"),
       "X96-signup-m7": ("keycheck.py", "X96"),
       "X97-ticket-m7": ("permreport.py", "X97"),
       "X98-stock-m7": ("modescan.py", "X98"),
       "X99-archive-m8": ("landcheck.py", "X99")}
ap = argparse.ArgumentParser()
ap.add_argument("--task", required=True); ap.add_argument("--arm", default="oracle")
ap.add_argument("--data", default="/data"); ap.add_argument("--app", default="/app")
ap.add_argument("--out", default="out"); ap.add_argument("--model", default="deepseek-v4-pro")
ap.add_argument("--base", default="https://api.llmgateway.io/v1"); ap.add_argument("--cell-env", default="{}")
ap.add_argument("--timeout", type=int, default=3600); ap.add_argument("--sudo-verify", action="store_true")
a = ap.parse_args()
here = pathlib.Path(__file__).resolve().parent; td = here / "tasks" / a.task
binname, venv = BIN[a.task]; data, app = pathlib.Path(a.data), pathlib.Path(a.app)
if os.name == "nt" and a.task in ("E7-publish-shared", "E12-publish-extend"):
    print(f"{a.task} cell={os.environ.get('XOS_CELL','?')} arm={a.arm} reward=NA 诊断=NA (Windows 无 POSIX 权限模型:坐标无定义)"); sys.exit(0)
out = pathlib.Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
cell_env = json.loads(a.cell_env); t0 = time.time()
def wipe(p):
    p.mkdir(parents=True, exist_ok=True)
    for c in p.iterdir(): shutil.rmtree(c, ignore_errors=True) if c.is_dir() else c.unlink(missing_ok=True)
wipe(data); wipe(app)
# 运行材料只存在于内存,agent 阶段不落盘。
import io, tarfile
_buf = io.BytesIO()
with tarfile.open(fileobj=_buf, mode="w") as _tf: _tf.add(str(td / "verifier"), arcname="verifier")
VERIFIER_TAR = _buf.getvalue()
def _rm(p):
    # 只读文件要先去只读位再删
    def _onerr(fn, path, exc):
        os.chmod(path, stat.S_IWRITE); fn(path)
    if p.exists(): shutil.rmtree(p, onerror=_onerr)
MKFIX_SRC = (td / "mkfixture.py").read_text(encoding="utf-8")
PROMPT_SRC = (td / "prompt.md").read_text(encoding="utf-8")
ARM_DIR_TAR = None
if a.arm not in ("agent", "null"):
    _b2 = io.BytesIO()
    with tarfile.open(fileobj=_b2, mode="w") as _tf: _tf.add(str(td / "arms" / a.arm), arcname="arm")
    ARM_DIR_TAR = _b2.getvalue()
if a.arm == "agent":
    _rm(here / "tasks"); _rm(here / ".git")
    for _f in here.glob("*.md"): _f.unlink(missing_ok=True)
    for _f in here.glob("*.py"):
        if _f.resolve() != pathlib.Path(__file__).resolve():
            try: _f.unlink()
            except OSError: pass
    assert not (here / "tasks").exists() and not (here / ".git").exists(), "materials not cleared"
# 1) fixture:不施加格子环境
_mk = pathlib.Path(tempfile.mkdtemp(prefix="mkfix-")) / "mkfixture.py"; _mk.write_text(MKFIX_SRC, encoding="utf-8")
r = subprocess.run([sys.executable, str(_mk), str(data)], capture_output=True, text=True,
                   env={**os.environ, f"{venv}_APP": str(app)})   # 从内存写回临时目录跑;E8/E9 的现成工具由 fixture 写进 app 根
shutil.rmtree(_mk.parent, ignore_errors=True)
(out / "fixture.log").write_text(r.stdout + r.stderr)
if r.returncode != 0: print(f"{a.task} arm={a.arm} FIXTURE-FAIL {r.stderr[-200:]}"); sys.exit(4)
# 2) 臂
agent_rc = 0; env_cell = dict(os.environ, **cell_env)
if a.arm == "agent":
    dsh = here / "dsh"; nm = dsh / "node_modules"
    prompt = out / ".prompt.md"
    # ★题面里写死的 /data /app 按本 OS 的真实根目录渲染(mac 根目录只读、Windows 无根目录)——这本身是 OS 坐标的一部分
    def _p(pth): return str(pathlib.Path(pth).resolve()).replace("\\", "/")
    txt = PROMPT_SRC.replace("/data", _p(data)).replace("/app", _p(app))
    prompt.write_text(txt, encoding="utf-8"); (out / "prompt.rendered.md").write_text(txt, encoding="utf-8")
    env = dict(env_cell, DSH_NM=str(nm), DSH_BRIDGE=str(dsh / "bridge.mjs"), DSH_CONFIG=str(dsh / "cordis.yaml"),
               DSH_HOME_DIR=str(out / "dsh-home"), DSH_SESSION_ROOT=str(out / "dsh-sessions"),
               DSH_RUN_TIMEOUT=str(a.timeout), DSH_MAX_TOKENS=os.environ.get("DSH_MAX_TOKENS", "131072"))
    key = os.environ.get("ENVSHIFT_API_KEY", "")
    r = subprocess.run([sys.executable, str(dsh / "drive_dsh.py"), str(app), a.model, a.base, key, str(out), str(prompt)],
                       cwd=str(app), env=env, capture_output=True, text=True, timeout=a.timeout + 300)
    (out / "driver.log").write_text(r.stdout + r.stderr); agent_rc = r.returncode; prompt.unlink(missing_ok=True)
elif a.arm != "null":
    if ARM_DIR_TAR is None: print(f"{a.task} arm={a.arm} NO-SUCH-ARM"); sys.exit(2)
    _at = pathlib.Path(tempfile.mkdtemp(prefix="arm-"))
    with tarfile.open(fileobj=io.BytesIO(ARM_DIR_TAR), mode="r") as _tf: _tf.extractall(_at)
    shutil.copytree(_at / "arm", app, dirs_exist_ok=True); shutil.rmtree(_at, ignore_errors=True)
    b = app / binname; b.chmod(b.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
t1 = time.time()
# 3) 评分阶段
tests = pathlib.Path(tempfile.mkdtemp(prefix="tests-"))
with tarfile.open(fileobj=io.BytesIO(VERIFIER_TAR), mode="r") as _tf: _tf.extractall(tests)
tests = tests / "verifier"
logdir = out / "verifier-log"; logdir.mkdir(exist_ok=True)
venv_env = dict(env_cell, **{f"{venv}_LOG": str(logdir), f"{venv}_BIN": str(app / binname), f"{venv}_ROOT": str(data)})
cmd = [sys.executable, str(tests / "check.py")]
if a.sudo_verify and os.name == "posix" and shutil.which("sudo"): cmd = ["sudo", "-E", "--preserve-env=PATH"] + cmd
r = subprocess.run(cmd, env=venv_env, capture_output=True, text=True, timeout=1800)
(out / "verifier.log").write_text(r.stdout + r.stderr)
reward = (logdir / "reward.txt").read_text().strip() if (logdir / "reward.txt").exists() else "?"
tr = json.loads((logdir / "trace_results.json").read_text()) if (logdir / "trace_results.json").exists() else {}
line = f"{a.task} cell={os.environ.get('XOS_CELL','?')} arm={a.arm} reward={reward} 诊断={tr.get('points','?')}/{tr.get('total','?')} agent_rc={agent_rc} vrc={r.returncode} agent_s={int(t1-t0)} verify_s={int(time.time()-t1)}"
print(line)
if reward != "1":
    _vl = (out / "verifier.log").read_text(encoding="utf-8", errors="replace") if (out / "verifier.log").exists() else ""
    for _ln in _vl.strip().splitlines()[-6:]:
        print("  VERIFIER-TAIL " + _ln[:200])
(out / "meta.json").write_text(json.dumps({"line": line, "reward": reward, "trace": tr, "cell_env": cell_env}, ensure_ascii=False, indent=2))
