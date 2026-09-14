"""Original synthetic GUI tasks; final-state graders accept alternative action sequences."""
import ast,copy,math,re
from datetime import datetime,timedelta

TITLES={'G17':'Ledger Grid','G18':'Team Calendar','G19':'Slide Studio','G20':'Shared Files'}
GUARD='Use the visible application and ordinary mouse/keyboard actions. Do not use a terminal, developer tools, scripts, APIs, or edit the task/evaluator files. All data is synthetic and local to this task.'
PROMPTS={
'G17':'In Ledger Grid, complete and save the September quote. In D2:D5 enter live spreadsheet formulas for each row: Quantity times Unit price times (1 minus the Discount in H2). In D6 enter a live total of D2:D5. The results must recalculate correctly when quantities, prices, or H2 change; fixed numbers are not sufficient. Format D2:D6 as Currency and save the workbook. Preserve all other cells and formats. The grid supports arithmetic, cell references (including $ absolute references), SUM, and Fill down.',
'G18':'In Team Calendar, change only the Atlas review occurrence originally on 2026-09-23. Move it to 2026-09-24, from 14:00 to 14:45, change its location to Room C, and add Noah without removing Lee or Sam. Keep its title and all other occurrences and meetings unchanged. Save the change for this event only. All times shown are the same local calendar time; no timezone conversion is needed.',
'G19':'Prepare the Atlas update deck in Slide Studio. Put the slides in this order: Introduction, Findings, Plan, Risks, Next steps, Appendix. Hide Appendix from the presentation without deleting it. Set the speaker notes of Next steps to exactly: Owner: Mina; review: 2026-09-25. Preserve every slide title and body, all other notes, and the visibility of the other slides. Save the deck. You may drag slides or use Move up / Move down.',
'G20':'In Shared Files, create Shared/Handoffs/Atlas Release. For each of Design, QA, and Launch under Shared/Atlas, find the most recently modified file whose review status is Approved. Copy those three files into the new folder, named Design.md, QA.md, and Launch.md respectively. Newer Draft versions must not be delivered. Preserve source file contents and metadata, keep all original files in place, and leave other folders and files unchanged. File previews show review status and contents.'}
DEST='Shared/Handoffs/Atlas Release'

def fixture(task):
    if task=='G17':
        cells={'A1':'Item','B1':'Quantity','C1':'Unit price','D1':'Net','A6':'Total','H1':'Discount','H2':'0.10'}
        for i,(name,q,price) in enumerate([('Keyboard',2,40),('Dock',1,120),('Headset',4,30),('Cable',10,10)],2):cells.update({f'A{i}':name,f'B{i}':str(q),f'C{i}':str(price),f'D{i}':''})
        cells['D6']='';formats={k:'General' for k in cells}
        return {'cells':cells,'formats':formats,'saved':None,'title':'September quote'}
    if task=='G18':
        events=[{'id':'AR-'+d,'series':'atlas-review','original_date':d,'date':d,'start':'10:00','end':'10:30','title':'Atlas review','location':'Room A','attendees':['Lee','Sam']} for d in ['2026-09-16','2026-09-23','2026-09-30','2026-10-07']]
        events.append({'id':'B-24','series':None,'original_date':'2026-09-24','date':'2026-09-24','start':'11:00','end':'11:30','title':'Boreal sync','location':'Room B','attendees':['Mina','Noah']})
        return {'events':events,'calendar':'Product team'}
    if task=='G19':
        data=[('intro','Introduction','Atlas update for the September review.'),('risks','Risks','Vendor lead time remains the main risk.'),('appendix','Appendix','Supporting material for questions.'),('plan','Plan','Pilot, measure, then expand.'),('findings','Findings','The pilot reduced repeat work.'),('next','Next steps','Confirm owners and schedule the review.')]
        return {'slides':[{'id':i,'title':t,'body':b,'notes':'','hidden':False} for i,t,b in data],'saved':None,'title':'Atlas update'}
    if task=='G20':
        files=[]
        specs=[('D1','Design',1,'Approved','2026-09-03'),('D2','Design',2,'Approved','2026-09-11'),('D3','Design',3,'Draft','2026-09-14'),('Q1','QA',1,'Approved','2026-09-06'),('Q2','QA',2,'Approved','2026-09-12'),('Q3','QA',3,'Draft','2026-09-15'),('L1','Launch',1,'Approved','2026-09-13'),('L2','Launch',2,'Draft','2026-09-14')]
        for i,k,v,status,date in specs:files.append({'id':i,'path':'Shared/Atlas/'+k,'name':k+' v'+str(v)+'.md','project':'Atlas','kind':k,'version':v,'status':status,'modified':date,'content':k+' release brief, revision '+str(v)+'. Review: '+status+'. Unique document '+i+'.'})
        files.append({'id':'B1','path':'Shared/Boreal','name':'Design v4.md','project':'Boreal','kind':'Design','version':4,'status':'Approved','modified':'2026-09-15','content':'Boreal design; not an Atlas deliverable.'})
        files.append({'id':'OLD','path':'Shared/Handoffs/Existing','name':'readme.md','project':'Archive','kind':'Readme','version':1,'status':'Approved','modified':'2026-09-01','content':'Keep this earlier handoff intact.'})
        return {'folders':['Shared','Shared/Atlas','Shared/Atlas/Design','Shared/Atlas/QA','Shared/Atlas/Launch','Shared/Boreal','Shared/Handoffs','Shared/Handoffs/Existing'],'files':files}
    raise ValueError(task)

