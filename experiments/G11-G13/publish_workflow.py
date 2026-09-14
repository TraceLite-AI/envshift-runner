"""Append new GUI tasks on an isolated branch without replacing old evidence."""
import base64, hashlib, json, pathlib, subprocess, tempfile
ROOT=pathlib.Path(__file__).resolve().parent
REPO='TraceLite-AI/envshift-runner'
BRANCH='codex/gui-batch4-20260914'
PARENT='74f0b6cd6a0d74631bc7ee6fe06874f2bf9f868e'

def api(path,payload=None,method='POST'):
    args=['gh','api',f'repos/{REPO}/{path}']
    if payload is None:return json.loads(subprocess.check_output(args,timeout=60))
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json') as f:
        json.dump(payload,f);f.flush()
        return json.loads(subprocess.check_output(args+['--method',method,'--input',f.name],timeout=60))

if __name__=='__main__':
    assert not (ROOT/'REMOTE.json').exists(),'Already published; inspect before updating'
    parent=api('git/commits/'+PARENT)
    old=api('contents/badcases/INDEX.json?ref='+PARENT)
    (ROOT/'PRIOR_BADCASES.json').write_bytes(base64.b64decode(old['content']))
    assert len(json.loads((ROOT/'PRIOR_BADCASES.json').read_text()))==22
    names=['gui_batch4.py','gui_agent_loop.py','task_world.py','app.js','app.css']
    manifest={'tasks':['G11','G12','G13'],'runners':['ubuntu-24.04','macos-15','windows-2022'],
              'model':'gemini-3.5-flash','tool_version':'gui_native_v2','steps':60,'max_parallel':3,
              'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names},
              'prior_result_commit':PARENT,'status':'awaiting_controls','new_badcases':0}
    (ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entries=[{'path':n,'mode':'100644','type':'blob','content':(ROOT/n).read_text()} for n in names]
    # The GUI experiment does not test source-file line endings; use identical source bytes on all three OSes.
    entries.append({'path':'.gitattributes','mode':'100644','type':'blob','content':''.join('/'+n+' text eol=lf\n' for n in names)})
    entries.append({'path':'.github/workflows/gui-run.yml','mode':'100644','type':'blob','content':(ROOT/'gui-run.yml').read_text()})
    for path in sorted(ROOT.rglob('*')):
        if path.is_file() and '__pycache__' not in path.parts and path.suffix in ['.py','.md','.json','.yml','.js','.css']:
            entries.append({'path':'experiments/G11-G13/'+path.relative_to(ROOT).as_posix(),'mode':'100644','type':'blob','content':path.read_text()})
    for path in sorted((ROOT/'tasks').rglob('*')):
        if path.is_file():entries.append({'path':path.relative_to(ROOT).as_posix(),'mode':'100644','type':'blob','content':path.read_text()})
    for name in ['ENVSHIFT_STATUS.md','ENVSHIFT_STATUS.json']:
        entries.append({'path':name,'mode':'100644','type':'blob','content':(ROOT.parent/name).read_text()})
    tree=api('git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})
    commit=api('git/commits',{'message':'Add G11-G13 GUI export, supplier selection and wide-grid tasks','tree':tree['sha'],'parents':[PARENT]})
    api('git/refs',{'ref':'refs/heads/'+BRANCH,'sha':commit['sha']})
    assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
    manifest['source_commit']=commit['sha'];(ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record={'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],'source_commit':commit['sha']}
    (ROOT/'REMOTE.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
