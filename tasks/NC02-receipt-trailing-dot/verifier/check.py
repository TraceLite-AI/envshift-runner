import collections,csv,hashlib,io,json,pathlib,re,sys,zipfile
root,truthpath,log=map(pathlib.Path,sys.argv[1:4]);log.mkdir(parents=True,exist_ok=True)
ledger=json.loads(truthpath.read_text(encoding='utf-8'));truth=ledger['records']
checks=[]
def add(name,ok,points,detail=''):
    checks.append(dict(name=name,passed=bool(ok),points=points,detail=str(detail)[:500]))
sums=collections.defaultdict(lambda:[0,0])
for e in truth:sums[e['department']][0]+=1;sums[e['department']][1]+=e['amount_cents']
want=[['department','receipt_count','total_amount']]+[[d,str(n),'%d.%02d'%(a//100,a%100)] for d,(n,a) in sorted(sums.items())]
try:
    raw=(root/'output/summary.csv').read_bytes()
    got=list(csv.reader(io.StringIO(raw.decode('utf-8-sig'))))
    add('汇总CSV可读',True,10)
    add('逐部门汇总正确',got==want,40,repr(got))
except Exception as exc:
    add('汇总CSV可读',False,10,repr(exc));add('逐部门汇总正确',False,40)
try:
    with zipfile.ZipFile(root/'output/receipts.zip') as z:
        infos=z.infolist();names=[i.filename for i in infos]
        expected={e['id']+'.json':e['source_sha256'] for e in truth}
        add('凭证ZIP可读',True,10)
        add('凭证齐全且命名正确',len(names)==len(expected) and set(names)==set(expected),20,str(len(names))+' members')
        same=all(hashlib.sha256(z.read(name)).hexdigest()==digest for name,digest in expected.items() if name in names)
        add('原件字节完整',set(names)==set(expected) and same,20)
except Exception as exc:
    add('凭证ZIP可读',False,10,repr(exc));add('凭证齐全且命名正确',False,20);add('原件字节完整',False,20)
try:
    add('原始来件未修改',hashlib.sha256((root/'incoming.zip').read_bytes()).hexdigest()==ledger['archive_sha256'],10)
except OSError as exc:
    add('原始来件未修改',False,10,repr(exc))
pts=sum(c['points'] for c in checks if c['passed']);total=sum(c['points'] for c in checks)
result=dict(reward=int(pts==total),points=pts,total=total,checks=checks)
(log/'trace_results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=True))
sys.exit(0 if result['reward'] else 1)