CELL=re.compile(r'\$?([A-H])\$?([1-6])\b',re.I)
def calc(cells,addr,seen=None):
    seen=set() if seen is None else set(seen)
    if addr in seen:raise ValueError('Circular formula')
    seen.add(addr);raw=str(cells.get(addr,''))
    if not raw:return 0.0
    if not raw.startswith('='):return float(raw)
    expr=re.sub(r'\s+','',raw[1:].upper())
    def sumrange(m):
        ca,ra,cb,rb=m.groups();assert ca==cb and int(ra)<=int(rb)
        return '('+'+'.join(str(calc(cells,ca+str(i),seen)) for i in range(int(ra),int(rb)+1))+')'
    expr=re.sub(r'SUM\(\$?([A-H])\$?([1-6]):\$?([A-H])\$?([1-6])\)',sumrange,expr)
    expr=CELL.sub(lambda m:'('+str(calc(cells,m[1].upper()+m[2],seen))+')',expr)
    tree=ast.parse(expr,mode='eval')
    def ev(n):
        if isinstance(n,ast.Expression):return ev(n.body)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):return n.value
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):return ev(n.operand)*(1 if isinstance(n.op,ast.UAdd) else -1)
        if isinstance(n,ast.BinOp) and isinstance(n.op,(ast.Add,ast.Sub,ast.Mult,ast.Div)):
            a,b=ev(n.left),ev(n.right)
            if isinstance(n.op,ast.Add):return a+b
            if isinstance(n.op,ast.Sub):return a-b
            if isinstance(n.op,ast.Mult):return a*b
            return a/b
        raise ValueError('Unsupported formula')
    result=float(ev(tree));assert math.isfinite(result);return result

def shifted(formula,offset):
    def sub(m):
        text=m[0];return text if re.search(r'\$[1-6]$',text) else re.sub(r'[1-6]$',str(int(m[2])+offset),text)
    return CELL.sub(sub,formula)

