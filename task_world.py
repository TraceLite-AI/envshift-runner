"""Synthetic GUI tasks G21–G25; frozen fixtures and independent delivery checks."""
import base64,copy,io,re
from functools import lru_cache
from PIL import Image

TITLES={'G21':'Mail Rules','G22':'Document Review','G23':'Image Workshop','G24':'Report Builder','G25':'Shared Access'}
GUARD='Use only the visible GUI and the provided mouse/keyboard actions. Do not use a terminal, browser console, page source, developer tools, scripts, or direct API requests. All task data is synthetic.'
PROMPTS={
'G21':'In Mail Rules, create one enabled rule named "Approved invoices". It must match ALL of: sender exactly "billing@atlas.example", subject contains "[APPROVED]", and has an attachment. For matching messages, move them to Finance, add the Invoice label, and mark them read. Apply the rule to existing messages as well. The saved rule must also work for future messages. Preserve all other messages and the existing rule.',
'G22':'In Document Review, accept the delivery-date revision to 2026-10-13 and the spelling correction from "recieve" to "receive". Reject the proposed budget increase and owner change. Resolve every revision and save the document. Keep the original title, all other wording, and the existing comment with its original anchor.',
'G23':'In Image Workshop, crop the ORIGINAL image using x=40, y=30, width=180, height=120 (pixels from the top-left). Then rotate the cropped image 90 degrees CLOCKWISE. Export it in PNG format as "badge.png"; the exported image must be 120 pixels wide and 180 pixels high. Preserve the original source image.',
'G24':'In Report Builder, create and save one report named "Weekly effort": a bar chart of the SUM of Hours grouped by Team, including only Posted entries, sorted by total hours descending. The saved report must retain this query so it can recompute when rows change. Preserve all source rows and the existing report. Apply the chart settings before saving.',
'G25':'In Shared Access, change access for "Launch brief" ONLY. Give it its own custom access list: Mina remains Owner, Atlas team remains Viewer, Noah Park (noah@atlas.example) becomes Editor, and Anyone with the link loses access. Save the changes. Preserve the Atlas project folder and Design notes, including their permissions. Do not choose Noah Operations (noah.ops@atlas.example).',
}

