"""Regression boundaries for saved deliveries; these are not model trials."""
import copy,json,pathlib,tempfile,base64
from task_world import PROMPTS,fixture,apply,grade,expected_actions,decode_image,encode_image
from task_server import TaskSession

checks=[]
def run(task,actions=None):
    s=fixture(task)
    for a in expected_actions(task) if actions is None else actions:apply(task,s,a)
    return s
def check(task,name,s,want=0):
    got=grade(task,s);ok=got['reward']==want
    checks.append({'task':task,'name':name,'expected_reward':want,'actual_reward':got['reward'],'passed':ok,'diagnostics':got['checks']})
    assert ok,(task,name,got)
def mutation(task,name,fn,want=0):
    s=run(task);fn(s);check(task,name,s,want)

for t in PROMPTS:
    check(t,'initial is not complete',fixture(t))
    check(t,'reference delivery',run(t),1)
    check(t,'plausible wrong delivery',run(t,expected_actions(t,False)))
    s=run(t);before=copy.deepcopy(s)
    try:apply(t,s,{'op':'nonexistent'})
    except (ValueError,AssertionError):pass
    else:raise AssertionError('Unknown action accepted')
    checks.append({'task':t,'name':'invalid action leaves saved state intact','passed':s==before})
    assert s==before

t='G21'
check(t,'rule saved but existing messages not processed',run(t,expected_actions(t)[:1]))
mutation(t,'missing attachment condition',lambda s:s['rules'][1].update(attachment=False))
mutation(t,'overbroad subject substring despite matching fixture rows',lambda s:s['rules'][1].update(subject='[APPROVED'))
mutation(t,'wrong action label',lambda s:s['rules'][1].update(label='Alert'))
mutation(t,'disabled future rule',lambda s:s['rules'][1].update(enabled=False))
mutation(t,'existing rule deleted',lambda s:s['rules'].pop(0))
mutation(t,'unrelated message changed',lambda s:s['messages'][5].update(read=True))
mutation(t,'duplicate new rule',lambda s:s['rules'].append({**s['rules'][1],'id':'R2'}))
mutation(t,'message order does not affect score',lambda s:s['messages'].reverse(),1)
acts=expected_actions(t,False)[:1]+[{'op':'delete_rule','id':'R1'}]+expected_actions(t)
check(t,'delete mistaken rule and recreate before applying',run(t,acts),1)

t='G22'
check(t,'correct changes without saving',run(t,expected_actions(t)[:-1]))
check(t,'decisions in a different order',run(t,list(reversed(expected_actions(t)[:-1]))+[{'op':'save'}]),1)
mutation(t,'saved text correct but a revision unresolved',lambda s:s['saved']['revisions'][1].update(status='pending'))
mutation(t,'comment moved to another anchor',lambda s:s['saved']['comments'][0].update(anchor='date'))
mutation(t,'saved title changed',lambda s:s['saved'].update(title='Delivery plan'))
mutation(t,'later unsaved draft does not replace saved delivery',lambda s:apply(t,s,{'op':'decide','id':'R1','decision':'rejected'}),1)
check(t,'incorrect decision can be revised',run(t,[{'op':'decide','id':'R2','decision':'accepted'}]+expected_actions(t)),1)

t='G23'
check(t,'correct working pixels without export',run(t,expected_actions(t)[:-1]))
acts=expected_actions(t);acts[0]['x']=41
check(t,'same size but crop shifted one pixel',run(t,acts))
acts=expected_actions(t);acts[-1]['format']='JPEG'
check(t,'JPEG bytes with PNG filename',run(t,acts))
acts=expected_actions(t);acts[-1]['name']='image.png'
check(t,'correct pixels under wrong filename',run(t,acts))
mutation(t,'original image replaced',lambda s:s.update(source_png=s['working_png']))
def corrupt_pixel(s):
    im=decode_image(s['exports']['badge.png']).convert('RGB');im.putpixel((0,0),(0,0,0));s['exports']['badge.png']=encode_image(im)
mutation(t,'one exported pixel changed',corrupt_pixel)
acts=expected_actions(t)
check(t,'three counterclockwise rotations equal one clockwise',run(t,acts[:1]+[{'op':'rotate','direction':'ccw'}]*3+acts[-1:]),1)
mutation(t,'later working image reset preserves exported delivery',lambda s:apply(t,s,{'op':'reset'}),1)
with tempfile.TemporaryDirectory(prefix='gui-g23-verifier-') as tmp:
    session=TaskSession(t,tmp)
    try:
        session.state=run(t)
        r=session.result();checks.append({'task':t,'name':'state claims export but physical file missing','passed':r['reward']==0 and not r['checks']['export_file_matches_saved_delivery']})
        p=pathlib.Path(tmp)/'exports';p.mkdir();file=p/'badge.png';file.write_bytes(base64.b64decode(session.state['exports']['badge.png']))
        checks.append({'task':t,'name':'physical export and source match saved delivery','passed':session.result()['reward']==1})
        file.write_bytes(b'not a PNG')
        checks.append({'task':t,'name':'physical export differs from state','passed':session.result()['reward']==0})
        file.write_bytes(base64.b64decode(session.state['exports']['badge.png']));(pathlib.Path(tmp)/'source.png').write_bytes(b'changed')
        checks.append({'task':t,'name':'physical original source changed','passed':session.result()['reward']==0})
    finally:session.close()

t='G24'
check(t,'applied preview without saved report',run(t,expected_actions(t)[:1]))
for key,val in [('status','All'),('sort','A to Z'),('group','Person')]:
    acts=expected_actions(t);acts[0]['config'][key]=val
    check(t,'wrong saved '+key,run(t,acts))
mutation(t,'static correct totals with wrong saved query',lambda s:s['reports'][1].update(aggregation='Average'))
mutation(t,'source row edited',lambda s:s['rows'][0].update(Hours=99))
mutation(t,'legacy report removed',lambda s:s['reports'].pop(0))
check(t,'correct and resave mistaken report without duplicate',run(t,expected_actions(t,False)+expected_actions(t)),1)
mutation(t,'unsaved settings retain prior saved report',lambda s:apply(t,s,expected_actions(t,False)[0]),1)

t='G25'
mutation(t,'similarly named wrong recipient',lambda s:s['nodes'][1]['acl'][2].update(principal='noah_ops'))
mutation(t,'recipient Viewer instead of Editor',lambda s:s['nodes'][1]['acl'][2].update(role='Viewer'))
mutation(t,'public link still granted',lambda s:s['nodes'][1]['acl'].append({'principal':'anyone','role':'Viewer'}))
mutation(t,'ACL order does not affect score',lambda s:s['nodes'][1]['acl'].reverse(),1)
mutation(t,'sibling permissions modified',lambda s:s['nodes'][2].update(mode='custom',acl=[]))
mutation(t,'unrequested extra grant',lambda s:s['nodes'][1]['acl'].append({'principal':'noah_ops','role':'Editor'}))
mutation(t,'target renamed',lambda s:s['nodes'][1].update(title='Launch brief copy'))

assert all(c['passed'] for c in checks)
result={'scope':'local verifier boundaries, not model or cross-OS evidence','passed':len(checks),'failed':0,'checks':checks}
(pathlib.Path(__file__).resolve().parent/'LOCAL_CHECKS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'passed':len(checks),'failed':0}))
