# GUI 第三批：G05–G10

六道可执行 GUI 业务流程题。模型只通过截图、鼠标和键盘操作 Chrome；业务数据全部为合成数据。沿用项目 GUI 模型 `gemini-3.5-flash`，每题每系统 60 步。

| 题号 | 任务 | 验收重点 |
|---|---|---|
| G05 | 新标签页查采购单，再对账原发票 | 正确 PO、金额、已对账状态，其他发票不变 |
| G06 | 筛选并批量分派工单 | 包含跨页全部匹配项，清除此前选中项，不误改其他工单 |
| G07 | 筛选分页费用并导出 CSV | 下载文件中所有记录和值正确，无遗漏、多选或重复 |
| G08 | 按最新活动记录更新客户资料 | 区分同名客户、最新确认信息、草稿与正式发布 |
| G09 | 拖拽指定看板卡片 | 区分近似编号，只有目标卡片的列改变 |
| G10 | 阅读可滚动规则弹窗后提交审批 | 找到适用的加急例外规则，提交正确路径与原因码 |

每道题都有 fixture、题面、真值、状态机和验收器。`task_world.py` 在控制进程中验收；预期答案和验收结果不会发送给模型。网页 API 只包含业务界面可展示的数据。模型不得使用 DOM、文件 API、终端或其他网站。

这些是待验证的跨环境 GUI 候选题，不能预先算作六条独立 OS 差异。三系统应用逻辑与数据相同，未按操作系统植入业务陷阱。运行结果必须区分成功、有效失败、通道故障与参考操作故障；一次跨系统不同结果不足以确认稳定 OS 机制。

## 运行

```sh
python check_local.py
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-batch3-20260914 -f arm=control
# 参考操作和错误操作验证完成后：
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-batch3-20260914 -f arm=agent
```

工作流安装 GUI 依赖，在 Ubuntu 24.04、macOS 15、Windows 2022 上运行。Linux 使用 Xvfb 与 Openbox，macOS 和 Windows 使用 runner 桌面。参考操作可用 DOM 定位、聚焦和滚动到元素，再通过真实键鼠操作；这不等于纯视觉 agent 的通过证据。模型开始前关闭控制进程的 CDP 连接。

## 动作接口变更

`gui_native_v2` 保留 0–1000 坐标，增加真实拖拽；滚动单位改为滚轮格数；Ctrl 始终是物理 Control，Mac Command 需明确指定。这允许 Ctrl+Tab 等原生快捷键。三系统共用这一接口，不能把本批与前批视为完全相同的 agent 接口对照。

## 证据留存

保存初始/最终截图、每步截图与动作、业务状态、审计流水、环境和浏览器版本、实际 CSV。旧 BC-G01 原始证据仍在 `badcases/`，后续成功不会删除失败记录。
