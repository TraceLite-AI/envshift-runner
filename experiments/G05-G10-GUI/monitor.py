"""Read-only collection of this experiment's GitHub status and completed job logs."""
import argparse,concurrent.futures,json,pathlib,subprocess,time
ap=argparse.ArgumentParser();ap.add_argument('runs',nargs='+',type=int);a=ap.parse_args()
root=pathlib.Path(__file__).resolve().parent

def gh(args):
 for attempt in range(3):
  p=subprocess.run(['gh',*args],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
  if p.returncode==0:return p.stdout
  if attempt<2:time.sleep(2)
 raise RuntimeError('GitHub read failed after retries: '+args[0])
for run in a.runs:
 out=root/'remote'/str(run);out.mkdir(parents=True,exist_ok=True)
 status=json.loads(gh(['run','view',str(run),'--repo','TraceLite-AI/envshift-runner','--json','status,conclusion,headSha,jobs,url']))
 (out/'status.json').write_text(json.dumps(status,indent=2),encoding='utf-8')
 def joblog(j):
  if run==34817662654 and j['conclusion']=='success':return {'job':j['name'],'conclusion':'success'}
  p=out/(str(j['databaseId'])+'.log')
  if not p.exists():p.write_text(gh(['api',f'repos/TraceLite-AI/envshift-runner/actions/jobs/{j["databaseId"]}/logs']),encoding='utf-8')
  lines=p.read_text(encoding='utf-8').splitlines();marks=[x.split('AGENT_RESULT ',1)[1] for x in lines if 'AGENT_RESULT {' in x]
  if marks:
   m=json.loads(marks[-1]);return {'job':j['name'],'run':run,'commit':status['headSha'],'valid':m['valid_model_run'],'reward':m['reward'],'steps':m['steps'],'failed_checks':[k for k,v in m['checks'].items() if not v]}
  return {'job':j['name'],'conclusion':j['conclusion'],'error_lines':[x for x in lines if 'Error:' in x or 'GUI_CONTROL_FAILED' in x][-3:]}
 finished=[j for j in status['jobs'] if j['status']=='completed']
 with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(joblog,finished))
 (out/'summary.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
 display=json.dumps({'run':run,'status':status['status'],'finished':len(finished),'total':len(status['jobs']),'active':[j['name'] for j in status['jobs'] if j['status']=='in_progress'],'results':results},ensure_ascii=False)
 previous=out/"display.json"
 if not previous.exists() or previous.read_text(encoding="utf-8")!=display:print(display,flush=True)
 previous.write_text(display,encoding="utf-8")