def source_pixel(x,y):
    if 145<=x<180 and 38<=y<80 or 132<=x<193 and 65<=y<80:return (244,196,68)
    if 55<=x<105 and 45<=y<110:return (212,74,63)
    if 58<=x<74 and 110<=y<140 or 58<=x<130 and 126<=y<140:return (58,148,99)
    if 170<=x<208 and 103<=y<140:return (236,241,245)
    return (38+(x//40)%2*15,88+(y//30)%2*12,135)

def encode_image(im,fmt='PNG'):
    out=io.BytesIO();im.save(out,format=fmt);return base64.b64encode(out.getvalue()).decode()

def decode_image(value):return Image.open(io.BytesIO(base64.b64decode(value,validate=True)))

@lru_cache(None)
def original_png():
    im=Image.new('RGB',(320,240));im.putdata([source_pixel(x,y) for y in range(240) for x in range(320)])
    return encode_image(im)

def fixture(task):
    if task=='G21':
        specs=[('M1','billing@atlas.example','[APPROVED] September invoice',True),('M2','billing@atlas.example','[PENDING] October invoice',True),('M3','vendor@boreal.example','[APPROVED] Service invoice',True),('M4','billing@atlas.example','[APPROVED] Adjustment',True),('M5','billing@atlas.example','[APPROVED] Reminder',False),('M6','news@atlas.example','Weekly news',False)]
        return {'messages':[{'id':i,'sender':f,'subject':s,'attachment':a,'folder':'Inbox','labels':[],'read':False} for i,f,s,a in specs],
                'rules':[{'id':'R0','name':'Keep alerts','enabled':False,'match':'all','sender':'ops@atlas.example','subject':'Alert','attachment':False,'folder':'Inbox','label':'Alert','mark_read':False}]}
    if task=='G22':
        blocks=[{'id':'date','text':'Delivery date: 2026-10-06.'},{'id':'budget','text':'Budget: $24,000.'},{'id':'owner','text':'Owner: Mina.'},{'id':'copy','text':'Please recieve the signed plan.'}]
        after=['Delivery date: 2026-10-13.','Budget: $42,000.','Owner: Noah.','Please receive the signed plan.']
        return {'title':'Atlas delivery plan','blocks':blocks,'comments':[{'id':'C1','anchor':'budget','text':'Finance has approved the original budget.'}],
                'revisions':[{'id':'R'+str(i+1),'block':b['id'],'before':b['text'],'after':a,'status':'pending'} for i,(b,a) in enumerate(zip(blocks,after))],'saved':None}
    if task=='G23':return {'title':'Badge source','source_png':original_png(),'working_png':original_png(),'exports':{}}
    if task=='G24':
        specs=[('Engineering','Ari',4,'Posted'),('Design','Mina',3,'Posted'),('Support','Lee',7,'Posted'),('Engineering','Sam',6,'Posted'),('Design','Noah',5,'Posted'),('Support','Ari',2,'Posted'),('Engineering','Lee',2,'Posted'),('Engineering','Sam',90,'Cancelled'),('Design','Mina',40,'Cancelled')]
        return {'rows':[{'id':'T'+str(i+1),'Team':t,'Person':p,'Hours':h,'Status':s} for i,(t,p,h,s) in enumerate(specs)],'reports':[{'id':'legacy','title':'Daily incidents','kind':'legacy','note':'Keep the saved report intact.'}],'draft':{'title':'Untitled report','kind':'Line','group':'Person','value':'Hours','aggregation':'Average','status':'All','sort':'A to Z'},'draft_report_id':None}
    if task=='G25':return {'nodes':[{'id':'project','title':'Atlas project','parent':None,'mode':'custom','acl':[{'principal':'mina','role':'Owner'},{'principal':'team','role':'Viewer'},{'principal':'anyone','role':'Viewer'}]},
                                      {'id':'launch','title':'Launch brief','parent':'project','mode':'inherit','acl':[]},{'id':'design','title':'Design notes','parent':'project','mode':'inherit','acl':[]}],
                          'people':[{'id':'mina','name':'Mina','email':'mina@atlas.example'},{'id':'team','name':'Atlas team','email':''},{'id':'anyone','name':'Anyone with the link','email':''},{'id':'noah','name':'Noah Park','email':'noah@atlas.example'},{'id':'noah_ops','name':'Noah Operations','email':'noah.ops@atlas.example'}]}
    raise ValueError('Unknown task')

def rule_matches(r,m):
    tests=[m['sender']==r['sender'],r['subject'] in m['subject']]
    if r['attachment']:tests.append(m['attachment'])
    return bool(r['enabled'] and (all(tests) if r['match']=='all' else any(tests)))

def query(cfg,rows):
    groups={}
    for row in rows:
        if cfg['status']!='All' and row['Status']!=cfg['status']:continue
        groups.setdefault(row[cfg['group']],[]).append(row[cfg['value']])
    result=[{'label':k,'value':sum(v) if cfg['aggregation']=='Sum' else sum(v)/len(v)} for k,v in groups.items()]
    return sorted(result,key=(lambda x:(-x['value'],x['label'])) if cfg['sort']=='Descending total' else lambda x:x['label'])

def effective_acl(state,node):
    n=next(n for n in state['nodes'] if n['id']==node)
    return copy.deepcopy(n['acl'] if n['mode']=='custom' else effective_acl(state,n['parent']))

def apply(task,state,action):
    fresh=copy.deepcopy(state);_apply(task,fresh,action);state.clear();state.update(fresh)

def _apply(task,s,a):
    op=a['op']
    if task=='G21':
        if op=='create_rule':
            r=copy.deepcopy(a['rule']);assert set(r)=={'name','enabled','match','sender','subject','attachment','folder','label','mark_read'}
            assert r['match'] in ['all','any'] and r['folder'] in ['Inbox','Finance','Archive'] and r['label'] in ['Invoice','Alert','Follow up']
            assert all(type(r[k]) is bool for k in ['enabled','attachment','mark_read']) and all(isinstance(r[k],str) for k in ['name','sender','subject'])
            r['id']='R'+str(1+max([int(x['id'][1:]) for x in s['rules']]+[0]));s['rules'].append(r)
        elif op=='delete_rule':
            r=next(r for r in s['rules'] if r['id']==a['id']);s['rules'].remove(r)
        elif op=='apply_rule':
            r=next(r for r in s['rules'] if r['id']==a['id'])
            for m in s['messages']:
                if rule_matches(r,m):
                    m['folder']=r['folder'];m['labels']=sorted(set(m['labels']+[r['label']]))
                    if r['mark_read']:m['read']=True
        else:raise ValueError('Unknown mail action')
    elif task=='G22':
        if op=='decide':
            assert a['decision'] in ['accepted','rejected'];r=next(x for x in s['revisions'] if x['id']==a['id']);r['status']=a['decision']
            next(b for b in s['blocks'] if b['id']==r['block'])['text']=r['after'] if a['decision']=='accepted' else r['before']
        elif op=='save':s['saved']=copy.deepcopy({k:s[k] for k in ['title','blocks','comments','revisions']})
        else:raise ValueError('Unknown review action')
    elif task=='G23':
        im=decode_image(s['working_png']).convert('RGB')
        if op=='crop':
            x,y,w,h=[a[k] for k in ['x','y','width','height']];assert all(type(v) is int for v in [x,y,w,h])
            assert x>=0 and y>=0 and w>0 and h>0 and x+w<=im.width and y+h<=im.height
            s['working_png']=encode_image(im.crop((x,y,x+w,y+h)))
        elif op=='rotate':
            assert a['direction'] in ['cw','ccw'];s['working_png']=encode_image(im.transpose(Image.Transpose.ROTATE_270 if a['direction']=='cw' else Image.Transpose.ROTATE_90))
        elif op=='reset':s['working_png']=s['source_png']
        elif op=='export':
            assert a['format'] in ['PNG','JPEG'] and re.fullmatch(r'[A-Za-z0-9_-]+\.(?:png|jpg|jpeg)',a['name'])
            s['exports'][a['name']]=encode_image(im,a['format'])
        else:raise ValueError('Unknown image action')
    elif task=='G24':
        if op=='configure':
            c=copy.deepcopy(a['config']);assert set(c)=={'title','kind','group','value','aggregation','status','sort'}
            assert c['kind'] in ['Bar','Line'] and c['group'] in ['Team','Person'] and c['value']=='Hours' and c['aggregation'] in ['Sum','Average'] and c['status'] in ['All','Posted','Cancelled'] and c['sort'] in ['Descending total','A to Z'] and isinstance(c['title'],str)
            s['draft']=c
        elif op=='save':
            c=copy.deepcopy(s['draft']);rid=s['draft_report_id'] or 'report-'+str(len(s['reports']));s['draft_report_id']=rid
            r={'id':rid,**c,'series':query(c,s['rows'])};s['reports']=[x for x in s['reports'] if x['id']!=rid]+[r]
        else:raise ValueError('Unknown report action')
    elif task=='G25':
        assert op=='set_access';n=next(n for n in s['nodes'] if n['id']==a['node']);assert a['mode'] in ['custom','inherit'] and (a['mode']=='custom' or n['parent'])
        acl=a['acl'];assert isinstance(acl,list) and len({x['principal'] for x in acl})==len(acl)
        for x in acl:assert set(x)=={'principal','role'} and x['principal'] in {p['id'] for p in s['people']} and x['role'] in ['Owner','Editor','Viewer']
        assert a['mode']=='custom' or not acl;n['mode']=a['mode'];n['acl']=copy.deepcopy(acl)
    else:raise ValueError('Unknown task')

def expected_actions(task,good=True):
    if task=='G21':return [{'op':'create_rule','rule':{'name':'Approved invoices','enabled':True,'match':'all' if good else 'any','sender':'billing@atlas.example','subject':'[APPROVED]','attachment':True,'folder':'Finance','label':'Invoice','mark_read':True}},{'op':'apply_rule','id':'R1'}]
    if task=='G22':return [{'op':'decide','id':'R'+str(i+1),'decision':('accepted' if d else 'rejected')} for i,d in enumerate([True,not good,False,True])]+[{'op':'save'}]
    if task=='G23':return [{'op':'crop','x':40,'y':30,'width':180,'height':120},{'op':'rotate','direction':'cw' if good else 'ccw'},{'op':'export','format':'PNG','name':'badge.png'}]
    if task=='G24':return [{'op':'configure','config':{'title':'Weekly effort','kind':'Bar','group':'Team','value':'Hours','aggregation':'Sum' if good else 'Average','status':'Posted','sort':'Descending total'}},{'op':'save'}]
    if task=='G25':return [{'op':'set_access','node':'launch' if good else 'project','mode':'custom','acl':[{'principal':'mina','role':'Owner'},{'principal':'team','role':'Viewer'},{'principal':'noah','role':'Editor'}]}]

def grade(task,s):
    original=fixture(task);c={}
    try:
        if task=='G21':
            new=[r for r in s['rules'] if r.get('id')!='R0'];r=new[0] if len(new)==1 else {}
            c['saved_enabled_rule']=len(new)==1 and r.get('name')=='Approved invoices' and r.get('enabled') is True
            c['saved_predicate_fields']=all(r.get(k)==v for k,v in {'match':'all','sender':'billing@atlas.example','subject':'[APPROVED]','attachment':True}.items())
            c['prior_rule_preserved']=[x for x in s['rules'] if x.get('id')=='R0']==original['rules']
            tests=[{'sender':sender,'subject':subject,'attachment':attach} for sender in ['billing@atlas.example','other@atlas.example'] for subject in ['[APPROVED] New invoice','[PENDING] New invoice'] for attach in [False,True]]
            wanted=lambda m:m['sender']=='billing@atlas.example' and '[APPROVED]' in m['subject'] and m['attachment']
            c['future_rule_predicate']=bool(r) and all(rule_matches(r,m)==wanted(m) for m in tests)
            c['rule_actions']=all(r.get(k)==v for k,v in {'folder':'Finance','label':'Invoice','mark_read':True}.items())
            wanted_msgs=copy.deepcopy(original['messages'])
            for m in wanted_msgs:
                if wanted(m):m.update(folder='Finance',labels=['Invoice'],read=True)
            c['existing_matching_and_other_messages']=sorted(s['messages'],key=lambda m:m['id'])==wanted_msgs
        elif task=='G22':
            saved=s.get('saved') or {};c['saved_document']=bool(saved)
            want_blocks=copy.deepcopy(original['blocks']);want_blocks[0]['text']='Delivery date: 2026-10-13.';want_blocks[3]['text']='Please receive the signed plan.'
            c['accepted_text_and_rejected_changes']=saved.get('blocks')==want_blocks
            want_rev=copy.deepcopy(original['revisions'])
            for r,d in zip(want_rev,['accepted','rejected','rejected','accepted']):r['status']=d
            c['all_revisions_correctly_resolved']=sorted(saved.get('revisions',[]),key=lambda r:r['id'])==want_rev
            c['title_comments_and_anchor_preserved']=saved.get('title')==original['title'] and saved.get('comments')==original['comments']
        elif task=='G23':
            data=s.get('exports',{}).get('badge.png');c['exported_badge_png']=bool(data)
            im=decode_image(data) if data else None;c['png_format_and_dimensions']=im is not None and im.format=='PNG' and im.size==(120,180)
            # Invert the desired geometric mapping directly; do not call the crop/rotate implementation.
            want=[source_pixel(40+y,30+119-x) for y in range(180) for x in range(120)]
            c['crop_and_clockwise_pixels']=bool(c['png_format_and_dimensions']) and list(im.convert('RGB').getdata())==want
            c['original_source_preserved']=s.get('source_png')==original['source_png'] and s.get('title')==original['title']
        elif task=='G24':
            new=[r for r in s['reports'] if r.get('id')!='legacy'];r=new[0] if len(new)==1 else {};c['saved_one_report']=len(new)==1
            c['bar_title']=r.get('title')=='Weekly effort' and r.get('kind')=='Bar'
            c['current_totals_order']=r.get('series')==[{'label':'Engineering','value':12},{'label':'Support','value':9},{'label':'Design','value':8}]
            hold=copy.deepcopy(original['rows']);hold[0]['Hours']=11;hold.append({'id':'new','Team':'Finance','Person':'Zoe','Hours':25,'Status':'Posted'})
            want=[{'label':'Finance','value':25},{'label':'Engineering','value':19},{'label':'Support','value':9},{'label':'Design','value':8}]
            c['live_saved_query']=bool(r) and query(r,hold)==want
            c['source_rows_unchanged']=s['rows']==original['rows'];c['old_report_preserved']=[x for x in s['reports'] if x.get('id')=='legacy']==original['reports']
        elif task=='G25':
            n=next(n for n in s['nodes'] if n['id']=='launch');c['target_custom_access']=n['mode']=='custom'
            c['target_effective_acl']=sorted(effective_acl(s,'launch'),key=lambda x:x['principal'])==[{'principal':'mina','role':'Owner'},{'principal':'noah','role':'Editor'},{'principal':'team','role':'Viewer'}]
            c['parent_and_sibling_preserved']=sorted([n for n in s['nodes'] if n['id']!='launch'],key=lambda n:n['id'])==sorted([n for n in original['nodes'] if n['id']!='launch'],key=lambda n:n['id'])
            c['target_identity_and_people_preserved']=n['title']=='Launch brief' and n['parent']=='project' and s['people']==original['people'] and len(s['nodes'])==3
    except (KeyError,ValueError,TypeError,StopIteration,AssertionError,OSError,RecursionError):c['readable_delivery']=False
    return {'reward':int(bool(c) and all(c.values())),'checks':c}
