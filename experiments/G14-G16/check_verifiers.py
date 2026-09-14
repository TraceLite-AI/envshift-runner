"""Verifier checks against plausible wrong deliveries and valid alternative action order."""
import copy, json, math, pathlib
from task_world import fixture, apply, grade, expected_actions, PROMPTS

results=[]
def check(name,task,s,want):
    r=grade(task,s);assert r['reward']==want,(name,r)
    results.append({'check':name,'task':task,'passed':True})
def solved(task):
    s=fixture(task)
    for a in expected_actions(task):apply(task,s,a)
    return s
for task in PROMPTS:
    check('untouched fixture rejected',task,fixture(task),0)
    check('literal correct delivery accepted',task,solved(task),1)
    s=fixture(task)
    for a in expected_actions(task,False):apply(task,s,a)
    check('plausible wrong delivery rejected',task,s,0)
s=fixture('G14')
computed={p['id']:math.ceil((p['target']-(p['on_hand']-p['reserved']+p['incoming']))/p['pack_size']) for p in s['inventory'] if p['on_hand']-p['reserved']+p['incoming']<p['minimum']}
assert computed=={'KEY-14':7,'DOCK-28':4,'HEAD-36':4}
for pid,q in reversed(list(computed.items())):apply('G14',s,{'op':'cart','product':pid,'quantity':q})
for a in expected_actions('G14')[-2:]:apply('G14',s,a)
check('independently calculated packs; different add order accepted','G14',s,1)
for label,mutate in [
 ('unit count mistaken for pack count',lambda s:s['orders'][0]['items'].update({'KEY-14':35})),
 ('extra non-required boundary item',lambda s:s['orders'][0]['items'].update({'CAM-32':5})),
 ('second otherwise correct order',lambda s:s['orders'].append(copy.deepcopy(s['orders'][0]))),
 ('request left open',lambda s:s['requests'][0].update(status='Open')),
 ('wrong linked order',lambda s:s['requests'][0].update(order_id='PO-9999')),
 ('unrelated request modified',lambda s:s['requests'][1].update(status='Resolved')),
 ('inventory edited',lambda s:s['inventory'][0].update(on_hand=99)),
 ('wrong destination',lambda s:s['orders'][0].update(destination='South Lab')),
 ('wrong reference',lambda s:s['orders'][0].update(reference='REQ-205')),
]:
    s=solved('G14');mutate(s);check(label,'G14',s,0)
for label,mutate in [
 ('wrong size',lambda s:s['cart'][1].update(size='24 L')),
 ('wrong closure',lambda s:s['cart'][1].update(closure='Open')),
 ('double added quantity',lambda s:s['cart'][1].update(quantity=4)),
 ('existing pouch removed',lambda s:s['cart'].pop(0)),
 ('existing pouch quantity changed',lambda s:s['cart'][0].update(quantity=2)),
 ('extra variant',lambda s:s['cart'].append(dict(s['cart'][1],size='12 L'))),
]:
    s=solved('G15');mutate(s);check(label,'G15',s,0)
s=fixture('G15');a=expected_actions('G15')[0];a['quantity']=1;apply('G15',s,a);apply('G15',s,a);s['cart'].reverse();check('two separate additions and cart reorder accepted','G15',s,1)
for label,mutate in [
 ('missed duplicate',lambda s:s['reports'][0].update(status='Open',resolution=None,duplicate_of=None)),
 ('earliest report closed',lambda s:s['reports'][6].update(status='Resolved',resolution='Duplicate',duplicate_of='INC-3101')),
 ('unrelated similar title closed',lambda s:s['reports'][4].update(status='Resolved',resolution='Duplicate',duplicate_of='INC-3108')),
 ('comment lost',lambda s:s['reports'][0].update(comments=[])),
 ('assignee changed',lambda s:s['reports'][2].update(assignee='Lee')),
]:
    s=solved('G16');mutate(s);check(label,'G16',s,0)
s=fixture('G16')
for pid in ['INC-3110','INC-3101','INC-3103']:apply('G16',s,{'op':'duplicate','ids':[pid],'canonical':'INC-3108'})
check('individual resolutions in another order accepted','G16',s,1)
pathlib.Path('LOCAL_CHECKS.json').write_text(json.dumps({'passed':len(results),'checks':results},indent=2)+'\n')
print('PASS',len(results),'verifier checks')
