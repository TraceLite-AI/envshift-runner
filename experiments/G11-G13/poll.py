"""Read status and completed job logs; never modify a remote run."""
import argparse, concurrent.futures, json, pathlib, subprocess
from publish_workflow import ROOT, REPO

def read(args):
    return subprocess.check_output(['gh',*args],text=True,encoding='utf-8',errors='replace',timeout=60)

def poll(arm):
    run = json.loads((ROOT/(arm.upper()+'_RUN.json')).read_text())['run']
    out = ROOT/'runs'/str(run); out.mkdir(parents=True,exist_ok=True)
    status = json.loads(read(['run','view',str(run),'--repo',REPO,'--json','status,conclusion,headSha,jobs,url']))
    (out/'status.json').write_text(json.dumps(status,indent=2))
    def job(j):
        row = {'job':j['name'],'id':j['databaseId'],'status':j['status'],'conclusion':j['conclusion']}
        if j['status']!='completed':
            row['current_step']=[s['name'] for s in j.get('steps',[]) if s['status']=='in_progress']
            return row
        path = out/(str(j['databaseId'])+'.log')
        if not path.exists():
            path.write_text(read(['api',f'repos/{REPO}/actions/jobs/{j["databaseId"]}/logs']))
        lines = path.read_text().splitlines()
        markers = [json.loads(line.split('AGENT_RESULT ',1)[1]) for line in lines if 'AGENT_RESULT {' in line]
        if markers:
            m = markers[-1]
            row.update(valid=m['valid_model_run'],reward=m['reward'],steps=m['steps'],audit=m['audit'],
                       failed_checks=[k for k,v in m['checks'].items() if not v])
        if arm=='control': row['control_result_lines']=sum('CONTROL_RESULT ' in s and '{' in s for s in lines)
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = list(pool.map(job,status['jobs']))
    summary = {'run':run,'status':status['status'],'conclusion':status['conclusion'],'jobs':rows}
    (out/'summary.json').write_text(json.dumps(summary,indent=2))
    display={'run':run,'status':status['status'],'conclusion':status['conclusion'],
             'active':[{'job':r['job'],'step':r.get('current_step')} for r in rows if r['status']=='in_progress'],
             'queued':sum(r['status']=='queued' for r in rows),
             'finished':[{k:r[k] for k in ['job','valid','reward','steps','conclusion'] if k in r} for r in rows if r['status']=='completed']}
    print(json.dumps(display,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('arm',choices=['control','agent']);a=p.parse_args();poll(a.arm)
