"""Publish the reviewed repeat workflow on a new experiment branch."""
import hashlib, json, pathlib, subprocess, tempfile

ROOT = pathlib.Path(__file__).resolve().parent
REPO = 'TraceLite-AI/envshift-runner'
BRANCH = 'codex/gui-repeat-20260914'
PARENT = 'b16cdf13c04f4444b26699f55c185f0527c92fa7'

def api(path, payload=None, method='POST'):
    args = ['gh','api',f'repos/{REPO}/{path}']
    if payload is None:
        return json.loads(subprocess.check_output(args))
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json') as f:
        json.dump(payload,f); f.flush()
        return json.loads(subprocess.check_output(args+['--method',method,'--input',f.name]))

if __name__ == '__main__':
    assert not (ROOT/'REMOTE.json').exists(), 'Already published; inspect instead of duplicating.'
    manifest = json.loads((ROOT/'EXPERIMENT.json').read_text())
    source = api('git/commits/'+manifest['source_commit'])
    source_tree = {e['path']: e for e in api('git/trees/'+source['tree']['sha'])['tree']}
    for name in manifest['source_sha256']:
        data = (ROOT/'source'/name).read_bytes()
        expected = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert source_tree[name]['sha'] == expected, 'Local source differs from tested commit: '+name
    parent = api('git/commits/'+PARENT)
    entries = [{'path':'.github/workflows/gui-run.yml','mode':'100644','type':'blob','content':(ROOT/'gui-run.yml').read_text()}]
    for name in ['EXPERIMENT.json','README.md','gui-run.yml','prepare.py','publish_workflow.py']:
        entries.append({'path':'experiments/G08-G10-repeat/'+name,'mode':'100644','type':'blob','content':(ROOT/name).read_text()})
    tree = api('git/trees', {'base_tree':parent['tree']['sha'],'tree':entries})
    commit = api('git/commits', {'message':'Repeat G08 and G10 with frozen baseline agent on fresh Ubuntu runners','tree':tree['sha'],'parents':[PARENT]})
    api('git/refs', {'ref':'refs/heads/'+BRANCH,'sha':commit['sha']})
    assert api('git/ref/heads/'+BRANCH)['object']['sha'] == commit['sha']
    record = {'repo':REPO,'branch':BRANCH,'commit':commit['sha'],'tree':tree['sha'],'source_commit':manifest['source_commit']}
    (ROOT/'REMOTE.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(record),flush=True)
