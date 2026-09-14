"""Publish only an explicit list of synthetic task sources and aggregate planning records."""
import base64,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
REPO='TraceLite-AI/envshift-runner'
BRANCH='codex/gui-batch5-windowfit-20260914'
PARENT='c44f8289162ca536596e93e0c60446e21a4af5eb'
SOURCE=['gui_batch5.py','gui_agent_loop.py','task_world.py','app.js','app.css']

def api(path,payload=None,method='POST'):
    args=['gh','api',f'repos/{REPO}/{path}']
    if payload is None:return json.loads(subprocess.check_output(args,timeout=60))
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json') as f:
        json.dump(payload,f);f.flush()
        return json.loads(subprocess.check_output(args+['--method',method,'--input',f.name],timeout=60))

if __name__=='__main__':
    assert not (ROOT/'REMOTE.json').exists()
    parent=api('git/commits/'+PARENT)
    original=ROOT.parent.parent
    for n in SOURCE[1:]:assert (ROOT/n).read_bytes()==(original/n).read_bytes()
    manifest={'tasks':['G14','G15','G16'],'runners':['windows-2022'],'model':'gemini-3.5-flash','tool_version':'gui_native_v2','steps':60,'max_parallel':3,
              'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCE},
              'prior_source_commit':PARENT,'status':'awaiting_controls','amendment':'maximize Windows Chrome before the trial; business rules and agent unchanged','full_evidence_storage':'local'}
    (ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entries=[{'path':n,'mode':'100644','type':'blob','content':(ROOT/n).read_text()} for n in SOURCE]
    entries.append({'path':'.github/workflows/gui-run.yml','mode':'100644','type':'blob','content':(ROOT/'gui-run.yml').read_text()})
    for name in SOURCE+['gui-run.yml','EXPERIMENT.json','PROTOCOL_AMENDMENT.md','publish_workflow.py','dispatch.py','poll.py','collect.py','watch.py']:
        entries.append({'path':'experiments/G14-G16/diagnostics/window-fit/'+name,'mode':'100644','type':'blob','content':(ROOT/name).read_text()})
    tree=api('git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})
    commit=api('git/commits',{'message':'Fix Windows GUI viewport before G14-G16 validation; preserve original trials','tree':tree['sha'],'parents':[PARENT]})
    api('git/refs',{'ref':'refs/heads/'+BRANCH,'sha':commit['sha']})
    assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
    manifest['source_commit']=commit['sha'];(ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record={'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],'source_commit':commit['sha']}
    (ROOT/'REMOTE.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
