"""Retry artifact transfers independently and preserve completed downloads."""
import argparse,json,pathlib,shutil,subprocess,tempfile,time
ap=argparse.ArgumentParser();ap.add_argument('run',type=int);ap.add_argument('--out',required=True);a=ap.parse_args();root=pathlib.Path(__file__).resolve().parent/a.out;root.mkdir(parents=True,exist_ok=True)
meta=json.loads(subprocess.check_output(['gh','api',f'repos/TraceLite-AI/envshift-runner/actions/runs/{a.run}/artifacts?per_page=100']))
for art in meta['artifacts']:
 name=art['name']
 if not name.startswith('gui-batch3-'):continue
 target=root/name
 if (target/'meta.json').exists() and (target/'agent/loop.json').exists():
  loop=json.loads((target/'agent/loop.json').read_text())
  if len(list((target/'agent').glob('step*.png')))>=loop.get('steps',0):continue
 for attempt in range(4):
  temp=pathlib.Path(tempfile.mkdtemp(prefix='.download-',dir=root));ok=False
  try:
   p=subprocess.run(['gh','run','download',str(a.run),'--repo','TraceLite-AI/envshift-runner','--name',name,'--dir',str(temp)],capture_output=True,text=True,timeout=300);ok=p.returncode==0
  except subprocess.TimeoutExpired:pass
  if ok:
   if target.exists():shutil.copytree(temp,target,dirs_exist_ok=True);shutil.rmtree(temp)
   else:temp.rename(target)
   print(name,'downloaded',flush=True);break
  shutil.rmtree(temp);print(name,'transfer failed; retry',attempt+1,flush=True)
  if attempt==3:raise RuntimeError('Artifact transport failed: '+name)
  time.sleep(2)
