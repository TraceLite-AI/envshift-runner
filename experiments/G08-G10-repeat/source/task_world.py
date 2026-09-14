"""Synthetic business fixtures, state transitions, and independent final-state checks."""
import copy, csv, io
GUARD = 'Use the visible application and browser UI only. Do not open a terminal or DevTools, execute code, or browse other websites.'
PROMPTS = {
'G05': 'Reconcile invoice INV-044. Open Purchase orders in its new browser tab and find the matching PO. Calculate total as quantity times unit price plus freight minus discount. Enter that total and the PO reference on INV-044, then mark it reconciled. Leave every other invoice unchanged.',
'G06': 'Assign all Open, High priority tickets for customer Cedar to Mina, set status Queued, and add the Reviewed tag. Include all matching tickets across pages. Leave every other ticket unchanged.',
'G07': 'Export all and only September 2026 Approved expenses from the Ops department, across all pages, as approved-expenses.csv in Downloads. Keep the original expense records unchanged.',
'G08': 'Update the live customer profile for Sam Lee at sam.lee@cedar.example using the latest confirmed address and contact preference in the activity notes. Publish the changes, not just a draft. Leave the other customer unchanged.',
'G09': 'Move only card PROJ-218 from Ready to Review by dragging it. Preserve its assignee and due date, and leave every other card unchanged.',
'G10': 'Read the current approval policy in the scrollable policy dialog, acknowledge it, then submit the appropriate approval route and reason code for case REQ-731. Use the policy applicable to this case.'}
TITLES = dict(zip(PROMPTS, ['Invoice reconciliation','Bulk ticket assignment','Expense export','Customer publication','Project board','Policy approval']))

def fixture(task):
    if task=='G05': return {'invoices':[
        {'id':'INV-040','supplier':'Nori','po':'PO-6040','total':'320.00','reference':'PO-6040','status':'Reconciled'},
        {'id':'INV-044','supplier':'Nori','po':'PO-6041','total':'480.00','reference':'','status':'Draft'}],
        'orders':[{'id':'PO-6014','supplier':'Nori','quantity':7,'unit':'84.50','freight':'18.20','discount':'5.00'},
                  {'id':'PO-6040','supplier':'Nori','quantity':4,'unit':'80.00','freight':'0.00','discount':'0.00'},
                  {'id':'PO-6041','supplier':'Nori','quantity':7,'unit':'85.40','freight':'18.20','discount':'5.00'}]}
    if task=='G06':
        specs=[('T-290','Maple','Closed','High'),('T-301','Cedar','Open','High'),('T-302','Cedar','Open','Low'),('T-303','Maple','Open','High'),('T-304','Cedar','Open','High'),('T-305','Cedar','Closed','High'),('T-306','Cedar','Open','High'),('T-307','Cedar','Open','Normal'),('T-308','Cedar','Open','High')]
        return {'tickets':[dict(zip(['id','customer','status','priority'],s),owner='Leo',tags=[]) for s in specs]}
    if task=='G07':
        rows=[]
        for i in range(1,13):
            target=i in [1,7,9,12]
            rows.append({'id':f'E-{100+i}','month':'2026-09' if target or i%2 else '2026-08','status':'Approved' if target or i%3 else 'Pending','department':'Ops' if target else 'Sales','amount':f'{50+i*13}.00'})
        return {'expenses':rows,'exports':[]}
    if task=='G08':
        return {'customers':[{'id':'C-71','name':'Sam Lee','email':'sam.lee@cedar.example','live':{'street':'8 Keizersgracht','city':'Amsterdam','postal':'1011 AB','contact':'Phone'},'draft':None,'notes':[
            '2026-09-08: Proposed address: 14 Havenstraat, Delft, 2611 BC. Awaiting confirmation.',
            '2026-09-12: Customer confirmed: 27 Maasstraat, Rotterdam, 3011 AA. Preferred contact: Email. Supersedes the September 8 proposal.']},
            {'id':'C-72','name':'Sam Lee','email':'sam.lee@cedar-logistics.example','live':{'street':'4 West Road','city':'Utrecht','postal':'3511 CD','contact':'Phone'},'draft':None,'notes':['2026-09-10: No requested changes.']}]}
    if task=='G09':return {'cards':[
        {'id':'PROJ-218','title':'Review supplier agreement','column':'Ready','assignee':'Mina','due':'2026-09-18'},
        {'id':'PROJ-281','title':'Review supplier agreement','column':'Ready','assignee':'Leo','due':'2026-09-19'},
        {'id':'PROJ-203','title':'Prepare vendor summary','column':'Doing','assignee':'Mina','due':'2026-09-20'},
        {'id':'PROJ-211','title':'Confirm tax details','column':'Review','assignee':'Ivo','due':'2026-09-17'}]}
    if task=='G10':return {'case':{'id':'REQ-731','amount':'1750.00','expedited':True},'acknowledged':False,'approval':None}
    raise ValueError(task)

