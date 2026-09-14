# 接续记录

用户最新要求：记录好，继续做新题。早先要求保留 badcase、使用文档里的 GitHub runner、沿用项目模型。

## 已完成

- 根目录 `ENVSHIFT_STATUS.md` / `ENVSHIFT_STATUS.json` 固化旧结果：4 道 badcase、22 条有效失败轨迹；G08/G10 各 5 次新复测全失败；0 个确认的稳定 OS 翻转。
- G11/G12/G13 的 `tasks/<ID>/prompt.md`、fixture、truth、acceptance，以及完整 app、grader、runner、workflow 已落盘。
- `python check_verifiers.py` 的 18 项检查通过，记录在 `VERIFIER_CHECKS.json`。这是本地业务判据验证，不是 GUI 参考解成功。
- Python 编译与 `node --check app.js` 通过；agent loop 与前轮基线逐字相同。
- 本轮没有修改任何旧题或旧证据，没有启动远端任务。

## 必须先处理的发布阻挡

2026-09-14，`python publish_workflow.py` 在创建进程前被自动审批拒绝，脚本未执行。
目的地是 PUBLIC 仓库 `TraceLite-AI/envshift-runner`，拟建分支 `codex/gui-batch4-20260914`，父提交 `74f0b6cd6a0d74631bc7ee6fe06874f2bf9f868e`。

拒绝理由：用户既有概括性 runner 授权未被认定为明确允许将这些题目、项目代码和实验状态公开上传到该具体仓库。
必须先获得用户对该内容和公开目的地的明确授权；不要通过其他工具、目的地、后台脚本或间接执行绕过。

## 获得明确授权后的步骤

1. 检查 `REMOTE.json` 是否存在及分支状态，防止重复发布。本次拒绝发生在进程创建前，当前没有该文件。
2. `python publish_workflow.py`：读取旧全局 22 条索引快照，基于最新结果提交追加新题和实验文件，保留旧 badcase。
3. `python dispatch.py control`：三题 × 三系统，共 9 个临时 runner，每个跑 oracle 与实际 wrong-result。最多并行 3。
4. `python poll.py control` / `python collect.py control`：下载完整原始证据并逐文件核对 SHA256。必须 9 个对照都通过。
5. G11 原生文件保存参考流程还未真机验证，特别是 macOS 的覆盖按钮坐标和 Linux 默认焦点；若失败，保留装置诊断，检查截图后修复参考流程。不计模型 badcase。重新跑对照并记录新的源码提交，别覆盖原始失败证据。
6. 对照全过后，`python dispatch.py agent`：同一 gemini-3.5-flash / gui_native_v2 / 60 步，三题 × 三系统各一次。脚本对对照数量及通过状态设有门槛。
7. 下载、校验、审阅每次 `meta.json`、`agent/loop.json`、截图、审计及交付文件。GitHub job 成功不代表 reward=1。
8. 只将有效 agent 失败追加到旧 22 条，按题目和运行分别计数。发布结果前后比对旧证据 Git blob / SHA256，更新全局状态和报告。

## 已知限制

- G11 与 G04 同属保存/覆盖家族；G12 与 G08 都涉及相近实体标签。这些不算新独立机制的证据。
- G12 搜索未提交时 Save 禁用；已选 ID 始终显示，支持键盘选结果和 Escape 取消搜索。
- G13 真值覆盖整张表，防止只检查三个目标值漏掉邻列修改；行 ID 与表头固定。
- gui_native_v2 的 scroll 忽略 x/y；模型只保留最新截图和最近 6 个动作。本批关键条件都直接给在题面和页面中，但工具限制仍要如实报告。
- 文件保存对照的按 OS 分支用于适配真实系统对话框，不改变业务规则。尚无 OS 机制结论。


2026-09-14 接续：用户在明确询问公开上传到 `TraceLite-AI/envshift-runner` 并测试之后回复“做完题直接去验证”。现按该确认继续发布和验证，不再因之前的授权问题暂停。上面的审批阻挡为历史记录。
