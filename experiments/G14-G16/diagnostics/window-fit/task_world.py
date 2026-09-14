"""G14-G16: synthetic benchmark-inspired workflows, immutable business truth."""
import copy
import math

GUARD = 'Use the visible application and browser UI only. Do not open a terminal or DevTools, execute code, or browse other websites.'
PROMPTS = {
    'G14': 'Complete replenishment request REQ-204 for North Lab. Use the policy in the request and the Inventory page to calculate what to order. Submit exactly one purchase order containing only the required products and pack quantities, with Standard priority and reference REQ-204. Then resolve REQ-204 and link that purchase order. Leave other requests and the inventory records unchanged.',
    'G15': 'Find the tote whose printed design matches the reference image shown in the application. Add two of that design to the cart in the 18 L size with Zipper closure. Keep the existing Travel pouch and its quantity unchanged, and do not add any other product or variant. The completed cart is the final deliverable.',
    'G16': 'In the Billing API queue, deduplicate reports for customer AC-72, invoice INV-1048, failure code PAY-RETRY-02. Among reports matching all three fields, keep the earliest-created report open as the canonical report. Resolve every other matching report as Duplicate and link each to that canonical report. Leave all other reports, titles, assignees, and comments unchanged. You can compare selected reports to inspect their full details together.',
}
TITLES = {'G14':'Supply Desk', 'G15':'Field Goods', 'G16':'Incident Desk'}
POLICY = ('Available = On hand - Reserved + Incoming. Replenish only when Available is strictly below Minimum. '
          'Order enough whole packs to bring Available up to Target; round the pack quantity up. '
          'Use the listed product IDs, North Lab delivery, Standard priority, and reference REQ-204. '
          'Submit one combined order, then resolve this request and link the submitted order.')
TARGET_PACKS = {'KEY-14':7, 'DOCK-28':4, 'HEAD-36':4}
TARGET_PRODUCT = 'FG-407'
CANONICAL = 'INC-3108'
DUPLICATES = {'INC-3101', 'INC-3103', 'INC-3110'}

def fixture(task):
    if task == 'G14':
        values = [
            ('KEY-14','Compact keyboard',18,5,4,20,50,5,90),
            ('MOU-22','Wireless mouse',25,3,0,15,40,5,65),
            ('DOCK-28','USB-C dock',7,2,3,10,24,4,140),
            ('CAM-32','Conference camera',12,2,0,10,20,2,100),
            ('HEAD-36','USB headset',14,4,0,12,30,5,80),
            ('CAB-42','USB-C cable',40,10,0,20,50,10,45),
        ]
        return {'inventory':[dict(zip(['id','name','on_hand','reserved','incoming','minimum','target','pack_size','pack_price'],v)) for v in values],
                'requests':[{'id':'REQ-204','title':'Replenish North Lab peripherals','status':'Open','order_id':None,'policy':POLICY},
                            {'id':'REQ-205','title':'Spare adapters for South Lab','status':'Open','order_id':None,'policy':'Await manager review.'}],
                'cart':{}, 'orders':[]}
    if task == 'G15':
        # Product labels deliberately do not describe the print; the task requires visual grounding.
        products = [{'id':'FG-'+str(i),'name':'Trail tote','print':j,'price':28} for j,i in enumerate([401,414,402,420,405,418,403,411,407,416,409,422])]
        return {'products':products,'cart':[{'product':'POUCH-01','name':'Travel pouch','size':'One size','closure':'Zip','quantity':1}]}
    if task == 'G16':
        values = [
            ('INC-3101','Double charge after retry','AC-72','INV-1048','PAY-RETRY-02','2026-09-14 09:02','Morgan'),
            ('INC-3102','Payment retry rejected','AC-72','INV-1048','PAY-AUTH-01','2026-09-14 08:30','Lee'),
            ('INC-3103','Second debit on payment retry','AC-72','INV-1048','PAY-RETRY-02','2026-09-14 09:21','Sam'),
            ('INC-3104','Double charge after retry','AC-73','INV-1048','PAY-RETRY-02','2026-09-14 08:10','Lee'),
            ('INC-3105','Double charge after retry','AC-72','INV-1084','PAY-RETRY-02','2026-09-14 08:20','Morgan'),
            ('INC-3106','Invoice PDF not available','AC-72','INV-1048','PDF-404','2026-09-14 08:35','Sam'),
            ('INC-3108','Retry charged card twice','AC-72','INV-1048','PAY-RETRY-02','2026-09-14 08:45','Lee'),
            ('INC-3110','Duplicate debit from retry','AC-72','INV-1048','PAY-RETRY-02','2026-09-14 10:05','Morgan'),
            ('INC-3112','Retry timed out before payment','AC-72','INV-1048','PAY-TIMEOUT','2026-09-14 08:40','Sam'),
        ]
        reports=[]
        for v in values:
            r=dict(zip(['id','title','customer','invoice','failure','created','assignee'],v))
            r.update(status='Open',resolution=None,duplicate_of=None,comments=['Customer log attached; retain for investigation.'])
            reports.append(r)
        return {'queue':'Billing API','reports':reports}
    raise ValueError(task)

