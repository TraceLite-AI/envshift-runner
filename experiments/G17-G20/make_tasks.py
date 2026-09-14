import json,pathlib
from task_world import PROMPTS,TITLES,GUARD,fixture,expected_actions,grade,apply
ROOT=pathlib.Path(__file__).resolve().parent
for task,prompt in PROMPTS.items():
    folder=ROOT/'tasks'/task;folder.mkdir(parents=True,exist_ok=True)
    (folder/'prompt.md').write_text(prompt+'\n\n'+GUARD+'\n')
    (folder/'fixture.json').write_text(json.dumps(fixture(task),indent=2)+'\n')
    s=fixture(task)
    for a in expected_actions(task):apply(task,s,a)
    assert grade(task,s)['reward']==1
    (folder/'truth.json').write_text(json.dumps({'task':task,'one_valid_final_state':s,'checks':list(grade(task,s)['checks']),'alternative_action_orders_allowed':True,'reference_actions':expected_actions(task),'materialized_wrong_control_actions':expected_actions(task,False)},indent=2)+'\n')
    (folder/'task.json').write_text(json.dumps({'task':task,'title':TITLES[task],'kind':'synthetic_browser_gui_workflow','benchmark_reproduction':False,'runners':['ubuntu-24.04','macos-15','windows-2022'],'os_specific_claim':False,'requires_model_validation':True,'prompt':'prompt.md','fixture':'fixture.json','truth':'truth.json','source':'../../task_world.py'},indent=2)+'\n')
print('Wrote G17-G20 task packages')
