import copy,json,pathlib
from task_world import fixture,apply,grade,expected_actions,calc,DEST
checks=[]
def check(name,test):
    assert test,name;checks.append(name)
def solved(task,good=True):
    s=fixture(task)
    for a in expected_actions(task,good):apply(task,s,a)
    return s
for t in ['G17','G18','G19','G20']:
    check(t+' initially incomplete',grade(t,fixture(t))['reward']==0)
    check(t+' complete oracle accepted',grade(t,solved(t))['reward']==1)
    check(t+' materialized wrong output rejected',grade(t,solved(t,False))['reward']==0)
s=fixture('G17')
for a in [{'op':'cell','address':'D2','value':'= C2 * B2 * (1 - $H$2)'},{'op':'fill','range':'D2:D5'},{'op':'cell','address':'D6','value':'=D5+D3+D4+D2'},{'op':'format','range':'D2:D6','format':'Currency'},{'op':'save'}]:apply('G17',s,a)
check('G17 equivalent formula and fill-down accepted',grade('G17',s)['reward']==1)
check('G17 current totals independently known',all(abs(calc(s['cells'],a)-b)<1e-8 for a,b in zip(['D2','D3','D4','D5','D6'],[72,108,108,90,378])))
for mutation in ['format','unsaved','preservation','circular','discount-dependency']:
    s=solved('G17')
    if mutation=='format':s['saved']['formats']['D4']='General'
    elif mutation=='unsaved':s['saved']=None
    elif mutation=='preservation':s['saved']['cells']['A3']='Replacement'
    elif mutation=='circular':s['saved']['cells']['D3']='=D3+1'
    else:s['saved']['cells']['D2']='=B2*C2*0.9'
    check('G17 rejects '+mutation,grade('G17',s)['reward']==0)
s=solved('G18');s['events'].reverse()
for e in s['events']:e['attendees'].reverse()
check('G18 event and attendee storage order irrelevant',grade('G18',s)['reward']==1)
for mutation in ['following','missing-attendee','wrong-time','other-event','duplicate-record']:
    s=solved('G18')
    if mutation=='following':s=fixture('G18');a=expected_actions('G18')[0];a['scope']='following';apply('G18',s,a)
    elif mutation=='missing-attendee':s['events'][1]['attendees'].remove('Noah')
    elif mutation=='wrong-time':s['events'][1]['end']='14:30'
    elif mutation=='other-event':s['events'][-1]['location']='Room C'
    else:s['events'].append(copy.deepcopy(s['events'][1]))
    check('G18 rejects '+mutation,grade('G18',s)['reward']==0)
s=fixture('G19')
for i,pid in enumerate(['intro','findings','plan','risks','next','appendix']):apply('G19',s,{'op':'move','id':pid,'index':i})
for a in [{'op':'notes','id':'next','value':'Owner: Mina; review: 2026-09-25.'},{'op':'hidden','id':'appendix','value':True},{'op':'save'}]:apply('G19',s,a)
check('G19 alternative reorder path accepted',grade('G19',s)['reward']==1)
for mutation in ['missing-save','deleted-appendix','changed-body','other-notes','other-hidden']:
    s=solved('G19')
    if mutation=='missing-save':s['saved']=None
    elif mutation=='deleted-appendix':s['saved'].pop()
    elif mutation=='changed-body':s['saved'][0]['body']='changed'
    elif mutation=='other-notes':s['saved'][0]['notes']='changed'
    else:s['saved'][0]['hidden']=True
    check('G19 rejects '+mutation,grade('G19',s)['reward']==0)
s=fixture('G20');actions=expected_actions('G20');apply('G20',s,actions[0])
for a in reversed(actions[1:]):apply('G20',s,a)
check('G20 copy order and allocated IDs irrelevant',grade('G20',s)['reward']==1)
for mutation in ['move','content','extra-file','other-folder','rename-original']:
    s=solved('G20')
    if mutation=='move':s['files']=[x for x in s['files'] if x['id']!='D2']
    elif mutation=='content':s['files'][-1]['content']='changed'
    elif mutation=='extra-file':apply('G20',s,{'op':'copy','id':'D1','destination':DEST,'name':'extra.md'})
    elif mutation=='other-folder':s['folders'].append('Shared/Unrequested')
    else:s['files'][0]['name']='renamed.md'
    check('G20 rejects '+mutation,grade('G20',s)['reward']==0)
s=fixture('G20');before=copy.deepcopy(s)
try:apply('G20',s,{'op':'copy','id':'D2','destination':'Missing','name':'Design.md'})
except AssertionError:pass
check('invalid operation is atomic',s==before)
pathlib.Path(__file__).with_name('LOCAL_CHECKS.json').write_text(json.dumps({'passed':len(checks),'checks':checks},indent=2)+'\n')
print(len(checks),'verifier checks passed')