def apply(task,state,action):
    op=action['op']
    if task == 'G14':
        if op == 'cart':
            pid=action['product'];qty=action['quantity']
            if pid not in {p['id'] for p in state['inventory']} or type(qty) is not int or not 0<=qty<=100:raise ValueError('Choose a product and a whole pack quantity from 0 to 100')
            if qty:state['cart'][pid]=qty
            else:state['cart'].pop(pid,None)
        elif op == 'submit-order':
            if not state['cart']:raise ValueError('Your cart is empty')
            if action['destination'] not in ['North Lab','South Lab'] or action['priority'] not in ['Standard','Urgent']:raise ValueError('Invalid delivery option')
            state['orders'].append({'id':'PO-'+str(7001+len(state['orders'])),'items':copy.deepcopy(state['cart']),
                                    'destination':action['destination'],'priority':action['priority'],'reference':str(action['reference']).strip()})
            state['cart'].clear()
        elif op == 'resolve-request':
            req=next(r for r in state['requests'] if r['id']==action['id'])
            if action['order_id'] not in {o['id'] for o in state['orders']}:raise ValueError('Link a submitted order first')
            req.update(status='Resolved',order_id=action['order_id'])
        else:raise ValueError('Unsupported operation')
    elif task == 'G15':
        if op == 'add-cart':
            if action['product'] not in {p['id'] for p in state['products']}:raise ValueError('Unknown product')
            if action['size'] not in ['12 L','18 L','24 L'] or action['closure'] not in ['Open','Zipper']:raise ValueError('Choose a valid variant')
            if type(action['quantity']) is not int or not 1<=action['quantity']<=20:raise ValueError('Choose quantity 1 to 20')
            row=next((r for r in state['cart'] if (r['product'],r['size'],r['closure'])==(action['product'],action['size'],action['closure'])),None)
            if row:row['quantity']+=action['quantity']
            else:state['cart'].append({'product':action['product'],'name':'Trail tote','size':action['size'],'closure':action['closure'],'quantity':action['quantity']})
        elif op == 'set-cart':
            row=state['cart'][action['index']];q=action['quantity']
            if type(q) is not int or not 0<=q<=20:raise ValueError('Choose quantity 0 to 20')
            if q:row['quantity']=q
            else:state['cart'].pop(action['index'])
        else:raise ValueError('Unsupported operation')
    elif task == 'G16' and op == 'duplicate':
        ids=action['ids'];target=action['canonical']
        known={r['id'] for r in state['reports']}
        if not ids or len(set(ids))!=len(ids) or not set(ids)<=known or target not in known or target in ids:raise ValueError('Select reports and a different canonical report')
        canonical=next(r for r in state['reports'] if r['id']==target)
        if canonical['status']!='Open':raise ValueError('The canonical report must be open')
        for r in state['reports']:
            if r['id'] in ids:r.update(status='Resolved',resolution='Duplicate',duplicate_of=target)
    else:raise ValueError('Unsupported operation')

def grade(task,state,files=None):
    original=fixture(task)
    if task == 'G14':
        orders=state['orders'];req=state['requests'][0]
        order=orders[0] if len(orders)==1 else {}
        checks={'exactly_one_order':len(orders)==1,'correct_products_and_pack_quantities':order.get('items')==TARGET_PACKS,
                'delivery_and_reference':all(order.get(k)==v for k,v in {'destination':'North Lab','priority':'Standard','reference':'REQ-204'}.items()),
                'request_resolved_and_linked':req['status']=='Resolved' and bool(order) and req['order_id']==order['id'],
                'inventory_unchanged':state['inventory']==original['inventory'],
                'other_request_unchanged':state['requests'][1:]==original['requests'][1:],
                'request_identity_and_policy_unchanged':all(req[k]==original['requests'][0][k] for k in ['id','title','policy']),
                'cart_empty':state['cart']=={}}
    elif task == 'G15':
        key=lambda r:(r['product'],r['size'],r['closure'],r['quantity'])
        expected=original['cart']+[{'product':TARGET_PRODUCT,'name':'Trail tote','size':'18 L','closure':'Zipper','quantity':2}]
        checks={'exact_cart_products_variants_quantities':sorted(map(key,state['cart']))==sorted(map(key,expected)),
                'existing_pouch_unchanged':[r for r in state['cart'] if r['product']=='POUCH-01']==original['cart'],
                'catalog_unchanged':state['products']==original['products']}
    else:
        expected=copy.deepcopy(original)
        for r in expected['reports']:
            if r['id'] in DUPLICATES:r.update(status='Resolved',resolution='Duplicate',duplicate_of=CANONICAL)
        checks={'all_matching_duplicates_resolved_and_linked':all(next(r for r in state['reports'] if r['id']==pid)==next(r for r in expected['reports'] if r['id']==pid) for pid in DUPLICATES),
                'canonical_report_unchanged':next(r for r in state['reports'] if r['id']==CANONICAL)==next(r for r in original['reports'] if r['id']==CANONICAL),
                'all_other_records_and_metadata_unchanged':state==expected}
    return {'reward':int(all(checks.values())),'checks':checks}

def expected_actions(task,good=True):
    """Independent literal reference actions; real controls replay them via the GUI."""
    if task=='G14':
        items={'KEY-14':7,'DOCK-28':4,'HEAD-36':4 if good else 3}
        return [{'op':'cart','product':p,'quantity':q} for p,q in items.items()]+[
            {'op':'submit-order','destination':'North Lab','priority':'Standard','reference':'REQ-204'},
            {'op':'resolve-request','id':'REQ-204','order_id':'PO-7001'}]
    if task=='G15':return [{'op':'add-cart','product':'FG-407' if good else 'FG-411','size':'18 L','closure':'Zipper','quantity':2}]
    return [{'op':'duplicate','ids':sorted(DUPLICATES),'canonical':CANONICAL if good else 'INC-3104'}]
