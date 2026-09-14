"""Create a standalone local evidence package after remote readback succeeds."""
import hashlib, json, pathlib, zipfile
from publish_workflow import ROOT

remote=json.loads((ROOT/'RESULTS_REMOTE.json').read_text())
assert remote['readback_verified']
assert json.loads((ROOT/'SUMMARY.json').read_text())['complete']
def included(path):
    return path.is_file() and '__pycache__' not in path.parts and not path.name.endswith('_PENDING.json')
files=[p for p in sorted(ROOT.rglob('*')) if included(p) and p.name not in ['SHA256.json','PACKAGE.json']]
manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
(ROOT/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
packet=ROOT.parent/(ROOT.name+'.zip')
with zipfile.ZipFile(packet,'w',zipfile.ZIP_DEFLATED) as z:
    for p in files+[ROOT/'SHA256.json']:
        z.write(p,str(p.relative_to(ROOT.parent)))
with zipfile.ZipFile(packet) as z:
    assert z.testzip() is None
    for name,digest in manifest.items():
        assert hashlib.sha256(z.read(ROOT.name+'/'+name)).hexdigest()==digest
record={'path':str(packet),'files':len(files)+1,'size':packet.stat().st_size,
        'sha256':hashlib.sha256(packet.read_bytes()).hexdigest(),'all_files_verified':True,
        'report_url':remote['report_url']}
(ROOT/'PACKAGE.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,ensure_ascii=False),flush=True)