def apply(task,state,action):
    """Validate on a copy so a rejected action never partially mutates state."""
    s=copy.deepcopy(state);a=action;op=a['op']
    if task=='G17':
        if op=='cell':
            assert a['address'] in s['cells'];assert len(a['value'])<=120
            s['cells'][a['address']]=str(a['value'])
        elif op=='fill':
            m=re.fullmatch(r'([A-H])([1-6]):\1([1-6])',a['range'].upper());assert m
            c,r1,r2=m.groups();assert int(r1)<int(r2);raw=s['cells'][c+r1]
            for i in range(int(r1)+1,int(r2)+1):s['cells'][c+str(i)]=shifted(raw,i-int(r1)) if raw.startswith('=') else raw
        elif op=='format':
            assert a['format'] in ['General','Currency'];m=re.fullmatch(r'([A-H])([1-6])(?::\1([1-6]))?',a['range'].upper());assert m
            c,r1,r2=m.groups()
            for i in range(int(r1),int(r2 or r1)+1):assert c+str(i) in s['cells'];s['formats'][c+str(i)]=a['format']
        elif op=='save':s['saved']={'cells':copy.deepcopy(s['cells']),'formats':copy.deepcopy(s['formats'])}
        else:raise ValueError('Unknown action')
    elif task=='G18':
        assert op=='edit';target=next(e for e in s['events'] if e['id']==a['id']);assert a['scope'] in ['this','following','series']
        changes=a['changes'];assert set(changes)=={'date','start','end','location','attendees'}
        dt=datetime.strptime(changes['date'],'%Y-%m-%d');assert datetime.strptime(changes['start'],'%H:%M')<datetime.strptime(changes['end'],'%H:%M')
        assert changes['location'] in ['Room A','Room B','Room C'];assert set(changes['attendees'])<=set(['Lee','Sam','Noah','Mina']) and len(set(changes['attendees']))==len(changes['attendees'])
        delta=dt-datetime.strptime(target['date'],'%Y-%m-%d');origin=target['original_date']
        for event in s['events']:
            matched=event['id']==a['id'] or (a['scope']!='this' and target['series'] and event['series']==target['series'] and (a['scope']=='series' or event['original_date']>=origin))
            if matched:
                date=(datetime.strptime(event['date'],'%Y-%m-%d')+delta).strftime('%Y-%m-%d');event.update(copy.deepcopy(changes));event['date']=date;event['attendees']=sorted(event['attendees'])
    elif task=='G19':
        if op=='move':
            index=next(i for i,x in enumerate(s['slides']) if x['id']==a['id']);target=int(a['index']);assert 0<=target<len(s['slides']);slide=s['slides'].pop(index);s['slides'].insert(target,slide)
        elif op in ['notes','hidden']:
            slide=next(x for x in s['slides'] if x['id']==a['id']);value=a['value'];assert isinstance(value,str) if op=='notes' else type(value)==bool;slide[op]=value
        elif op=='save':s['saved']=copy.deepcopy(s['slides'])
        else:raise ValueError('Unknown action')
    elif task=='G20':
        if op=='mkdir':
            path=a['path'];parent,_,name=path.rpartition('/');assert parent in s['folders'] and name.strip() and path not in s['folders'] and '/' not in name and name not in ['.','..'];s['folders'].append(path)
        elif op in ['copy','move']:
            src=next(x for x in s['files'] if x['id']==a['id']);assert a['destination'] in s['folders'];assert a['name'].strip() and '/' not in a['name']
            assert not any(x['path']==a['destination'] and x['name']==a['name'] for x in s['files'])
            if op=='copy':
                obj=copy.deepcopy(src);obj['id']='COPY-'+str(len([x for x in s['files'] if x['id'].startswith('COPY-')])+1);obj['source_id']=src.get('source_id',src['id']);s['files'].append(obj)
            else:obj=src
            obj.update(path=a['destination'],name=a['name'])
        else:raise ValueError('Unknown action')
    else:raise ValueError(task)
    state.clear();state.update(s)

def expected_actions(task,good=True):
    if task=='G17':
        actions=[{'op':'cell','address':f'D{i}','value':f'=B{i}*C{i}*(1-$H$2)' if good else str(v)} for i,v in zip(range(2,6),[72,108,108,90])]
        return actions+[{'op':'cell','address':'D6','value':'=SUM(D2:D5)'},{'op':'format','range':'D2:D6','format':'Currency'},{'op':'save'}]
    if task=='G18':return [{'op':'edit','id':'AR-2026-09-23','scope':'this' if good else 'series','changes':{'date':'2026-09-24','start':'14:00','end':'14:45','location':'Room C','attendees':['Lee','Sam','Noah']}}]
    if task=='G19':
        order=[x['id'] for x in fixture(task)['slides']];actions=[]
        for pid,target in [('findings',1),('plan',2),('next',4 if good else 3)]:
            while order.index(pid)!=target:
                i=order.index(pid);j=i+(1 if target>i else -1);actions.append({'op':'move','id':pid,'index':j});order.insert(j,order.pop(i))
        return actions+[{'op':'hidden','id':'appendix','value':True},{'op':'notes','id':'next','value':'Owner: Mina; review: 2026-09-25.'},{'op':'save'}]
    return [{'op':'mkdir','path':DEST}]+[{'op':'copy','id':i,'destination':DEST,'name':n+'.md'} for i,n in [(('D2' if good else 'D3'),'Design'),('Q2','QA'),('L1','Launch')]]

