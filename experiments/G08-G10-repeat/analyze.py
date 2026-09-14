"""Describe observed trials and archive references without assuming their outcome."""
import argparse, collections, hashlib, json, pathlib
from publish_workflow import ROOT

def write(name,data):
    (ROOT/name).parent.mkdir(parents=True,exist_ok=True)
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def analyze(partial=False):
    experiment=json.loads((ROOT/'EXPERIMENT.json').read_text())
    rows=json.loads((ROOT/'AGENT_RESULTS.json').read_text())
    controls=json.loads((ROOT/'CONTROL_RESULTS.json').read_text())
    assert len({(r['task'],r['trial']) for r in rows})==len(rows)
    details=[];badcases=[];groups=[]
    def signature(r):
        return {'source_commit':r['runtime']['source_commit'],'source_sha256':r['runtime']['source_sha256'],
                'python':r['runtime']['python'],'platform':r['runtime']['platform'],
                'runner_image':r['runtime']['runner_image'],'pip_freeze':r['pip_freeze'],
                'browser':r['environment'].get('browser'),'screen_size':r['environment'].get('screen_size')}
    signatures={json.dumps(signature(r),sort_keys=True) for r in rows+controls}
    for r in rows:
        d=ROOT/r['evidence'];loop=json.loads((d/'agent/loop.json').read_text()) if (d/'agent/loop.json').exists() else {}
        history=loop.get('history',[]);actions=[h.get('action',{}) for h in history]
        counts=collections.Counter(json.dumps(a,sort_keys=True,ensure_ascii=False) for a in actions)
        frames=sorted((d/'agent').glob('step*.png'))+[d/'agent-final.png']
        hashes=[hashlib.sha256(p.read_bytes()).hexdigest() for p in frames if p.exists()]
        streak=longest=1
        for first,second in zip(hashes,hashes[1:]):
            streak=streak+1 if first==second else 1;longest=max(longest,streak)
        meta=r['meta'];audit=meta.get('audit',[])
        classification=('invalid_run' if not r['valid'] else 'correct_delivery' if r['reward']==1 else
                        'false_completion' if actions and actions[-1].get('action')=='done' else
                        'step_budget_exhausted' if r['steps']==experiment['steps'] else 'unfinished_or_incorrect_delivery')
        detail={k:r[k] for k in ['task','trial','run','valid','reward','steps','evidence','archive']}
        detail.update(classification=classification,
                      failed_checks=[k for k,v in meta.get('checks',{}).items() if not v],audit=audit,
                      action_types=dict(collections.Counter(a.get('action') for a in actions)),
                      most_repeated_actions=[{'action':json.loads(k),'count':v} for k,v in counts.most_common(5)],
                      longest_identical_screenshot_streak=longest if hashes else 0,
                      identical_adjacent_screenshots=sum(x==y for x,y in zip(hashes,hashes[1:])),
                      scroll_actions_with_unsupported_xy=sum(a.get('action')=='scroll' and ('x' in a or 'y' in a) for a in actions),
                      execution_error_steps=[i for i,h in enumerate(history,1) if h.get('result','').startswith('执行失败')],
                      parse_error_steps=[i for i,a in enumerate(actions,1) if a.get('action')=='?'])
        details.append(detail)
        if r['valid'] and r['reward']==0:
            bid=f'BC-{r["task"]}-ubuntu-24.04-{r["run"]}-trial{r["trial"]}'
            bc={'id':bid,'task':r['task'],'model':experiment['model'],'classification':classification,
                'tested_commit':experiment['source_commit'],'workflow_commit':json.loads((ROOT/'REMOTE.json').read_text())['commit'],
                'trial':r['trial'],'run':r['run'],'stable_os_failure_proven':False,'failure':detail,
                'archive_sha256':hashlib.sha256((ROOT/r['archive']).read_bytes()).hexdigest(),
                'note':'Prospectively collected fixed-configuration repeat. Interpret jointly with the full five-trial series; valid successes also retained.'}
            folder=ROOT/'badcases'/bid;folder.mkdir(parents=True,exist_ok=True)
            (folder/'badcase.json').write_text(json.dumps(bc,ensure_ascii=False,indent=2)+'\n')
            badcases.append(bc)
    for task in experiment['tasks']:
        trial_rows=[r for r in rows if r['task']==task];valid=[r for r in trial_rows if r['valid']]
        if not partial:assert len(valid)==5, f'{task}: expected five valid trials, got {len(valid)}'
        groups.append({'task':task,'collected':len(trial_rows),'valid':len(valid),'invalid':len(trial_rows)-len(valid),
                       'successes':sum(r['reward']==1 for r in valid),'failures':sum(r['reward']==0 for r in valid),
                       'all_five_failed':len(valid)==5 and all(r['reward']==0 for r in valid)})
    old_index=json.loads((ROOT/'PRIOR_BADCASES.json').read_text())
    summary={'complete':not partial,'source_and_runtime_uniform':len(signatures)==1,
             'observed_runtime_signatures':len(signatures),'groups':groups,
             'retained_failure_trajectories':len(badcases),'stable_os_failure_proven':False,
             'previous_failure_trajectories':len(old_index),
             'total_retained_failure_trajectories':len(old_index)+len(badcases),
             'distinct_badcase_tasks_including_prior':len({r['task'] for r in old_index+badcases}),
             'runtime_signature':signature(controls[0])}
    write('TRIAL_ANALYSIS.json',details);write('SUMMARY.json',summary);write('badcases/INDEX.json',badcases)
    if not partial:
        assert len(signatures)==1, 'Runtime drift found; report strata before claiming fixed configuration.'
        experiment['status']='complete';experiment['summary']=summary
        write('EXPERIMENT.json',experiment)
    report=['# G08 / G10 GUI 固定配置复测','',
            '状态：'+('部分结果，试验仍在运行。' if partial else '已完成；以下仅统计本轮预先指定的新增试验。'),'',
            '| 题目 | 有效次数 | 成功 | 失败 | 无效运行 |','|---|---:|---:|---:|---:|']
    for g in groups:report.append(f'| {g["task"]} | {g["valid"]} | {g["successes"]} | {g["failures"]} | {g["invalid"]} |')
    report+=['','每题 5 次从干净 GitHub Ubuntu runner 启动。gemini-3.5-flash，60 步，gui_native_v2；无 notebook。',
             f'本轮新增 {len(badcases)} 条失败轨迹；连同此前累计 {summary["total_retained_failure_trajectories"]} 条，仍对应 {summary["distinct_badcase_tasks_including_prior"]} 道不同的 badcase 题目。复测次数不计为新题。',
             '原版任务、提示词、鼠标键盘工具、截图处理、判据及模型请求均未改动。历史只提供最新截图和最近 6 个动作。',
             '前置对照：G08、G10 的参考解全部通过，实际生成的错误业务状态全部被拒绝。参考解用 DOM 辅助定位与滚动，再执行物理键鼠；模型只看截图。','',
             '## 配置与判读边界','',
             f'- 源码提交：`{experiment["source_commit"]}`。',
             f'- 全部模型试验及对照的已记录运行环境是否一致：{summary["source_and_runtime_uniform"]}。',
             '- 每次保存并核对源码 SHA256、runner 镜像、Python、pip 包、Chrome 与屏幕尺寸。',
             '- 模型仍使用网关别名；后端权重、默认采样参数和服务端调度无法冻结。源码固定不等于后端模型快照固定。',
             '- 新 runner 使用全新 Chrome 配置目录；本地站点随机端口沿用原装置，因此不声称初始截图逐像素相同。业务数据和起始页面逻辑相同。',
             '- 0/5 表示本轮五次均失败，不能推断无限次必败，也不能证明换操作系统导致失败。',
             '- 这两个任务经先前失败样本筛选，属于候选题的前瞻复测，不是随机抽取任务的总体成功率估计。',
             '- 旧基线与 notebook 诊断保留在上一批报告中，不混入本轮分母。','',
             '## 逐次结果','',
             '| 题目 | 次数 | reward | 步数 | 结果类型 | 业务写入次数 | 连续相同截图最长段 |',
             '|---|---:|---:|---:|---|---:|---:|']
    for d in details:report.append(f'| {d["task"]} | {d["trial"]} | {d["reward"]} | {d["steps"]} | {d["classification"]} | {len(d["audit"])} | {d["longest_identical_screenshot_streak"]} |')
    report+=['','[行为复查](OBSERVATIONS.md)解释关键截图与操作循环；[复现命令](REPRODUCE.md)给出完整运行方式。',
             '截图相同是停滞线索，不能单独证明认知原因。动作明细、判分与业务审计见 `TRIAL_ANALYSIS.json`，每条原始证据见 `AGENT_RESULTS.json` 的 archive 字段。',
             'GitHub Actions 的 success 表示装置正常完成；模型成绩以 meta.json 的 reward 为准。',
             '全部成功、失败以及对照均保留，压缩包内部的 EVIDENCE_SHA256.json 可逐文件校验。',
             '全部有效失败另登记在 badcases/INDEX.json；一次失败轨迹不等于一道新题。','']
    (ROOT/'REPORT.md').write_text('\n'.join(report))
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--partial',action='store_true');a=p.parse_args();analyze(a.partial)
