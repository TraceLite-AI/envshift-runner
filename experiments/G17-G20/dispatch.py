"""Exactly one dispatch per arm; require all current-source controls before model trials."""
import argparse,json,re,subprocess
from publish_workflow import api,ROOT,REPO,BRANCH
p=argparse.ArgumentParser();p.add_argument('arm',choices=['control','agent']);a=p.parse_args()
record=ROOT/(a.arm.upper()+'_RUN.json');pending=ROOT/(a.arm.upper()+'_DISPATCH_PENDING.json')
assert not record.exists() and not pending.exists(),'Inspect existing dispatch before retrying'
remote=json.loads((ROOT/'REMOTE.json').read_text());source=json.loads((ROOT/'EXPERIMENT.json').read_text())
assert api('git/ref/heads/'+BRANCH)['object']['sha']==remote['commit']
if a.arm=='agent':
    controls=json.loads((ROOT/'CONTROL_RESULTS.json').read_text())
    assert len(controls)==12 and all(r['verified'] and r['runtime']['source_commit']==source['source_commit'] and r['runtime']['source_sha256']==source['source_sha256'] for r in controls)
    assert len({(r['task'],r['runtime']['runner_image']['RUNNER_OS']) for r in controls})==12
    assert all(json.loads((ROOT/r['evidence']/'scroll-probe.json').read_text())['passed'] for r in controls)
inputs={'arm':a.arm,'oslist':json.dumps(source['runners']),'tasks':json.dumps(source['tasks']),
        'trials':'[1]','model':source['model'],'steps':str(source['steps'])}
pending.write_text(json.dumps({'workflow_commit':remote['commit'],'inputs':inputs},indent=2))
cmd=['gh','workflow','run','gui-run.yml','--repo',REPO,'--ref',BRANCH]
for k,v in inputs.items():cmd+=['-f',k+'='+v]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=90);match=re.search(r'/actions/runs/(\d+)',r.stdout+r.stderr)
if r.returncode or not match:raise RuntimeError('Dispatch outcome uncertain; inspect pending record and GitHub before retrying')
row={'run':int(match.group(1)),'workflow_commit':remote['commit'],'source_commit':remote['source_commit'],
     'url':f'https://github.com/{REPO}/actions/runs/'+match.group(1),'inputs':inputs}
record.write_text(json.dumps(row,indent=2)+'\n');pending.unlink();print(json.dumps(row),flush=True)
