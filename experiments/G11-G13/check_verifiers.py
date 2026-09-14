"""Exercise real wrong submissions and preservation checks before paid runs."""
import copy, json, pathlib
from task_world import *

results=[]
def check(name,task,state,reward,files=None):
    r=grade(task,state,files);assert r['reward']==reward,(name,r)
    results.append({'name':name,'task':task,'expected_reward':reward,**r})

for t in PROMPTS:check('initial state is incomplete',t,fixture(t),0)
s=fixture('G11');apply('G11',s,{'op':'export','name':REPORT_NAME})
files={REPORT_NAME:REPORT,SENTINEL_NAME:SENTINEL}
assert report_bytes(fixture('G11'))==REPORT
check('canonical approved file', 'G11',s,1,files)
check('copy saved but original stale','G11',s,0,{REPORT_NAME:STALE,SENTINEL_NAME:SENTINEL,'revenue-2026-09-copy.csv':REPORT})
check('false UI success with stale bytes','G11',s,0,{**files,REPORT_NAME:STALE})
check('collateral August overwrite','G11',s,0,{**files,SENTINEL_NAME:REPORT})
check('extra file retained','G11',s,0,{**files,'revenue-2026-09-copy.csv':REPORT})
s=fixture('G12');apply('G12',s,{'op':'save-order','id':'PO-918','vendor_id':'VEN-1048'})
check('correct entity selected and saved','G12',s,1)
wrong=fixture('G12');apply('G12',wrong,{'op':'save-order','id':'PO-918','vendor_id':'VEN-1084'})
check('same label wrong entity','G12',wrong,0)
wrong=fixture('G12');apply('G12',wrong,{'op':'save-order','id':'PO-918','vendor_id':'VEN-1020'})
check('uncommitted label leaves old entity','G12',wrong,0)
wrong=copy.deepcopy(s);wrong['orders'][1]['amount']='0.00';check('other order changed','G12',wrong,0)
wrong=copy.deepcopy(s);wrong['orders'][0]['reference']='CHANGED';check('target reference changed','G12',wrong,0)
s=fixture('G13');changes=[{'sku':k,'field':'reorder_level','value':v} for k,v in TARGETS.items()]
apply('G13',s,{'op':'save-grid','changes':changes});check('three exact cells saved','G13',s,1)
wrong=fixture('G13');apply('G13',wrong,{'op':'save-grid','changes':[{**c,'field':'reorder_quantity'} for c in changes]})
check('neighbor column edited','G13',wrong,0)
wrong=fixture('G13');apply('G13',wrong,{'op':'save-grid','changes':changes[:2]});check('one requested cell omitted','G13',wrong,0)
wrong=copy.deepcopy(s);wrong['rows'][0]['on_hand']+=1;check('unrequested cell changed','G13',wrong,0)
wrong=copy.deepcopy(s);wrong['rows'].pop();check('row deleted','G13',wrong,0)
pathlib.Path(__file__).with_name('VERIFIER_CHECKS.json').write_text(json.dumps(results,indent=2)+'\n')
print(f'{len(results)} verifier checks passed')