def grade(task,state):
    base=fixture(task)
    if task=='G17':
        saved=state.get('saved') or {};cells=saved.get('cells',{});formats=saved.get('formats',{});targets=[f'D{i}' for i in range(2,7)]
        def correct(data):
            try:
                values=[float(data[f'B{i}'])*float(data[f'C{i}'])*(1-float(data['H2'])) for i in range(2,6)]
                return all(math.isclose(calc(data,f'D{i}'),v,abs_tol=1e-7) for i,v in zip(range(2,7),values+[sum(values)]))
            except (ValueError,TypeError,AssertionError,KeyError,ZeroDivisionError,SyntaxError,RecursionError):return False
        dynamic=all(str(cells.get(k,'')).startswith('=') for k in targets)
        for discount,qty,price in [('0.25','7','23'),('0.07','3','51')]:
            varied=copy.deepcopy(cells);varied['H2']=discount
            for i in range(2,6):varied[f'B{i}']=str(int(qty)+i);varied[f'C{i}']=str(int(price)+i*2)
            dynamic=dynamic and correct(varied)
        checks={'saved_workbook':bool(saved),'current_values_correct':correct(cells),'live_formulas_recalculate':dynamic,'currency_format':all(formats.get(k)=='Currency' for k in targets),'other_cells_and_formats_preserved':set(cells)==set(base['cells']) and set(formats)==set(base['formats']) and all(cells[k]==v for k,v in base['cells'].items() if k not in targets) and all(formats[k]==v for k,v in base['formats'].items() if k not in targets),'title_preserved':state.get('title')==base['title']}
    elif task=='G18':
        expected=copy.deepcopy(base);apply(task,expected,expected_actions(task)[0]);tid='AR-2026-09-23';actual={e['id']:{**e,'attendees':sorted(e['attendees'])} for e in state['events']};wanted={e['id']:{**e,'attendees':sorted(e['attendees'])} for e in expected['events']}
        checks={'target_occurrence_correct':actual.get(tid)==wanted[tid],'other_events_unchanged':all(actual.get(i)==e for i,e in wanted.items() if i!=tid),'no_added_or_deleted_events':len(state['events'])==len(wanted) and set(actual)==set(wanted),'calendar_preserved':state['calendar']==base['calendar']}
    elif task=='G19':
        slides=state.get('saved') or [];byid={x['id']:x for x in slides};original={x['id']:x for x in base['slides']}
        checks={'saved_deck':state.get('saved') is not None,'correct_order':[x['id'] for x in slides]==['intro','findings','plan','risks','next','appendix'],'appendix_hidden_only':all(byid.get(i,{}).get('hidden')==(i=='appendix') for i in original),'next_steps_notes':byid.get('next',{}).get('notes')=='Owner: Mina; review: 2026-09-25.','content_and_other_notes_preserved':len(slides)==6 and set(byid)==set(original) and all(byid[i]['title']==v['title'] and byid[i]['body']==v['body'] and (i=='next' or byid[i]['notes']==v['notes']) for i,v in original.items()),'deck_title_preserved':state['title']==base['title']}
    else:
        originals={x['id']:x for x in base['files']};actual={x['id']:x for x in state['files']};new=[x for x in state['files'] if x['id'] not in originals]
        wanted=[]
        for kind in ['Design','QA','Launch']:
            src=max((x for x in base['files'] if x['project']=='Atlas' and x['kind']==kind and x['status']=='Approved'),key=lambda x:x['modified'])
            wanted.append({**src,'path':DEST,'name':kind+'.md','source_id':src['id']})
        clean=lambda x:{k:v for k,v in x.items() if k!='id'}
        checks={'handoff_folder_created':DEST in state['folders'],'exact_approved_copies':len(new)==3 and sorted((clean(x) for x in new),key=lambda x:x['name'])==sorted((clean(x) for x in wanted),key=lambda x:x['name']),'original_files_unchanged':len(actual)==len(state['files']) and all(actual.get(i)==x for i,x in originals.items()),'other_folders_unchanged':len(state['folders'])==len(base['folders'])+1 and set(state['folders'])==set(base['folders'])|{DEST}}
    return {'reward':int(all(checks.values())),'checks':checks}
