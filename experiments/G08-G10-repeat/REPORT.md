# G08 / G10 GUI 固定配置复测

状态：已完成；以下仅统计本轮预先指定的新增试验。

| 题目 | 有效次数 | 成功 | 失败 | 无效运行 |
|---|---:|---:|---:|---:|
| G08 | 5 | 0 | 5 | 0 |
| G10 | 5 | 0 | 5 | 0 |

每题 5 次从干净 GitHub Ubuntu runner 启动。gemini-3.5-flash，60 步，gui_native_v2；无 notebook。
本轮新增 10 条失败轨迹；连同此前累计 22 条，仍对应 4 道不同的 badcase 题目。复测次数不计为新题。
原版任务、提示词、鼠标键盘工具、截图处理、判据及模型请求均未改动。历史只提供最新截图和最近 6 个动作。
前置对照：G08、G10 的参考解全部通过，实际生成的错误业务状态全部被拒绝。参考解用 DOM 辅助定位与滚动，再执行物理键鼠；模型只看截图。

## 配置与判读边界

- 源码提交：`c230fc6a1c2fb98a336b7154ba8d15b16e6605c0`。
- 全部模型试验及对照的已记录运行环境是否一致：True。
- 每次保存并核对源码 SHA256、runner 镜像、Python、pip 包、Chrome 与屏幕尺寸。
- 模型仍使用网关别名；后端权重、默认采样参数和服务端调度无法冻结。源码固定不等于后端模型快照固定。
- 新 runner 使用全新 Chrome 配置目录；本地站点随机端口沿用原装置，因此不声称初始截图逐像素相同。业务数据和起始页面逻辑相同。
- 0/5 表示本轮五次均失败，不能推断无限次必败，也不能证明换操作系统导致失败。
- 这两个任务经先前失败样本筛选，属于候选题的前瞻复测，不是随机抽取任务的总体成功率估计。
- 旧基线与 notebook 诊断保留在上一批报告中，不混入本轮分母。

## 逐次结果

| 题目 | 次数 | reward | 步数 | 结果类型 | 业务写入次数 | 连续相同截图最长段 |
|---|---:|---:|---:|---|---:|---:|
| G08 | 1 | 0 | 60 | step_budget_exhausted | 0 | 32 |
| G08 | 2 | 0 | 60 | step_budget_exhausted | 0 | 21 |
| G08 | 3 | 0 | 60 | step_budget_exhausted | 1 | 31 |
| G08 | 4 | 0 | 60 | step_budget_exhausted | 1 | 21 |
| G08 | 5 | 0 | 60 | step_budget_exhausted | 0 | 31 |
| G10 | 1 | 0 | 60 | step_budget_exhausted | 4 | 13 |
| G10 | 2 | 0 | 60 | step_budget_exhausted | 5 | 13 |
| G10 | 3 | 0 | 60 | step_budget_exhausted | 4 | 16 |
| G10 | 4 | 0 | 60 | step_budget_exhausted | 4 | 16 |
| G10 | 5 | 0 | 60 | step_budget_exhausted | 5 | 14 |

[行为复查](OBSERVATIONS.md)解释关键截图与操作循环；[复现命令](REPRODUCE.md)给出完整运行方式。
截图相同是停滞线索，不能单独证明认知原因。动作明细、判分与业务审计见 `TRIAL_ANALYSIS.json`，每条原始证据见 `AGENT_RESULTS.json` 的 archive 字段。
GitHub Actions 的 success 表示装置正常完成；模型成绩以 meta.json 的 reward 为准。
全部成功、失败以及对照均保留，压缩包内部的 EVIDENCE_SHA256.json 可逐文件校验。
全部有效失败另登记在 badcases/INDEX.json；一次失败轨迹不等于一道新题。
