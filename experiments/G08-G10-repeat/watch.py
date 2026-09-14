"""Monitor already-dispatched trials and collect completed artifacts; no dispatches."""
import json, subprocess, sys, time
from publish_workflow import ROOT

previous=None; collected=-1; errors=0
for _ in range(120):
    try:
        p=subprocess.run([sys.executable,str(ROOT/'poll.py'),'agent'],capture_output=True,text=True,timeout=180)
        if p.returncode:raise RuntimeError('Status collection failed')
        run=json.loads((ROOT/'AGENT_RUN.json').read_text())['run']
        summary=json.loads((ROOT/'runs'/str(run)/'summary.json').read_text())
        current=json.dumps(summary,sort_keys=True)
        if current!=previous:
            print(p.stdout.strip(),flush=True);previous=current
        finished=sum(j['status']=='completed' for j in summary['jobs'])
        if finished>collected:
            q=subprocess.run([sys.executable,str(ROOT/'collect.py'),'agent'],timeout=240)
            if q.returncode:raise RuntimeError('Artifact collection failed')
            collected=finished
        errors=0
        if summary['status']=='completed':
            q=subprocess.run([sys.executable,str(ROOT/'collect.py'),'agent'],timeout=240)
            if q.returncode:raise RuntimeError('Final artifact collection failed')
            print('ALL_TRIALS_FINISHED',flush=True);break
    except Exception as e:
        errors+=1;print('MONITOR_RETRY',type(e).__name__,str(e),flush=True)
        if errors>=3:raise
    time.sleep(40)
