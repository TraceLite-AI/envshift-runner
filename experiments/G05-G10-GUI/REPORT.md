# G05–G10 GUI 实测报告

新增 **6 道可执行 GUI 题**。三系统参考操作 **18/18 通过**，实际错误操作 **18/18 被拦住**。基线模型 **9/18 交付正确**，保留 **9 条有效失败轨迹**。另做 3 次自写笔记诊断，单独统计。

这些是合成业务网页上的真实键鼠任务。已确认的新增独立 OS 失败机制仍为 **0**；失败样本数量不等于机制数量，单次结果或步数差异不足以确认 OS 因果。

## 六道题与基线成绩

每格为“验收结果 / 消耗步数”。成功按真实交付物和后台业务状态判断；用满预算但已交付正确结果仍算通过。

| 题号 | 内容 | Linux | macOS | Windows |
|---|---|---|---|---|
| G05 | 跨标签页对账 | 未完成 / 60 | 未完成 / 60 | 未完成 / 60 |
| G06 | 筛选后批量分派 | 通过 / 20 | 通过 / 22 | 通过 / 24 |
| G07 | 跨页 CSV 导出 | 通过 / 9 | 通过 / 60 | 通过 / 10 |
| G08 | 客户资料正式发布 | 未完成 / 60 | 未完成 / 60 | 未完成 / 60 |
| G09 | 拖拽指定看板卡片 | 通过 / 3 | 通过 / 2 | 通过 / 2 |
| G10 | 阅读规则弹窗后审批 | 未完成 / 60 | 未完成 / 60 | 未完成 / 60 |

G05 检查发票金额、PO 与对账状态；G06 逐条检查目标工单和非目标工单；G07 读取实际下载的 CSV 并核对记录和值；G08 检查正式资料及同名客户是否被误改；G09 检查指定卡片与其他卡片的全部字段；G10 检查规则确认、审批路径和原因码。网页“成功”提示不能代替这些检查。

本批共保留 11 条新失败轨迹：基线 9 条，加上笔记诊断的 2 条；另有原 G01 失败证据。它们均是预算耗尽未提交最终业务结果，不是已证明的静默错误交付。

## 失败证据与共同短板

G05 的 Linux 轨迹反复切换标签页、打开重复采购单页，没有输入对账数据。G08 打开编辑页后反复尝试浏览器 Back；网页内部切换没有新增浏览历史，没有草稿或发布操作。G10 在规则阅读和滚动之间反复操作，Linux 只确认了规则，没有提交审批。各系统具体动作见原始轨迹，不能仅凭相同题号认定同一个底层原因。

基线循环每次只提供最新截图和最近 6 次动作，不保留历史截图内容，也没有显式笔记。跨页事实容易在切换后丢失。G10 另有模型自行添加 scroll.x/y 的行为，但 v2 协议只支持在当前鼠标位置滚动；这些额外字段被忽略。笔记诊断保持滚动行为不变。

G07 的 Mac 运行虽然耗尽 60 步，但确实下载了正确 CSV，审计记录显示重复导出和反复查看下载记录。按既定交付验收通过，另记录效率与停止判断问题，不事后改判失败。

## 单独的自写笔记诊断

模型、业务页面、键鼠执行与 60 步预算保持一致，只给动作增加可选 memory 字段并在后续调用保留。笔记由模型从截图自行读取和总结，执行器不读取 DOM 或后台答案。只在 Linux 上复测三道失败题，成绩不混入上面的 18 格。

| 题号 | 基线 Linux | 自写笔记 |
|---|---|---|
| G05 | 0 / 60 步 | 1 / 21 步 |
| G08 | 0 / 60 步 | 0 / 60 步 |
| G10 | 0 / 60 步 | 0 / 60 步 |

加入笔记后恢复的题目：G05。这一结果用于检查 agent 上下文设计，不是 OS 归因实验。每格只有一次运行，提示变化和模型运行随机性尚未单独隔离，不能据此估计稳定成功率。

诊断使用情况也不同：G08 全程未写 memory，最终笔记为空，因此这不是“正确使用笔记之后仍失败”的对照。G10 第 26 步记下 Manager 和 EXP-7，第 27 步却用“Select Approval route: Manager”覆盖了笔记，丢失原因码，随后又陷入滚动。提供记忆字段与实际正确使用记忆是两回事。

## 条件、对照与限制

- 基线模型：项目既有 GUI 模型 gemini-3.5-flash；每格 60 步；总模型并发不超过 3。
- 基线提交：`c230fc6a1c2fb98a336b7154ba8d15b16e6605c0`；自写笔记提交：`08a52edc8bf58c286c4a6e51977ce65037c7cf39`。
- 三系统共用相同应用和 fixture，未按 OS 更改业务规则、locale、数据库配置或正确答案。
- Linux 为 x86_64、1280×900、Chrome 152.0.7977.82；Mac 为 arm64、1024×768、Chrome 152.0.7977.83；Windows 为 AMD64、1024×768、Chrome 152.0.7977.83。OS、架构、视口和浏览器小版本并未单独控制。
- 参考操作可用 DOM 聚焦、scrollIntoView 和几何定位，再用真实键鼠执行；模型只能看截图与操作键鼠。参考通过证明任务可操作，不等于模型通过。
- v2 相比前批增加拖拽、改用原生 Ctrl/Command、把滚动单位改为滚轮格数。前批与本批不能当作完全相同 agent 接口的连续对照。
- API 通道故障、盲图、进程超时应单独标无效；本表只收有效运行。GitHub artifact 下载重试属于事后证据传输，不计入模型成绩。

## 重跑与取证

正反对照：[GitHub run 34817662654](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34817662654)。Linux/Mac 基线：[run 34818197573](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34818197573)。

Windows 基线：[G05](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820054650)，[G06](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820164471)，[G07](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820222541)，[G08](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820390662)，[G09](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820569777)，[G10](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820695089)。

Linux 笔记诊断：[G05](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34820793201)，[G08](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34821097368)，[G10](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34821164564)。

完整题面、fixture、验收意图在 `tasks/`；基线和诊断摘要在 `AGENT_RESULTS.json`、`NOTEBOOK_RESULTS.json`；正反对照在 `CONTROL_RESULTS.json`；完整截图与轨迹在本地包和 GitHub artifacts。有效失败另存为无损压缩的 `badcases/<id>.tar.xz`，并以 `badcases/<id>/evidence.tar.xz` 永久提交 Git 仓库，带逐文件 SHA256 清单。原有 `BC-G01-Ubuntu-file-activation` 证据未删除或替换。

`NEXT_CANDIDATES.md` 另列 20 个后续设计方向，尚未实测，不计入本批 6 道完成题数。
