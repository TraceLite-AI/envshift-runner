import hashlib, json, os, pathlib, sys, zipfile
root=pathlib.Path(sys.argv[1]);root.mkdir(parents=True,exist_ok=True)
received=root/'received';received.mkdir()
records=[]
for i in range(1,73):
    records.append(dict(id='R%04d'%i,department=['Design','Field','Support','Research'][i%4],amount_cents=1300+i*79,description='Travel reimbursement %04d'%i))
names=['receipt-%04d.json'%i for i in range(1,73)]
names[16]='Cafe\u0301-receipt.json'
names[17]='Caf\u00e9-receipt.json'
names[40]='Re\u0301union-receipt.json'
names[41]='R\u00e9union-receipt.json'
with zipfile.ZipFile(root/'incoming.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name,row in zip(names,records):
        info=zipfile.ZipInfo(name,date_time=(2026,8,31,12,0,0));info.compress_type=zipfile.ZIP_DEFLATED
        body=(json.dumps(row,ensure_ascii=True,sort_keys=True)+'\n').encode('utf-8')
        z.writestr(info,body)
        row['source_sha256']=hashlib.sha256(body).hexdigest()
with zipfile.ZipFile(root/'incoming.zip') as z:
    z.extractall(received)
(root/'output').mkdir()
(root/'HANDOFF.txt').write_text('Finance intake has unpacked incoming.zip into received/. The original archive is retained for reconciliation. Create the requested delivery under output/.\n',encoding='utf-8')
truth=pathlib.Path(os.environ['NC_TRUTH'])
truth.write_text(json.dumps(dict(records=records,archive_sha256=hashlib.sha256((root/'incoming.zip').read_bytes()).hexdigest()),ensure_ascii=True),encoding='utf-8')
print(json.dumps(dict(source_entries=len(records),received_files=sum(p.is_file() for p in received.rglob('*')),source_sha256=hashlib.sha256((root/'incoming.zip').read_bytes()).hexdigest())))
