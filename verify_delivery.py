"""Offline delivery verifier. G23 also requires the actual artifact directory."""
import argparse,base64,json,pathlib
from task_world import PROMPTS,fixture,grade

def verify(task,state,artifacts=None):
    result=grade(task,state)
    if task=='G23':
        root=pathlib.Path(artifacts) if artifacts else None
        expected=state.get('exports',{}).get('badge.png')
        export=root/'exports/badge.png' if root else None
        source=root/'source.png' if root else None
        result['checks']['export_file_matches_saved_delivery']=bool(expected and export and export.is_file()) and export.read_bytes()==base64.b64decode(expected)
        result['checks']['source_file_unchanged']=bool(source and source.is_file()) and source.read_bytes()==base64.b64decode(fixture(task)['source_png'])
        result['reward']=int(all(result['checks'].values()))
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--task',required=True,choices=list(PROMPTS));p.add_argument('--result',required=True);p.add_argument('--artifacts');a=p.parse_args()
    raw=json.loads(pathlib.Path(a.result).read_text(encoding='utf-8'));r=verify(a.task,raw.get('state',raw),a.artifacts)
    print(json.dumps(r,indent=2));raise SystemExit(0 if r['reward']==1 else 1)
