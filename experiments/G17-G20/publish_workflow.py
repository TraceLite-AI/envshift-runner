"""Publish only an explicit list of synthetic task sources and aggregate planning records."""
import base64,hashlib,json,pathlib,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parent
REPO='TraceLite-AI/envshift-runner'
BRANCH='codex/gui-batch6-20260915'
PARENT='ca224a34c12154311b19af59722a680f12933b3f'
SOURCE=['gui_batch6.py','gui_agent_loop.py','task_world.py','app.js','app.css','scroll_probe.py']

def api(path,payload=None,method='POST'):
    args=['gh','api',f'repos/{REPO}/{path}']
    if payload is None:return json.loads(subprocess.check_output(args,timeout=60))
    with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',suffix='.json') as f:
        json.dump(payload,f);f.flush()
        return json.loads(subprocess.check_output(args+['--method',method,'--input',f.name],timeout=60))

if __name__=='__main__':
    assert not (ROOT/'REMOTE.json').exists(),'Already published; inspect before updating'
    assert hashlib.sha256((ROOT/'gui_agent_loop.py').read_bytes()).hexdigest()==json.loads((ROOT/'TOOL_CHANGE.json').read_text())['v3_sha256']
    checks=json.loads((ROOT/'LOCAL_CHECKS.json').read_text());assert checks['passed']>=30
    preview=json.loads((ROOT/'local_preview/CHECKS.json').read_text());assert len(preview)==4 and all(r['ui_smoke_passed'] for r in preview)
    parent=api('git/commits/'+PARENT)
    old=api('contents/badcases/INDEX.json?ref='+PARENT)
    prior=base64.b64decode(old['content']);assert len(json.loads(prior))==22
    (ROOT/'PRIOR_BADCASES.json').write_bytes(prior)
    manifest={'tasks':['G17','G18','G19','G20'],'runners':['ubuntu-24.04','macos-15','windows-2022'],
              'model':'gemini-3.5-flash','tool_version':'gui_native_v3_scroll','steps':60,'max_parallel':3,
              'source_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in SOURCE},
              'prior_result_commit':PARENT,'status':'awaiting_controls','new_badcases':0,
              'publication_mode':'synthetic_sources_and_aggregate_records_only','full_evidence_storage':'local'}
    (ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    entries=[]
    def add(remote,local):entries.append({'path':remote,'mode':'100644','type':'blob','content':local.read_text()})
    for name in SOURCE:add(name,ROOT/name)
    oldattrs=base64.b64decode(api('contents/.gitattributes?ref='+PARENT)['content']).decode()
    attrs=oldattrs.rstrip()+'\n'
    for name in SOURCE:
        if '/'+name+' text eol=lf' not in attrs:attrs+='/'+name+' text eol=lf\n'
    entries.append({'path':'.gitattributes','mode':'100644','type':'blob','content':attrs})
    add('.github/workflows/gui-run.yml',ROOT/'gui-run.yml')
    allowed=SOURCE+['gui-run.yml','README.md','BENCHMARK_REFERENCES.md','TEST_PLAN.md','CONTINUE.md','EXPERIMENT.json','LOCAL_CHECKS.json',
        'check_verifiers.py','make_tasks.py','publish_workflow.py','dispatch.py','poll.py','collect.py','watch.py','unpack_archives.py','local_preview.py','serve.py','TOOL_CHANGE.json']
    for name in allowed:add('experiments/G17-G20/'+name,ROOT/name)
    for p in sorted((ROOT/'tasks').rglob('*')):
        if p.is_file():
            rel=p.relative_to(ROOT).as_posix();add(rel,p);add('experiments/G17-G20/'+rel,p)
    tree=api('git/trees',{'base_tree':parent['tree']['sha'],'tree':entries})
    commit=api('git/commits',{'message':'Add G17-G20 spreadsheet, recurring calendar, slide and file handoff GUI tasks','tree':tree['sha'],'parents':[PARENT]})
    api('git/refs',{'ref':'refs/heads/'+BRANCH,'sha':commit['sha']})
    assert api('git/ref/heads/'+BRANCH)['object']['sha']==commit['sha']
    # Tree inheritance must preserve every previous permanent badcase artifact.
    before=api('git/trees/'+parent['tree']['sha']+'?recursive=1')['tree'];after=api('git/trees/'+tree['sha']+'?recursive=1')['tree']
    filt=lambda xs:{x['path']:x['sha'] for x in xs if x['path'].startswith('badcases/') and x['type']=='blob'}
    assert filt(before)==filt(after)
    manifest['source_commit']=commit['sha'];(ROOT/'EXPERIMENT.json').write_text(json.dumps(manifest,indent=2)+'\n')
    record={'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],'source_commit':commit['sha'],'prior_badcase_blobs_preserved':True}
    (ROOT/'REMOTE.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record),flush=True)
