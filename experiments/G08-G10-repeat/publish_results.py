"""Publish completed repeat results and preserve every earlier badcase blob."""
import base64, hashlib, json, pathlib
from publish_workflow import api, ROOT, REPO, BRANCH

remote=json.loads((ROOT/'REMOTE.json').read_text())
assert not (ROOT/'RESULTS_REMOTE.json').exists(), 'Results already published.'
assert api('git/ref/heads/'+BRANCH)['object']['sha']==remote['commit'], 'Branch changed; inspect first.'
summary=json.loads((ROOT/'SUMMARY.json').read_text())
assert summary['complete'] and summary['source_and_runtime_uniform']
assert all(g['valid']==5 for g in summary['groups'])
assert (ROOT/'OBSERVATIONS.md').exists(), 'Review trajectories before publishing.'
old_tree=api('git/trees/'+remote['tree']+'?recursive=1')
assert not old_tree.get('truncated')
old_paths={e['path']:e for e in old_tree['tree']}
old_index_path=ROOT/'PRIOR_BADCASES.json'
old_data=old_index_path.read_bytes()
assert hashlib.sha1(b'blob '+str(len(old_data)).encode()+b'\0'+old_data).hexdigest()==old_paths['badcases/INDEX.json']['sha']
old_index=json.loads(old_data);new_index=json.loads((ROOT/'badcases/INDEX.json').read_text())
assert not ({r['id'] for r in old_index}&{r['id'] for r in new_index})
prefix='experiments/G08-G10-repeat/'
entries=[];artifacts=[];archive_blobs={}
for archive in sorted((ROOT/'archives').glob('*.tar.xz')):
    data=archive.read_bytes()
    blob=api('git/blobs',{'encoding':'base64','content':base64.b64encode(data).decode()})
    expected=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert blob['sha']==expected
    rel=str(archive.relative_to(ROOT));archive_blobs[rel]=blob['sha']
    entries.append({'path':prefix+rel,'mode':'100644','type':'blob','sha':blob['sha']})
    artifacts.append({'path':rel,'size':len(data),'sha256':hashlib.sha256(data).hexdigest(),'git_blob':blob['sha']})
    print('ARCHIVED',archive.name,len(data),flush=True)
for record in new_index:
    bid=record['id'];blob=archive_blobs[record['failure']['archive']]
    entries.append({'path':f'badcases/{bid}/evidence.tar.xz','mode':'100644','type':'blob','sha':blob})
    entries.append({'path':f'badcases/{bid}/badcase.json','mode':'100644','type':'blob','content':json.dumps(record,ensure_ascii=False,indent=2)})
entries.append({'path':'badcases/INDEX.json','mode':'100644','type':'blob','content':json.dumps(old_index+new_index,ensure_ascii=False,indent=2)+'\n'})
old_readme=api('git/blobs/'+old_paths['badcases/README.md']['sha'])
readme=base64.b64decode(old_readme['content']).decode('utf-8')
readme+='\n## G08 / G10 prospective repeats\n\n'
readme+=f'{len(new_index)} additional failure trajectories were retained from five fresh Ubuntu trials per task. '
readme+='These are repeats of existing tasks, not new task identities or proven OS mechanisms. '
readme+='See the [repeat report](../experiments/G08-G10-repeat/REPORT.md) and [trajectory review](../experiments/G08-G10-repeat/OBSERVATIONS.md).\n'
entries.append({'path':'badcases/README.md','mode':'100644','type':'blob','content':readme})
for path in sorted(ROOT.rglob('*')):
    if not path.is_file() or '__pycache__' in path.parts:continue
    rel=path.relative_to(ROOT)
    include=(len(rel.parts)==1 and path.suffix in ['.json','.md','.py','.yml','.html']) or rel.parts[0]=='source' or (rel.parts[0]=='badcases' and path.suffix=='.json') or (rel.parts[0]=='evidence' and path.name in ['meta.json','loop.json','environment.json','instruction.txt','agent.log','runtime.json','pip-freeze.txt','VERIFIED.json','EVIDENCE_SHA256.json']) or (rel.parts[0]=='runs' and path.suffix=='.json')
    if include:entries.append({'path':prefix+str(rel),'mode':'100644','type':'blob','content':path.read_text()})
tree=api('git/trees',{'base_tree':remote['tree'],'tree':entries})
commit=api('git/commits',{'message':'Archive prospective G08 and G10 repeated GUI trials with full evidence','tree':tree['sha'],'parents':[remote['commit']]})
api('git/refs/heads/'+BRANCH,{'sha':commit['sha'],'force':False},'PATCH')
assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
readback=api('git/trees/'+tree['sha']+'?recursive=1')
assert not readback.get('truncated')
paths={e['path']:e for e in readback['tree']}
for path,old in old_paths.items():
    if path.startswith('badcases/') and old['type']=='blob' and path not in ['badcases/INDEX.json','badcases/README.md']:
        assert paths[path]['sha']==old['sha'], 'Earlier badcase changed: '+path
for artifact in artifacts:assert paths[prefix+artifact['path']]['sha']==artifact['git_blob']
result={'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],
        'workflow_commit':remote['commit'],'source_commit':remote['source_commit'],
        'readback_verified':True,'earlier_badcases_preserved':len(old_index),'new_failure_trajectories':len(new_index),
        'all_badcase_tasks':sorted({r['task'] for r in old_index+new_index}),
        'report_url':f'https://github.com/{REPO}/blob/{commit["sha"]}/{prefix}REPORT.md','artifacts':artifacts}
(ROOT/'RESULTS_REMOTE.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='artifacts'}),flush=True)
