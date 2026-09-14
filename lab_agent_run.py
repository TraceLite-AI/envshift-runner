"""Run public lab tasks through the existing pinned DSH, then verify fresh fixtures."""
import argparse, hashlib, json, os, pathlib, shutil, stat, subprocess, sys, tempfile, time
for stream in (sys.stdout, sys.stderr):
    stream.reconfigure(encoding='utf-8', errors='replace')
ap = argparse.ArgumentParser()
ap.add_argument('--task', required=True)
ap.add_argument('--model', default='deepseek-v4.1-flash')
ap.add_argument('--timeout', type=int, default=1500)
a = ap.parse_args()
here = pathlib.Path(__file__).resolve().parent
spec = json.loads((here/'tasks'/a.task/'task.json').read_text(encoding='utf-8'))
fixture = (here/'tasks'/a.task/'mkfixture.py').read_text(encoding='utf-8')
verifier = (here/'tasks'/a.task/'verifier/check.py').read_text(encoding='utf-8')
prompt_src = (here/'tasks'/a.task/'prompt.md').read_text(encoding='utf-8')
key = os.environ['ENVSHIFT_API_KEY']
assert key, 'model credential is missing'
out = here/'out'; out.mkdir(exist_ok=True)
public = here/'public-results'; public.mkdir(exist_ok=True)
base = pathlib.Path(tempfile.mkdtemp(prefix='envshift-agent-'))
app, data = base/'app', base/'data'
app.mkdir(); data.mkdir()

def remove(path):
    def onerror(fn, name, exc):
        os.chmod(name, stat.S_IWRITE); fn(name)
    if path.exists(): shutil.rmtree(path, onerror=onerror)

# No oracle, verifier, fixture source or Git history on disk during the model turn.
remove(here/'tasks'); remove(here/'.git')
for path in here.glob('*.md'): path.unlink()
for path in here.glob('*.py'):
    if path.resolve() != pathlib.Path(__file__).resolve(): path.unlink()
assert not (here/'tasks').exists() and not (here/'.git').exists()

def materialize(root, appdir, label):
    with tempfile.TemporaryDirectory(prefix='envshift-fixture-') as tmp:
        path = pathlib.Path(tmp)/'fixture.py'; path.write_text(fixture, encoding='utf-8')
        p = subprocess.run([sys.executable, str(path), str(root)], capture_output=True, env={**os.environ, spec['venv']+'_APP': str(appdir), 'PYTHONIOENCODING':'utf-8'}, timeout=120)
        (out/(label+'.log')).write_bytes(p.stdout+p.stderr)
        if p.returncode: raise RuntimeError(label+' failed: '+p.stderr.decode('utf-8','replace')[-500:])
materialize(data, app, 'fixture')
initial_hash = hashlib.sha256((app/spec['tool']).read_bytes()).hexdigest()
prompt = prompt_src.replace('/app', app.as_posix()).replace('/data', data.as_posix())
prompt += '\n本次数据根目录：`'+data.as_posix()+'`。当前 Python 解释器：`'+pathlib.Path(sys.executable).as_posix()+'`。\n'
prompt_path=out/'prompt.rendered.md'; prompt_path.write_text(prompt, encoding='utf-8')
dsh=here/'dsh'
env={**os.environ, 'DSH_NM':str(dsh/'node_modules'), 'DSH_BRIDGE':str(dsh/'bridge.mjs'), 'DSH_CONFIG':str(dsh/'cordis.yaml'), 'DSH_HOME_DIR':str(out/'dsh-home'), 'DSH_SESSION_ROOT':str(out/'dsh-sessions'), 'DSH_RUN_TIMEOUT':str(a.timeout), 'DSH_MAX_TOKENS':'131072'}
t0=time.time()
agent_rc=None
try:
    p=subprocess.run([sys.executable,str(dsh/'drive_dsh.py'),str(app),a.model,'https://api.llmgateway.io/v1',key,str(out),str(prompt_path)],cwd=app,env=env,capture_output=True,timeout=a.timeout+180)
    agent_rc=p.returncode
    (out/'driver.log').write_bytes(p.stdout+p.stderr)
except subprocess.TimeoutExpired as exc:
    (out/'driver.log').write_bytes((exc.stdout or b'')+(exc.stderr or b'')+b'\nDRIVER_TIMEOUT\n')
agent_seconds=int(time.time()-t0)
# Preserve deliverable independently of what the verifier runs.
shutil.copytree(app,out/'delivery',dirs_exist_ok=True)
if (app/spec['tool']).is_file(): shutil.copyfile(app/spec['tool'],public/spec['tool'])
# Fresh materialization prevents the agent from changing the grading ledger/data.
holdout, freshapp=base/'holdout',base/'freshapp'
holdout.mkdir();freshapp.mkdir()
materialize(holdout,freshapp,'holdout-fixture')
with tempfile.TemporaryDirectory(prefix='envshift-verifier-') as tmp:
    check=pathlib.Path(tmp)/'check.py';check.write_text(verifier,encoding='utf-8')
    logdir=out/'verifier-log'
    verifyenv={**os.environ, spec['venv']+'_ROOT':str(holdout),spec['venv']+'_BIN':str(app/spec['tool']),spec['venv']+'_LOG':str(logdir),spec['venv']+'_TIME_LIMIT':'120','PYTHONIOENCODING':'utf-8'}
    p=subprocess.run([sys.executable,str(check)],capture_output=True,env=verifyenv,timeout=900)
    (out/'verifier.log').write_bytes(p.stdout+p.stderr)
    trace=json.loads((logdir/'trace_results.json').read_text(encoding='utf-8'))
final=json.loads((out/'final.json').read_text(encoding='utf-8')) if (out/'final.json').exists() else {}
meta=dict(task=a.task,model=a.model,os=os.environ.get('RUNNER_OS'),cell=os.environ.get('XOS_CELL'),agent_rc=agent_rc,agent_seconds=agent_seconds,finish_reason=final.get('finishReason'),final_exists=bool(final),reward=trace['reward'],points=trace['points'],total=trace['total'],verifier_exit=p.returncode,initial_sha256=initial_hash,delivery_sha256=hashlib.sha256((app/spec['tool']).read_bytes()).hexdigest() if (app/spec['tool']).is_file() else None,trace=trace)
# Public tasks only: publish redacted run evidence; preserve full logs encrypted too.
for name in ('driver.log','final.json','trace.jsonl','verifier.log','prompt.rendered.md'):
    f=out/name
    if f.exists(): (public/name).write_text(f.read_text(encoding='utf-8',errors='replace').replace(key,'[REDACTED]'),encoding='utf-8')
(public/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"{a.task} cell={meta['cell']} arm=agent model={a.model} reward={meta['reward']} 诊断={meta['points']}/{meta['total']} agent_rc={agent_rc} finish={meta['finish_reason']} agent_s={agent_seconds}")
# Infrastructure failures must not be presented as measured agent failures.
if agent_rc != 0 or not final:
    print('AGENT_INFRA_FAILURE: see redacted driver log',file=sys.stderr)
    sys.exit(3)
