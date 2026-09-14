import json,pathlib
from task_world import PROMPTS,GUARD,fixture,expected_actions,grade,apply
ROOT=pathlib.Path(__file__).resolve().parent
descriptions={'G14':'库存补货：计算整包数量 → 单张采购单 → 关联并关闭申请',
              'G15':'视觉商品匹配：跨页查找图案 → 规格与数量 → 保留原购物车商品',
              'G16':'工单去重：核对多个字段 → 找最早报告 → 建立 Duplicate 关系'}
for task,prompt in PROMPTS.items():
    folder=ROOT/'tasks'/task;folder.mkdir(parents=True,exist_ok=True)
    (folder/'prompt.md').write_text(prompt+'\n\n'+GUARD+'\n')
    (folder/'fixture.json').write_text(json.dumps(fixture(task),indent=2)+'\n')
    s=fixture(task)
    for a in expected_actions(task):apply(task,s,a)
    (folder/'truth.json').write_text(json.dumps({'task':task,'one_valid_final_state':s,'checks':list(grade(task,s)['checks']),
        'alternative_action_orders_allowed':True,'reference_actions':expected_actions(task),
        'materialized_wrong_control_actions':expected_actions(task,False)},indent=2)+'\n')
    (folder/'task.json').write_text(json.dumps({'task':task,'description':descriptions[task],'kind':'synthetic_gui_workflow',
        'benchmark_reproduction':False,'runners':['ubuntu-24.04','macos-15','windows-2022'],
        'os_specific_claim':False,'requires_model_validation':True,'prompt':'prompt.md',
        'fixture':'fixture.json','truth':'truth.json','source':'../../task_world.py'},ensure_ascii=False,indent=2)+'\n')
(ROOT/'README.md').write_text('''# EnvShift GUI 第五批：G14–G16

三道自行编写的 GUI 工作流，参考 WorkArena++、VisualWebArena、WebArena，并采用 OSWorld-Verified 的初始化与验收经验。出处与实际改编见 [BENCHMARK_REFERENCES.md](BENCHMARK_REFERENCES.md)。

| 题号 | 题目 | 题面 |
|---|---|---|
| G14 | 库存补货、下单、关闭申请 | [prompt.md](tasks/G14/prompt.md) |
| G15 | 看图选商品、配置规格、维护购物车 | [prompt.md](tasks/G15/prompt.md) |
| G16 | 多字段核对和工单去重关联 | [prompt.md](tasks/G16/prompt.md) |

本批初始计划是 3 题 × 3 系统的 9 次模型运行。先执行每格 GUI oracle 与真实错误交付对照；任何对照失败先修装置，不能计作模型 badcase。模型沿用 gemini-3.5-flash / gui_native_v2 / 60 步，最多 3 个并发。

旧批累计 4 个 badcase 题目、22 条有效失败轨迹全部保留。新题是否失败、是否稳定、是否为 OS 差异，分别记录，未经验证不下结论。

源码与汇总实验记录可公开；完整截图、日志、环境记录保存在本地归档，不新增永久公开的完整证据上传。

本地路径：`/Users/conglin/Downloads/cl实验/EnvShift-GUI第五批-20260914/tasks/`
''')
(ROOT/'TEST_PLAN.md').write_text('''# 预先登记的测试计划

- 三题：G14、G15、G16；三系统：ubuntu-24.04、macos-15、windows-2022。
- 第一阶段每格两条 GUI 对照：oracle 应 reward=1；完整执行的错误交付应 reward=0。对照只有在全部预期审计事件实际产生时才算 materialized。
- 第二阶段每格一次全新 runner 模型运行：gemini-3.5-flash，gui_native_v2，60 步；同一组源码 SHA256；最多 3 个并发。
- 模型只看当前截图和最近 6 条操作；没有 DOM、终端、历史图片或笔记。参考控制器可用 DOM 定位/聚焦，但实际动作由原生键鼠执行。公开 benchmark 的代理设定不同，成绩不可直接比较。
- 所有最终交付判分均在模型运行前固定。done 不作为额外成功条件；提前完成后继续误改则按最终状态验收。G14 的“一单”要求在题面中明确，不能回溯套用到 G11。
- 初始 fixture 必须失败；允许合理操作次序和逐个/批量处理。检查实际错误状态被拒绝、旁支数据保持不变。
- 运行失败、网关持续故障、盲操作、参考控制失败均不计模型 badcase。可恢复的工具/解析问题单独记录。
- 单次失败只叫新 badcase 候选；稳定性需要固定条件追加前瞻复测。跨系统表现不同也不自动等于 OS 因果。
- 原始 Actions artifact 下载后逐文件验 SHA256，完整证据本地留存。向公开 Git 仓库仅发布合成题目源码和汇总实验记录。
- 后续修订必须保留已执行的版本、控制结果和源代码；模型开跑后不修改该批题目/判据。
''')
(ROOT/'CONTINUE.md').write_text('''# 接续记录

当前批 G14–G16，题目参考见 BENCHMARK_REFERENCES.md，固定测试计划见 TEST_PLAN.md。
用户要求出完直接用 GitHub runner 验证，沿用现有模型，保留全部旧 badcase；无需再次询问普通题目发布与运行。
完整截图/日志/环境的永久公开 Git 上传曾被自动审批拒绝；仅公开源码和汇总记录，完整证据保留本地。
执行顺序：check_verifiers.py → local_preview.py → publish_workflow.py → dispatch.py control → watch.py control → 九格对照均通过后 dispatch.py agent → watch.py agent → 审阅和归档。
不得重跑已有 *_RUN.json 的 dispatch；先读记录和 GitHub 确认已有运行。模型循环不得改动。
''')
print('Wrote three task packages and preregistered test plan')
