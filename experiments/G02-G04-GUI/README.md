# EnvShift GUI 第二批：G02–G04

保留了上一轮 G01 Linux badcase，并新增三道可以在真实桌面上复跑的 GUI 任务。本轮三题 × 三系统的 9 次模型运行全部正确交付，没有新增模型 badcase。

| 题目 | 实际验收 | Linux | macOS | Windows |
|---|---|---|---|---|
| G02 不连续多选账单附件 | 恰好三份文件，原始字节正确 | 通过，9 步 | 通过，10 步 | 通过，9 步 |
| G03 修改跨月预约日期 | 日期、服务等级和参考号全部正确 | 通过，10 步 | 通过，10 步 | 通过，9 步 |
| G04 保存并替换批准版网页 | 规定路径内的旧文件被新版内容替换 | 通过，6 步 | 通过，10 步 | 通过，7 步 |

模型配置为 `gemini-3.5-flash`；每次预算 45 步，步数包含 done。每个任务/系统只运行一次，不能据此估计稳定成功率。三道任务尚未证明独立的 OS 失真机制。

文件入口：

- `tasks/G02`、`tasks/G03`、`tasks/G04`：题面、固定业务真值、判分与错误控制说明。
- `gui_batch2.py`：合成页面、数据、独立判分及真实 GUI 控制。
- `gui_agent_loop.py`：截图、鼠标、键盘执行器，统一归一化坐标，支持修饰键点击。
- `AGENT_RESULTS.json`、`CONTROL_RESULTS.json`、`EXPERIMENT.json`：结果、运行编号和代码版本。
- `agent-first/`、`agent-save/`：本地完整模型截图、动作轨迹和交付物。
- `badcases/INDEX.json`：badcase 索引；`badcases/BC-G01-Ubuntu-file-activation.zip` 是完整旧失败证据包。
- `REPORT.md`：实验边界、控制校准与证据来源。

在已有 GitHub runner 仓库复跑：

```bash
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-batch2-20260914 -f arm=control -f 'tasks=["G02","G03","G04"]'
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-batch2-20260914 -f arm=agent -f 'tasks=["G02","G03","G04"]' -f model=gemini-3.5-flash -f steps=45
```

模型调用沿用仓库已有 secret。所有业务页面与文件都是合成内容。脚本会创建测试工作目录并操作 Chrome，应在专用 runner 上执行。本轮没有操作用户本机桌面。
