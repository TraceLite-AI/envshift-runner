# EnvShift GUI 第四批：G11–G13

2026-09-14 新题。状态：已实现，18 项本地判据检查及 Python/JavaScript 语法检查通过，等待三系统 GUI 对照；尚无模型结果，不计入 badcase。

本轮向公共仓库发布时被自动审批拒绝，远端尚未创建分支或启动任务。继续操作与授权条件见 `CONTINUE.md`。

| 题号 | 任务 | 关键验收 | 与旧题的关系 |
|---|---|---|---|
| G11 | 导出批准版 CSV，在原生保存框替换 Downloads 中旧文件 | 目标路径实际字节、八月文件未变、没有副本 | 与 G04 同属保存/覆盖家族；执行路径为 File System Access picker，不算独立机制 |
| G12 | 可搜索供应商框选择 VEN-1048，保存 PO-918 | 实际 vendor_id 和所有需保持字段 | 与 G08 都有实体歧义；这里题面给出精确 ID，测搜索输入到实际选中，不依赖跨页面记忆 |
| G13 | 横向滚动库存表，修改三行 Reorder level | 全表比对，邻列 Reorder quantity 和其他单元格保持 | 新增宽表格定位与编辑工作流，不预设 OS 差异 |

题面直接包含目标值，界面也保留可见目标。使用同一 gemini-3.5-flash、原始 gui_native_v2（SHA256 `8d4e7f7d85cec5a3f4a947483a1bc80403e206341bb56b9391c7d6fafe228580`）、60 步、最新截图和最近 6 个动作；三系统最多同时 3 个模型任务。

`tasks/G11`、`tasks/G12`、`tasks/G13` 包含题面、初始数据、业务真值和验收说明。`task_world.py` 是独立判据与状态转换；`app.js`/`app.css` 是界面；`gui_batch4.py` 是参考控制和实跑入口。

参考控制允许 DOM focus/scrollIntoView/坐标辅助，实际输入走原生键鼠。模型只看到截图并使用原生键鼠。G11 的操作系统保存框由 Chrome 和系统生成；业务规则不按 OS 分支。先要求每题三系统 oracle 成功、实际错误交付被拒，再运行模型。参考失败属于装置待修复，不计模型失败。

G12 搜索文字未提交时 Save 禁用，页面显示已选实体。选择结果或 Escape 恢复后才能保存；不会把搜索文字冒充已选择的供应商。G13 保留固定行 ID 和表头，允许拖动横向滚动条；当前 agent 的 scroll 动作忽略 x/y，诊断须考虑这一工具限制。

G11 使用立即响应用户操作的 `showSaveFilePicker`，随后才生成写入流；依据 [Chrome File System Access 文档](https://developer.chrome.com/docs/capabilities/web-apis/file-system-access)。是否能在三系统完成，以真实 runner 对照为准。

仅使用 GitHub 临时 runner 的合成文件。此脚本会操作桌面，不要直接在日常桌面运行参考键鼠控制。


2026-09-14 接续：用户在明确询问公开上传到 `TraceLite-AI/envshift-runner` 并测试之后回复“做完题直接去验证”。现按该确认继续发布和验证，不再因之前的授权问题暂停。上面的审批阻挡为历史记录。
