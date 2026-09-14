"""Fetch compact original artifacts, validate every file, and summarize fresh trials."""
import argparse, hashlib, io, json, pathlib, ssl, subprocess, tarfile, time, urllib.error, urllib.request, zipfile
import certifi
from publish_workflow import api, ROOT, REPO

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None

def collect(arm):
    record = json.loads((ROOT/(arm.upper()+'_RUN.json')).read_text())
    artifacts = api(f'actions/runs/{record["run"]}/artifacts?per_page=100')['artifacts']
    context = ssl.create_default_context(cafile=certifi.where())
    opener = urllib.request.build_opener(NoRedirect,urllib.request.HTTPSHandler(context=context))
    key = subprocess.check_output(['gh','auth','token'],text=True).strip()
    source = json.loads((ROOT/'EXPERIMENT.json').read_text())
    rows=[]
    for artifact in artifacts:
        name=artifact['name']
        if not name.startswith('gui-batch6init-') or '-'+arm+'-' not in name: continue
        dest=ROOT/'evidence'/str(record['run'])/name; archive=ROOT/'archives'/(str(record['run'])+'-'+name+'.tar.xz')
        if not (dest/'VERIFIED.json').exists():
            for attempt in range(3):
                try:
                    request=urllib.request.Request(f'https://api.github.com/repos/{REPO}/actions/artifacts/{artifact["id"]}/zip',
                        headers={'Authorization':'Bearer '+key,'Accept':'application/vnd.github+json'})
                    try: response=opener.open(request,timeout=25)
                    except urllib.error.HTTPError as e:
                        if e.code not in (301,302,303,307,308):raise
                        location=e.headers['Location']
                        if not location.startswith('https://'):raise RuntimeError('Non-HTTPS artifact redirect')
                        response=urllib.request.urlopen(location,timeout=25,context=context)
                    with response: data=response.read()
                    expected=artifact.get('digest')
                    if expected: assert expected=='sha256:'+hashlib.sha256(data).hexdigest()
                    with zipfile.ZipFile(io.BytesIO(data)) as z:
                        assert z.testzip() is None
                        packet=z.read('evidence.tar.xz')
                    archive.parent.mkdir(parents=True,exist_ok=True); archive.write_bytes(packet)
                    dest.mkdir(parents=True,exist_ok=True)
                    with tarfile.open(fileobj=io.BytesIO(packet),mode='r:xz') as tar:
                        for member in tar.getmembers():
                            rel=pathlib.PurePosixPath(member.name)
                            assert not rel.is_absolute() and '..' not in rel.parts
                            assert member.isfile() or member.isdir(), 'Unexpected archive member'
                        tar.extractall(dest)
                    files=json.loads((dest/'evidence/EVIDENCE_SHA256.json').read_text())
                    for rel,digest in files.items():
                        path=pathlib.PurePosixPath(rel)
                        assert not path.is_absolute() and '..' not in path.parts
                        assert hashlib.sha256((dest/'evidence'/rel).read_bytes()).hexdigest()==digest, rel
                    verification={'artifact_id':artifact['id'],'run':record['run'],'files_verified':len(files),
                                  'zip_sha256':hashlib.sha256(data).hexdigest(),'archive_sha256':hashlib.sha256(packet).hexdigest()}
                    (dest/'VERIFIED.json').write_text(json.dumps(verification,indent=2))
                    print('VERIFIED',name,len(files),'files',flush=True);break
                except Exception as e:
                    print('DOWNLOAD_RETRY',name,attempt+1,type(e).__name__,flush=True)
                    if attempt==2:raise RuntimeError('Artifact collection failed: '+name) from None
                    time.sleep(2)
        d=dest/'evidence'
        runtime=json.loads((d/'repeat_metadata/runtime.json').read_text())
        assert runtime['source_commit']==source['source_commit'] and runtime['source_sha256']==source['source_sha256']
        meta=json.loads((d/'meta.json').read_text()) if (d/'meta.json').exists() else {}
        row={'task':runtime['task'],'trial':int(runtime['trial']),'run':record['run'],
             'artifact':name,'evidence':str(d.relative_to(ROOT)),'archive':str(archive.relative_to(ROOT)),
             'verified':True,'source_verified':True,'meta':meta,'runtime':runtime,
             'environment':json.loads((d/'environment.json').read_text()) if (d/'environment.json').exists() else {},
             'pip_freeze':(d/'repeat_metadata/pip-freeze.txt').read_text()}
        if arm=='control':
            checks=meta.get('results',[])
            row['verified']=bool(meta.get('control_passed')) and len(checks)==2 and all(r['materialized'] and r['reward']==int(r['arm']=='oracle') for r in checks)
        else:
            loop=json.loads((d/'agent/loop.json').read_text()) if (d/'agent/loop.json').exists() else {}
            row.update(valid=bool(meta.get('valid_model_run')) and loop.get('tool_version')==source['tool_version'] and loop.get('coordinate_mode')=='normalized_0_1000',
                       reward=meta.get('reward'),steps=meta.get('steps'),last_action=loop.get('history',[{}])[-1].get('action') if loop.get('history') else None)
        rows.append(row)
    rows.sort(key=lambda r:(r['task'],r['trial']))
    payload=json.dumps(rows,ensure_ascii=False,indent=2)+'\n'
    (ROOT/(arm.upper()+'_RESULTS.json')).write_text(payload)
    run_dir=ROOT/'runs'/str(record['run']);run_dir.mkdir(parents=True,exist_ok=True)
    (run_dir/(arm.upper()+'_RESULTS.json')).write_text(payload)
    print(json.dumps([{'task':r['task'],'os':r['runtime']['runner_image']['RUNNER_OS'],'trial':r['trial'],'verified':r['verified'],**{k:r[k] for k in ['valid','reward','steps'] if k in r}} for r in rows]),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('arm',choices=['control','agent']);a=p.parse_args();collect(a.arm)
