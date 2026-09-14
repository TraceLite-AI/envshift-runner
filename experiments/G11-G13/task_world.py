"""G11-G13 fixtures and final-state grading. No OS-dependent business rules."""
import copy

GUARD = 'Use the visible application and browser UI only. Do not open a terminal or DevTools, execute code, or browse other websites.'
PROMPTS = {
    'G11': 'Export the approved September 2026 revenue report from the open page. Save it as revenue-2026-09.csv in Downloads, replacing the existing stale file with that exact name. Do not keep a copy with a different filename. Leave revenue-2026-08.csv unchanged.',
    'G12': 'Change the supplier on purchase order PO-918 to Cedar Components, vendor ID VEN-1048 (Rotterdam), and save the purchase order. Confirm the selected vendor ID is VEN-1048. Leave the amount, reference, other order, and vendor directory unchanged.',
    'G13': 'In the inventory grid, change only Reorder level for SKU-1048 to 24, SKU-1084 to 36, and SKU-1148 to 18, then save changes. Keep Reorder quantity and every other cell unchanged. The Reorder level column is toward the right of the wide table.',
}
TITLES = {'G11': 'Revenue report export', 'G12': 'Purchase order supplier', 'G13': 'Inventory planning grid'}
REPORT_NAME = 'revenue-2026-09.csv'
SENTINEL_NAME = 'revenue-2026-08.csv'
STALE = b'month,account,amount\n2026-09,Cedar,100.00\n'
SENTINEL = b'month,account,amount\n2026-08,Cedar,924.00\n'
# Immutable expected output; never inferred from delivered bytes or current app state.
REPORT = b'month,account,amount\n2026-09,Cedar,1684.50\n2026-09,Maple,927.25\n2026-09,Nori,611.00\n'
TARGETS = {'SKU-1048': 24, 'SKU-1084': 36, 'SKU-1148': 18}
COLS = [('sku','SKU'),('name','Product'),('warehouse','Warehouse'),('category','Category'),
        ('bin','Bin'),('on_hand','On hand'),('reserved','Reserved'),('incoming','Incoming'),
        ('lead_days','Lead days'),('unit_cost','Unit cost'),('supplier','Supplier'),
        ('pack','Pack size'),('reorder_level','Reorder level'),('reorder_quantity','Reorder quantity')]

def fixture(task):
    if task == 'G11':
        return {'month':'2026-09','revision':'SEP26-APPROVED-R4',
                'rows':[{'account':'Cedar','amount':'1684.50'}, {'account':'Maple','amount':'927.25'}, {'account':'Nori','amount':'611.00'}],
                'exports':[]}
    if task == 'G12':
        return {'orders':[{'id':'PO-918','vendor_id':'VEN-1020','amount':'611.00','reference':'STOCK-SEP'},
                          {'id':'PO-919','vendor_id':'VEN-1084','amount':'392.50','reference':'PARTS-SEP'}],
                'vendors':[{'id':'VEN-1020','name':'Maple Supply','city':'Utrecht'},
                           {'id':'VEN-1040','name':'Cedar Components','city':'Delft'},
                           {'id':'VEN-1048','name':'Cedar Components','city':'Rotterdam'},
                           {'id':'VEN-1084','name':'Cedar Components','city':'Amsterdam'},
                           {'id':'VEN-1090','name':'Nori Packaging','city':'Leiden'}], 'saves':0}
    if task == 'G13':
        ids = ['SKU-1008','SKU-1040','SKU-1048','SKU-1080','SKU-1084','SKU-1108','SKU-1140','SKU-1148']
        return {'rows':[{'sku':sku,'name':'Bracket '+str(i+1),'warehouse':'Main','category':'Hardware',
                         'bin':'A-'+str(i+11),'on_hand':70+i*3,'reserved':i+2,'incoming':20,
                         'lead_days':5,'unit_cost':'4.50','supplier':'Cedar','pack':6,
                         'reorder_level':12,'reorder_quantity':48} for i,sku in enumerate(ids)], 'saves':0}
    raise ValueError(task)

def report_bytes(state):
    # Rendering path intentionally separate from the literal oracle above.
    return ('month,account,amount\n'+''.join(f"{state['month']},{r['account']},{r['amount']}\n" for r in state['rows'])).encode('utf-8')

def apply(task,state,action):
    if task == 'G11' and action['op'] == 'export':
        state['exports'].append({'name':str(action['name'])})
    elif task == 'G12' and action['op'] == 'save-order':
        if action['vendor_id'] not in {v['id'] for v in state['vendors']}: raise ValueError('Select a vendor from the results')
        row = next(r for r in state['orders'] if r['id'] == action['id'])
        row['vendor_id'] = action['vendor_id']; state['saves'] += 1
    elif task == 'G13' and action['op'] == 'save-grid':
        updates = action['changes']
        # Validate the whole transaction before changing any row.
        assert len({(u['sku'],u['field']) for u in updates}) == len(updates)
        for u in updates:
            if u['sku'] not in {r['sku'] for r in state['rows']} or u['field'] not in ['reorder_level','reorder_quantity']:
                raise ValueError('Unknown editable cell')
            if type(u['value']) is not int or not 0 <= u['value'] <= 9999: raise ValueError('Enter a whole number between 0 and 9999')
        for u in updates: next(r for r in state['rows'] if r['sku'] == u['sku'])[u['field']] = u['value']
        state['saves'] += 1
    else: raise ValueError('Unsupported operation')

def expected(task):
    state = fixture(task)
    if task == 'G12': state['orders'][0]['vendor_id'] = 'VEN-1048'
    if task == 'G13':
        for r in state['rows']:
            if r['sku'] in TARGETS: r['reorder_level'] = TARGETS[r['sku']]
    return state

def grade(task,state,files=None):
    want = expected(task); checks = {}
    if task == 'G11':
        files = files or {}
        checks = {'canonical_file_has_approved_bytes':files.get(REPORT_NAME) == REPORT,
                  'august_file_unchanged':files.get(SENTINEL_NAME) == SENTINEL,
                  'no_alternative_report_files':set(files) == {REPORT_NAME,SENTINEL_NAME},
                  'report_data_unchanged':{k:v for k,v in state.items() if k != 'exports'} == {k:v for k,v in want.items() if k != 'exports'},
                  'successful_export_recorded':{'name':REPORT_NAME} in state['exports']}
    elif task == 'G12':
        checks = {'correct_supplier_and_preserved_order_fields':state['orders'][0] == want['orders'][0],
                  'other_order_unchanged':state['orders'][1:] == want['orders'][1:],
                  'vendor_directory_unchanged':state['vendors'] == want['vendors'], 'saved':state['saves'] > 0}
    elif task == 'G13':
        checks = {r['sku']+'_complete_row':r == w for r,w in zip(state['rows'],want['rows'])}
        checks.update(row_count_unchanged=len(state['rows']) == len(want['rows']),saved=state['saves'] > 0)
    else: raise ValueError(task)
    return {'reward':int(all(checks.values())), 'checks':checks}
