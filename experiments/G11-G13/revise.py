"""Publish an inspected reference fix and retain the complete previous control attempt."""
import hashlib,json,pathlib,shutil
from publish_workflow import ROOT,REPO,BRANCH,api
remote=json.loads((ROOT/'REMOTE.json').read_text())
run=json.loads((ROOT/'CONTROL_RUN.json').read_text())
status=json.loads((ROOT/'runs'/str(run['run'])/'status.json').read_text())
assert status['status']=='completed','Wait for the previous controls and their evidence'
rows=json.loads((ROOT/'CONTROL_RESULTS.json').read_text());assert len(rows)==9
assert all((ROOT/r['archive']).exists() for r in rows)
assert api('git/ref/heads/'+BRANCH)['object']['sha']==remote['commit']
dest=ROOT/'control_attempts'/str(run['run']);dest.mkdir(parents=True,exist_ok=True)
for name in ['CONTROL_RUN.json','CONTROL_RESULTS.json','REMOTE.json','EXPERIMENT.json']:
 shutil.copyfile(ROOT/name,dest/name)
manifest=json.loads((ROOT/'EXPERIMENT.json').read_text())
names=list(manifest['source_sha256']);manifest['source_sha256']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
manifest['previous_source_commit']=manifest.pop('source_commit')
entries=[]
for name in names:
 data=(ROOT/name).read_text()
 for prefix in ['', 'experiments/G11-G13/']:entries.append({'path':prefix+name,'mode':'100644','type':'blob','content':data})
for name in ['collect.py','analyze.py','watch.py','revise.py']:
 entries.append({'path':'experiments/G11-G13/'+name,'mode':'100644','type':'blob','content':(ROOT/name).read_text()})
entries.append({'path':'experiments/G11-G13/EXPERIMENT.json','mode':'100644','type':'blob','content':json.dumps(manifest,indent=2)})
tree=api('git/trees',{'base_tree':remote['tree'],'tree':entries})
commit=api('git/commits',{'message':'Correct G11 native Save reference navigation using runner screenshots','tree':tree['sha'],'parents':[remote['commit']]})
api('git/refs/heads/'+BRANCH,{'sha':commit['sha'],'force':False},'PATCH')
assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
manifest['source_commit']=commit['sha'];(ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
new={'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],'source_commit':commit['sha']}
(ROOT/'REMOTE.json').write_text(json.dumps(new,indent=2)+'\n')
(ROOT/'CONTROL_RUN.json').unlink();(ROOT/'CONTROL_RESULTS.json').unlink()
print(json.dumps(new),flush=True)
