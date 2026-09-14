"""Artifact-delivery task runner: model produces CSV/ZIP, not a program."""
import argparse,hashlib,json,os,pathlib,shutil,stat,subprocess,sys,tempfile,time
for stream in (sys.stdout,sys.stderr):stream.reconfigure(encoding='utf-8',errors='replace')
p=argparse.ArgumentParser();p.add_argument('--task',required=True);p.add_argument('--arm',choices=['oracle','naive','agent'],default='agent');p.add_argument('--model',default='deepseek-v4.1-flash');p.add_argument('--timeout',type=int,default=900)
a=p.parse_args();here=pathlib.Path(__file__).resolve().parent;td=here/'tasks'/a.task
fixture=(td/'mkfixture.py').read_text(encoding='utf-8');verifier=(td/'verifier/check.py').read_text(encoding='utf-8');prompt_src=(td/'prompt.md').read_text(encoding='utf-8')
arm_src=(td/'arms'/a.arm/'deliver.py').read_text(encoding='utf-8') if a.arm!='agent' else None
base=pathlib.Path(tempfile.mkdtemp(prefix='envshift-delivery-'));work=base/'work';work.mkdir();truth=base/'truth.json'
out=here/'out'/f'{a.task}-{a.arm}';out.mkdir(parents=True,exist_ok=True)
public=here/'public-results'/f'{a.task}-{a.arm}';public.mkdir(parents=True,exist_ok=True)
if a.arm=='agent':
 def onerror(fn,path,exc):os.chmod(path,stat.S_IWRITE);fn(path)
 for folder in ('tasks','.git'):
  if (here/folder).exists():shutil.rmtree(here/folder,onerror=onerror)
 for f in here.glob('*.md'):f.unlink()
 for f in here.glob('*.py'):
  if f.resolve()!=pathlib.Path(__file__).resolve():f.unlink()
with tempfile.TemporaryDirectory(prefix='fixture-') as tmp:
 f=pathlib.Path(tmp)/'fixture.py';f.write_text(fixture,encoding='utf-8')
 proc=subprocess.run([sys.executable,str(f),str(work)],env={**os.environ,'NC_TRUTH':str(truth),'PYTHONIOENCODING':'utf-8'},capture_output=True,timeout=120)
 (out/'fixture.log').write_bytes(proc.stdout+proc.stderr)
 if proc.returncode:raise RuntimeError(proc.stderr.decode('utf-8','replace'))
 ledger=truth.read_bytes();truth.unlink()
 shape=json.loads(proc.stdout.decode('utf-8'))
t0=time.time();agent_rc=0;finish={'kind':'control-arm'};key=os.environ.get('ENVSHIFT_API_KEY','')
if a.arm=='agent':
 assert key,'ENVSHIFT_API_KEY missing'
 prompt=out/'prompt.rendered.md';prompt.write_text(prompt_src+'\n工作目录：`'+work.as_posix()+'`。\nPython 解释器：`'+pathlib.Path(sys.executable).as_posix()+'`。\n',encoding='utf-8')
 dsh=here/'dsh'
 env={**os.environ,'DSH_NM':str(dsh/'node_modules'),'DSH_BRIDGE':str(dsh/'bridge.mjs'),'DSH_CONFIG':str(dsh/'cordis.yaml'),'DSH_HOME_DIR':str(out/'dsh-home'),'DSH_SESSION_ROOT':str(out/'dsh-sessions'),'DSH_RUN_TIMEOUT':str(a.timeout),'DSH_MAX_TOKENS':'131072'}
 env.pop('TASK',None)
 try:
  proc=subprocess.run([sys.executable,str(dsh/'drive_dsh.py'),str(work),a.model,'https://api.llmgateway.io/v1',key,str(out),str(prompt)],cwd=work,env=env,capture_output=True,timeout=a.timeout+120)
  (out/'driver.log').write_bytes(proc.stdout+proc.stderr);agent_rc=proc.returncode
 except subprocess.TimeoutExpired as exc:
  agent_rc=-1;(out/'driver.log').write_bytes((exc.stdout or b'')+(exc.stderr or b'')+b'\nTIMEOUT\n')
 final=json.loads((out/'final.json').read_text(encoding='utf-8')) if (out/'final.json').exists() else {}
 finish=final.get('finishReason')
else:
 with tempfile.TemporaryDirectory(prefix='arm-') as tmp:
  f=pathlib.Path(tmp)/'deliver.py';f.write_text(arm_src,encoding='utf-8')
  proc=subprocess.run([sys.executable,str(f),str(work)],capture_output=True,timeout=120)
  (out/'arm.log').write_bytes(proc.stdout+proc.stderr);agent_rc=proc.returncode
elapsed=int(time.time()-t0)
truth.write_bytes(ledger)
with tempfile.TemporaryDirectory(prefix='grade-') as tmp:
 f=pathlib.Path(tmp)/'check.py';f.write_text(verifier,encoding='utf-8')
 proc=subprocess.run([sys.executable,str(f),str(work),str(truth),str(out/'verifier-log')],capture_output=True,timeout=120)
 (out/'verifier.log').write_bytes(proc.stdout+proc.stderr)
 result=json.loads((out/'verifier-log/trace_results.json').read_text(encoding='utf-8'))
if (work/'output').exists():shutil.copytree(work/'output',public/'delivery',dirs_exist_ok=True)
for name in ('trace.jsonl','final.json','driver.log','fixture.log','verifier.log','prompt.rendered.md'):
 f=out/name
 if f.exists():
  s=f.read_text(encoding='utf-8',errors='replace');s=s.replace(key,'[REDACTED]') if key else s;(public/name).write_text(s,encoding='utf-8')
meta=dict(task=a.task,arm=a.arm,cell=os.environ.get('XOS_CELL','local'),model=a.model if a.arm=='agent' else None,agent_rc=agent_rc,finish_reason=finish,agent_seconds=elapsed,materialization=shape,**result)
(public/'meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print(f"{a.task} cell={meta['cell']} arm={a.arm} reward={result['reward']} 诊断={result['points']}/{result['total']} agent_rc={agent_rc} received={shape['received_files']}/{shape['source_entries']} seconds={elapsed}")
if agent_rc!=0 or (a.arm=='agent' and finish!={'kind':'completed'}):sys.exit(3)
