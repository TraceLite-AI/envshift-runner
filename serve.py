"""Manual review only; Ctrl+C saves state, grade and materialized exports."""
import argparse,json,pathlib,time
from task_server import TaskSession
from task_world import PROMPTS,GUARD

p=argparse.ArgumentParser();p.add_argument('--task',choices=list(PROMPTS),required=True);p.add_argument('--out',default='manual-review');a=p.parse_args()
out=pathlib.Path(a.out);session=TaskSession(a.task,out)
print(PROMPTS[a.task]+' '+GUARD,flush=True);print(session.url,flush=True)
try:
    while True:time.sleep(.5)
except KeyboardInterrupt:pass
finally:
    result={'task':a.task,'kind':'manual_not_model_trial',**session.result()};session.close();(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'reward':result['reward'],'checks':result['checks'],'output':str(out.resolve())}))
