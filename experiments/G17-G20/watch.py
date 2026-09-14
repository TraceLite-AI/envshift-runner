"""Read existing runs and collect complete artifacts; never dispatch work."""
import argparse, json, time
from publish_workflow import ROOT
from poll import poll
from collect import collect
p=argparse.ArgumentParser();p.add_argument('arm',choices=['control','agent']);a=p.parse_args()
for _ in range(120):
    poll(a.arm)
    run=json.loads((ROOT/(a.arm.upper()+'_RUN.json')).read_text())['run']
    status=json.loads((ROOT/'runs'/str(run)/'status.json').read_text())
    if any(j['status']=='completed' for j in status['jobs']):collect(a.arm)
    if status['status']=='completed':break
    time.sleep(40)
else:raise RuntimeError('Watcher timed out; remote run has not been cancelled')
