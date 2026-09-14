# 非 coding 交付题：首轮实测结果

2026-09-14。本轮新增两道文件交付任务，交付物为部门汇总 CSV 与凭证 ZIP，不要求修改/交付代码。沿用前轮 DSH + deepseek-v4.1-flash。

**结果：控制组 12 格符合预期，但真实 agent 6/6 满分。没有发现 agent 跨环境失败。**

| 题目/流程 | Ubuntu 24.04 | macOS 15 | Windows 2022 |
|---|---:|---:|---:|
| NC01 Unicode / oracle | 110 | 110 | 110 |
| NC01 Unicode / naive | 110 | 30 | 110 |
| NC01 Unicode / agent | 110 | 110 | 110 |
| NC02 尾随点 / oracle | 110 | 110 | 110 |
| NC02 尾随点 / naive | 110 | 110 | 30 |
| NC02 尾随点 / agent | 110 | 110 | 110 |

满分 110，reward 全或无。控制流程正常结束，目标环境朴素流程少交两份凭证并算错金额，因而失分。相同凭证集合经相同解包流程，在目标环境得到 70 份文件，其他环境 72 份。逐份比对已通过字节完整性验收的交付物，确认每题全部 72 份原件的 SHA256 在三系统完全一致。

输入控制边界：原始 ZIP 的整包 SHA256 在 Windows 与另两台不同；Python ZipInfo 默认按宿主填写 create_system=0/3，fixture 未固定该容器元数据。本轮不宣称原包逐字节相同。全部凭证的内容字节、业务字段及命名规则一致，但更严格的后续版本应预先固定 ZIP 创建系统字段并重新验证，不能把本轮追记成该新版本的实验。

## 真实 agent 的行为

六次都有实际工具调用，正常完成；不是用参考流程冒充 agent。macOS 的 NC01 运行发现原始 ZIP 有 72 项而 received/ 只有 70 份，直接从 ZIP 读取凭证，以业务 ID 命名交付，避开了 Unicode 路径合并。Windows 的 NC02 同样从原包整理，提交了完整 72 份。其他格也均完成金额、文件集合、字节完整性验收。

这个结果只说明这两道题在当前模型与工具面、每格一次的实验中没有诱发失败。不能推广成“非 coding 题都不会失败”。两题属于 M1/M5 的新 ZIP 执行路径，不计为新独立机制。

## 与上一轮的区别和剩余问题

上一轮让 agent 修改继承来的代码，这轮让它处理已经接收的业务资料并提交最终文件。变化确实落到了工作流程，但工具仍允许终端和临时脚本；模型可以直接读取无损原包，完全避开宿主解包路径。当前规模和显式原始来件范围也使核对成本很低。

不应通过删除合理的业务范围、隐藏必要的恢复材料或修改评分标准来强造失败。两题应退出“已发现 agent 失败”列表，保留为完整性检查的控制任务。

更有依据的后续方向是：测试必须与真实应用交互的任务，并把终端工具面与截图/鼠标键盘工具面分开。可先做原生文件对话框中的另存为/上传、浏览器设置持久化、办公应用打印导出。每个方向仍需初始状态与参考操作三系统验证；这些是待出题方向，不是本轮已完成或已实测题目。项目已有 gui_agent_loop.py 可以复用；它的默认模型是 gemini-3.5-flash，换到该通道会同时涉及模型/装置控制，不能直接与本轮分数作单因素比较。

## 可复查证据

实验代码提交：00c8dc654cb85434ecf341677fa41b206d9e0ee1。

控制组：
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802773263
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802775682
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802777952

真实 agent：
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802918362
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802920538
- https://github.com/TraceLite-AI/envshift-runner/actions/runs/34802922396

本地 artifacts/ 包含六次轨迹、最终回复、CSV 与 ZIP 交付物、逐项判分；evidence/ 包含原始门一日志和结构化结果。所有输入是本轮合成数据，无用户真实凭证。判据只用物化时私有流水计算预期，不从 received/ 倒推真值。agent 开始前删除磁盘题库、判据及 Git 历史；评分时恢复私有流水。工具轨迹保留供复查，不把该处理宣称为硬安全沙箱。
