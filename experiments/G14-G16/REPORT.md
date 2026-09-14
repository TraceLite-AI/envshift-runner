# G14–G16 GUI validation summary

本批新增 3 道已验证题目；当前装置的主结果采用 9 次有效模型试验，1 次通过、8 次失败。新增 3 个 badcase 题目：G14、G15、G16。

| 题号 | 任务 | Ubuntu | macOS | Windows |
|---|---|---|---|---|
| G14 | 库存补货、下单并关闭申请 | 失败 · 60 步 | 失败 · 60 步 | 失败 · 60 步 |
| G15 | 视觉商品匹配与规格购物车 | 通过 · 41 步 | 失败 · 60 步 | 失败* · 60 步 |
| G16 | 多字段核对与工单去重 | 失败 · 60 步 | 失败 · 60 步 | 失败* · 60 步 |

\* Windows 滚动单位存在工具混杂，详见 TOOL_SEMANTICS_REVIEW.md；本表是冻结工具下的端到端结果，不是隔离工具后的模型能力分数。

累计已验证 16 道 GUI 题；7 个 badcase 题目，30 条有效失败轨迹。旧 G01/G05/G08/G10 的 22 条记录全部保留。已证实稳定 OS 翻转仍为 0。

模型沿用 `gemini-3.5-flash`；工具循环 `gui_native_v2` 未修改，预算 60 步，并发上限 3。模型只看当前截图与最近 6 条操作，无历史图片、笔记或 DOM。三系统业务规则完全相同，初测每格一次。

主结果的 9 组 GUI 对照均通过：参考解 reward=1，完整执行的错误交付 reward=0，审计已核验。业务逻辑、界面和代理循环四个文件逐字节相同；runner 仅增加了 Windows 开始前最大化窗口的步骤，见 SOURCE_COMPATIBILITY.json。

参考解使用 DOM 辅助定位、scrollIntoView 后配合原生键鼠；模型没有 DOM 权限。对照验证业务交付与判分，不能证明滚动等动作原语在三系统完全等价。

本批实际执行 12 次模型运行：初轮 9 次，加修正后的 Windows 3 次。原轮 Windows 三格因内容被任务栏遮挡统一作为装置诊断排除；主结果采用原轮 Ubuntu/macOS 六格和修正后 Windows 三格。初轮原始统计为 1 次通过、8 次失败，完整保存在 INITIAL_SUMMARY.json，未覆盖或删除。共保留 12 组正反对照（24 条路径），其中 9 组进入主结果。排除规则在复跑前记录于 PROTOCOL_AMENDMENT.md。

- [初轮模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34860716979)；[修正后 Windows 模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34864718022)
- [初轮正反对照](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34860001447)；[修正后 Windows 对照](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34864374222)
- 初轮源码：`c44f8289162ca536596e93e0c60446e21a4af5eb`；窗口修正源码：`4a06c617efc35ee39b45d54ed7d499eb4c65f301`
- 本地判分检查 32 项通过，另有 3 条 headless GUI smoke flow；这些本地检查不当作模型试验。

### 行为摘要

- **G14：三系统失败。** 60 步反复切换页面、展开政策，未输入采购数量或加购。最终订单、购物车和业务审计为空，请求仍 Open。实际观察是阅读/导航循环，不能称作算错补货数量。
- **G15：Ubuntu 通过，macOS / Windows 失败。** Ubuntu 先滚动 25 步，随后翻页、匹配正确图案，最终加购正确规格两件。macOS 60 步全部滚动，没有翻页；修正后的 Windows 先滚动 49 步，之后找到正确商品并选对规格，但在数量输入阶段耗尽预算、未加购。不能将两次失败统一归因为视觉识别错误。
- **G16：Ubuntu / Windows 错连 canonical，macOS 无提交。** Ubuntu 与修正后的 Windows 都将一个目标工单错误关联到 INC-3101，未改连更早创建的 INC-3108，也漏处理另两条目标。macOS 在选择、比较、清空选择和滚动之间循环，无业务修改。

G16 一个检查项的名称为 `all_other_records_and_metadata_unchanged`，但实际比较完整 expected 状态。未完成目标也会令其 False；本报告依据实际状态与审计描述，不把该布尔值自动解释为旁支损坏。

九次主结果均为有效模型运行，0 网关重试、0 动作解析失败、0 执行异常、0 盲操作，均非父进程超时。八次失败都耗尽 60 步且没有 done。工具未抛异常不代表各系统动作效果等价。

**Windows 滚动存在工具语义混杂。** 同版本 PyAutoGUI 源码将 dy 原样传给 Windows 原始滚轮单位，而其一格为 120；X11/macOS 使用不同的滚动单位。G15/G16 Windows 不能作为已隔离工具因素的模型能力证据。成绩保留为冻结 gui_native_v2 下的端到端结果；尚未做滚动位移探针或修正后的因果对照，详见 [工具语义核对](TOOL_SEMANTICS_REVIEW.md)。参考解可用 DOM 辅助定位/scrollIntoView，不能以其通过证明模型滚动原语等价。

参考方向为 [WorkArena++](https://arxiv.org/html/2407.05291v2) 的补货与组合工作流、[VisualWebArena](https://jykoh.com/vwa) 的图像条件购物、[WebArena](https://github.com/web-arena-x/webarena) 的多页业务操作；初始化与判分审阅参考 [OSWorld-Verified](https://xlang.ai/blog/osworld-verified)。题目数据与界面均为原创合成内容。


本批为 WorkArena++ / VisualWebArena / WebArena 启发的原创合成任务，OSWorld-Verified 用于验证方法。没有运行官方套件，不比较官方排行榜分数。详细改编见 [BENCHMARK_REFERENCES.md](BENCHMARK_REFERENCES.md)。

单次失败不证明稳定性；三系统结果不同不证明 OS 因果。旧 G08/G10 的固定配置 5/5 失败结论继续保留，新题尚无前瞻稳定性复测。同类基础控件或工作流也不自动算独立失败机制。
模型使用网关别名，未固定不可变后端版本；请求未指定 seed 或 temperature。窗口修正前后各一次也不能证明窗口是唯一原因。

Full evidence remains local. This result commit contains aggregate records only; screenshots, raw action logs and runtime archives are not republished in Git.
