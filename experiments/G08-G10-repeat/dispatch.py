"""Dispatch once, recording pending state before the mutating request."""
import argparse, json, pathlib, re, subprocess
from publish_workflow import api, ROOT, REPO, BRANCH

p = argparse.ArgumentParser()
p.add_argument('arm', choices=['control','agent'])
a = p.parse_args()
record = ROOT / (a.arm.upper()+'_RUN.json')
pending = ROOT / (a.arm.upper()+'_DISPATCH_PENDING.json')
assert not record.exists() and not pending.exists(), 'Inspect existing dispatch before retrying.'
remote = json.loads((ROOT/'REMOTE.json').read_text())
assert api('git/ref/heads/'+BRANCH)['object']['sha'] == remote['commit']
if a.arm == 'agent':
    controls = json.loads((ROOT/'CONTROL_RESULTS.json').read_text())
    assert len(controls)==2 and all(x['verified'] for x in controls), 'Both controls must be verified before model runs.'
trials = [1] if a.arm == 'control' else [1,2,3,4,5]
inputs = {'arm':a.arm, 'oslist':'["ubuntu-24.04"]','tasks':'["G08","G10"]',
          'trials':json.dumps(trials), 'model':'gemini-3.5-flash', 'steps':'60'}
pending.write_text(json.dumps({'workflow_commit':remote['commit'],'inputs':inputs},indent=2))
cmd = ['gh','workflow','run','gui-run.yml','--repo',REPO,'--ref',BRANCH]
for k,v in inputs.items(): cmd += ['-f',k+'='+v]
result = subprocess.run(cmd,capture_output=True,text=True,timeout=90)
match = re.search(r'/actions/runs/(\d+)',result.stdout+result.stderr)
if result.returncode or not match:
    raise RuntimeError('Dispatch outcome uncertain; inspect pending record and GitHub before retrying.')
row = {'run':int(match.group(1)),'workflow_commit':remote['commit'],'source_commit':remote['source_commit'],
       'url':f'https://github.com/{REPO}/actions/runs/'+match.group(1),'inputs':inputs}
record.write_text(json.dumps(row,indent=2)+'\n'); pending.unlink()
print(json.dumps(row),flush=True)
