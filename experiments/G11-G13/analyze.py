"""Summarize verified GUI outcomes without converting invalid runs into badcases."""
import collections, hashlib, json, pathlib, re
from publish_workflow import ROOT

rows=json.loads((ROOT/'AGENT_RESULTS.json').read_text())
controls=json.loads((ROOT/'CONTROL_RESULTS.json').read_text())
prior=json.loads((ROOT/'PRIOR_BADCASES.json').read_text())
manifest=json.loads((ROOT/'EXPERIMENT.json').read_text())
results=[];badcases=[]
for row in rows:
    folder=ROOT/row['evidence'];meta=row['meta']
    loop=json.loads((folder/'agent/loop.json').read_text())
    history=loop.get('history',[])
    actions=collections.Counter(h['action'].get('action') for h in history)
    failures=[h for h in history if str(h.get('result','')).startswith('执行失败')]
    retries=(folder/'agent.log').read_text().count('后重试(')
    hashes=[hashlib.sha256((folder/'agent'/f'step{i:02d}.png').read_bytes()).hexdigest() for i in range(1,len(history)+1)]
    longest=max((len(list(g)) for _,g in __import__('itertools').groupby(hashes)),default=0)
    osname=row['artifact'].split(row['task']+'-',1)[1].split('-agent-',1)[0]
    result={'task':row['task'],'os':osname,'run':row['run'],'valid':row['valid'],'reward':row['reward'],
            'steps':row['steps'],'actions':dict(actions),'execution_errors':len(failures),'parse_errors':actions['?'],
            'channel_retries':retries,'longest_identical_screenshot_run':longest,
            'failed_checks':[k for k,v in meta['checks'].items() if not v],
            'completion_claimed':bool(history and history[-1]['action'].get('action')=='done'),
            'audit':meta['audit'],'evidence':row['evidence'],'archive':row['archive']}
    results.append(result)
    if row['valid'] and row['reward']==0:
        bid=f"BC-{row['task']}-{osname}-{row['run']}"
        record={'id':bid,'task':row['task'],'model':meta['model'],'tool_version':loop['tool_version'],
                'classification':'incorrect_final_state_after_done' if result['completion_claimed'] else 'action_budget_exhausted_without_correct_delivery',
                'stable_os_failure_proven':False,'independent_mechanism_claimed':False,
                'failure':{**result,'source_commit':row['runtime']['source_commit'],
                           'archive_sha256':hashlib.sha256((ROOT/row['archive']).read_bytes()).hexdigest()},
                'limitations':['One initial model trial per task and OS; no stability claim.',
                               'Reference uses DOM assistance; model sees screenshots only.',
                               'Frozen gui_native_v2 retains only latest screenshot and six recent actions.']}
        badcases.append(record)
        d=ROOT/'badcases'/bid;d.mkdir(parents=True,exist_ok=True)
        (d/'badcase.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
(ROOT/'badcases').mkdir(exist_ok=True)
(ROOT/'badcases/INDEX.json').write_text(json.dumps(badcases,ensure_ascii=False,indent=2)+'\n')
required={(t,o) for t in ['G11','G12','G13'] for o in ['ubuntu-24.04','macos-15','windows-2022']}
complete=len(results)==9 and {(r['task'],r['os']) for r in results}==required and all(r['valid'] for r in results)
source_consistent=all(r['runtime']['source_commit']==manifest['source_commit'] and r['runtime']['source_sha256']==manifest['source_sha256'] for r in rows+controls)
old_tasks={re.match(r'G\d+',r['task']).group() for r in prior}
new_tasks={r['task'] for r in badcases}-old_tasks
summary={'complete':complete,'controls_passed':len(controls)==9 and all(r['verified'] for r in controls),
         'source_consistent':source_consistent,'valid_model_runs':sum(r['valid'] for r in results),
         'passes':sum(r['valid'] and r['reward']==1 for r in results),'failures':len(badcases),
         'new_badcase_tasks':sorted(new_tasks),'all_badcase_tasks':sorted(old_tasks|new_tasks,key=lambda t:int(t[1:])),
         'all_failure_trajectories':len(prior)+len(badcases),'stable_os_flips_proven':0,'results':results}
(ROOT/'SUMMARY.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='results'},ensure_ascii=False))
for r in results:print(json.dumps({k:r[k] for k in ['task','os','valid','reward','steps','execution_errors','parse_errors','channel_retries','failed_checks']},ensure_ascii=False))