def apply(task,state,action):
    op=action['op']
    if task=='G05' and op=='reconcile':
        row=next(r for r in state['invoices'] if r['id']==action['id'])
        from decimal import Decimal
        row.update(total=format(Decimal(action['total']),'.2f'),reference=action['reference'],status='Reconciled')
    elif task=='G06' and op=='bulk':
        for row in state['tickets']:
            if row['id'] in action['ids']:
                row.update(owner=action['owner'],status=action['status'])
                if action['tag'] and action['tag'] not in row['tags']:row['tags'].append(action['tag'])
    elif task=='G08' and op in ['draft','publish']:
        row=next(r for r in state['customers'] if r['id']==action['id'])
        if op=='draft':row['draft']={k:action[k] for k in ['street','city','postal','contact']}
        elif row['draft'] is not None:row['live']=row['draft'];row['draft']=None
    elif task=='G09' and op=='move':
        if action['column'] not in ['Ready','Doing','Review']:raise ValueError('Unknown column')
        next(r for r in state['cards'] if r['id']==action['id'])['column']=action['column']
    elif task=='G10' and op=='ack':state['acknowledged']=True
    elif task=='G10' and op=='approve':
        if not state['acknowledged']:raise ValueError('Read and acknowledge the policy first')
        state['approval']={k:action[k] for k in ['route','reason']}
    else:raise ValueError('Unsupported operation')

def csv_bytes(rows):
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=['id','month','status','department','amount'],lineterminator='\n');w.writeheader();w.writerows(rows)
    return out.getvalue().encode('utf-8')

def expected(task):
    state=fixture(task)
    if task=='G05':state['invoices'][1].update(total='611.00',reference='PO-6041',status='Reconciled')
    if task=='G06':
        for r in state['tickets']:
            if r['id'] in ['T-301','T-304','T-306','T-308']:r.update(owner='Mina',status='Queued',tags=['Reviewed'])
    if task=='G08':state['customers'][0]['live']={'street':'27 Maasstraat','city':'Rotterdam','postal':'3011 AA','contact':'Email'}
    if task=='G09':state['cards'][0]['column']='Review'
    if task=='G10':state.update(acknowledged=True,approval={'route':'Manager','reason':'EXP-7'})
    return state

def grade(task,state,download=None):
    want=expected(task);checks={}
    if task=='G05':checks={'target_reconciled':state['invoices'][1]==want['invoices'][1],'other_invoice_unchanged':state['invoices'][0]==want['invoices'][0],'orders_unchanged':state['orders']==want['orders']}
    if task=='G06':
        checks={r['id']:r==w for r,w in zip(state['tickets'],want['tickets'])}
    if task=='G07':
        rows=[r for r in want['expenses'] if r['id'] in ['E-101','E-107','E-109','E-112']]
        # Order is immaterial to a CSV export; compare parsed records, including duplicates and values.
        try:parsed=list(csv.DictReader(io.StringIO(download.decode('utf-8')))) if download is not None else []
        except (ValueError,UnicodeError,csv.Error):parsed=[]
        checks={'download_exists':download is not None,'exact_records':sorted(parsed,key=lambda r:r.get('id',''))==rows,'expenses_unchanged':state['expenses']==want['expenses']}
    if task=='G08':checks={'live_profile':state['customers'][0]['live']==want['customers'][0]['live'],'draft_cleared':state['customers'][0]['draft'] is None,'identity_and_notes_unchanged':all(state['customers'][0][k]==want['customers'][0][k] for k in ['id','name','email','notes']),'other_customer_unchanged':state['customers'][1]==want['customers'][1]}
    if task=='G09':checks={r['id']:r==w for r,w in zip(state['cards'],want['cards'])}
    if task=='G10':checks={'policy_acknowledged':state['acknowledged'],'correct_approval':state['approval']==want['approval'],'case_unchanged':state['case']==want['case']}
    return {'reward':int(bool(checks) and all(checks.values())),'checks':checks}
