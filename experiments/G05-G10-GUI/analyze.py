"""Summarize selected model runs and retain every valid unsuccessful trajectory."""
import argparse, hashlib, json, pathlib, shutil, zipfile
ap=argparse.ArgumentParser();ap.add_argument('--run',action='append',required=True);ap.add_argument('--output',default='AGENT_RESULTS.json');ap.add_argument('--commit',default='c230fc6a1c2fb98a336b7154ba8d15b16e6605c0');args=ap.parse_args()
root=pathlib.Path(__file__).resolve().parent
rows=[]
index_path=root/'badcases/INDEX.json'
retained={r['id']:r for r in json.loads(index_path.read_text(encoding='utf-8'))} if index_path.exists() else {}
for spec in args.run:
    run,folder=spec.split(':',1)
    for p in sorted((root/folder).rglob('meta.json')):
        m=json.loads(p.read_text(encoding='utf-8'))
        if m.get('arm')!='agent':continue
        trace_path=p.parent/'agent/loop.json'
        trace=json.loads(trace_path.read_text(encoding='utf-8')) if trace_path.exists() else {}
        history=trace.get('history',[]);last=history[-1].get('action',{}) if history else {}
        valid=bool(m.get('valid_model_run')) and trace.get('coordinate_mode')=='normalized_0_1000'
        runner='macos-15' if 'macOS' in m['platform'] else 'windows-2022' if 'Windows' in m['platform'] else 'ubuntu-24.04'
        category='invalid_run' if not valid else 'correct_delivery' if m['reward'] else 'false_completion' if last.get('action')=='done' else 'unfinished_or_incorrect_delivery'
        row={**m,'tool_version':trace.get('tool_version'),'run_id':int(run),'runner':runner,'artifact_meta':str(p.relative_to(root)),'protocol_valid':valid,'last_action':last,'classification':category,'execution_errors':[h for h in history if '执行失败' in h.get('result','')],'parse_errors':sum(h.get('action',{}).get('action')=='?' for h in history)}
        rows.append(row);print(m['task'],runner,'reward='+str(m['reward']),'steps='+str(m['steps']),category)
        if valid and not m['reward']:
            bid=f'BC-{m["task"]}-{runner}-{run}'
            b=root/'badcases'/bid;b.mkdir(parents=True,exist_ok=True)
            shutil.copytree(p.parent,b/'failure',dirs_exist_ok=True)
            record={'id':bid,'task':m['task'],'model':m['model'],'classification':category,'stable_os_failure_proven':False,'failure':row,'tested_commit':args.commit,'note':'Retained observed badcase; a single trajectory does not establish an OS cause or stable failure rate.'}
            (b/'badcase.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            manifest={str(f.relative_to(b)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(b.rglob('*')) if f.is_file() and f.name!='SHA256.json'}
            (b/'SHA256.json').write_text(json.dumps(manifest,indent=2)+'\n')
            with zipfile.ZipFile(root/'badcases'/(bid+'.zip'),'w',zipfile.ZIP_DEFLATED) as z:
                for f in sorted(b.rglob('*')):
                    if f.is_file():z.write(f,str(f.relative_to(b.parent)))
(root/args.output).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
for p in sorted((root/'badcases').glob('*/badcase.json')):
    record=json.loads(p.read_text(encoding='utf-8'));retained[record['id']]=record
index=list(retained.values())
(root/'badcases/INDEX.json').write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
