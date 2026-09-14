import collections,csv,io,json,pathlib,sys,zipfile
root=pathlib.Path(sys.argv[1])
def inbox_bytes():
    with zipfile.ZipFile(root/'incoming.zip') as z:
        return [z.read(info) for info in z.infolist() if not info.is_dir()]
def received_bytes():
    return [p.read_bytes() for p in sorted((root/'received').rglob('*')) if p.is_file()]
bodies=inbox_bytes()
rows={json.loads(b)['id']:(json.loads(b),b) for b in bodies}
sums=collections.defaultdict(lambda:[0,0])
for row,b in rows.values():
    sums[row['department']][0]+=1;sums[row['department']][1]+=row['amount_cents']
out=root/'output';out.mkdir(exist_ok=True)
with (out/'summary.csv').open('w',encoding='utf-8',newline='') as f:
    w=csv.writer(f);w.writerow(['department','receipt_count','total_amount'])
    for dept,(count,amount) in sorted(sums.items()):w.writerow([dept,count,'%d.%02d'%(amount//100,amount%100)])
with zipfile.ZipFile(out/'receipts.zip','w',zipfile.ZIP_DEFLATED) as z:
    for id,(row,b) in sorted(rows.items()):z.writestr(id+'.json',b)
