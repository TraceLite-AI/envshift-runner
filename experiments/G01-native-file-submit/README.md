# G01：通过原生文件选择框提交对账资料

已完成两轮三系统 GUI agent 实测：Windows 2/2、macOS 2/2、Ubuntu 1/2 正确提交。尚无稳定的跨环境失败；详见 [REPORT.md](REPORT.md)。

任务：在 Chrome 合成业务页面选择已批准的八月 CSV，填写批次号并提交。全部网页和数据均为合成内容，服务仅监听 runner 本机。模型只有截图、鼠标、键盘动作，不提供 shell、DOM、文件读取。

文件：

- `gui_submit_task.py`：物化合成数据、页面、独立上传判据、正误文件控制和 Linux 双击诊断。
- `gui_agent_loop.py`：模型 GUI 执行器，归一化坐标、UTF-8 轨迹记录。
- `gui-run.yml`：GitHub 三系统工作流，部署位置为 `.github/workflows/gui-run.yml`。
- `AGENT_RESULTS.json`、`CONTROL_RESULTS.json`：模型与控制判分。
- `EXPERIMENT.json`：模型、预算、固定提交、运行编号和排除原因。
- `HARNESS_FIXES.md`：执行器问题及排除依据。
- `agent-corrected/`、`agent-repeat/`：实际六次运行的截图和动作轨迹。

在已授权 runner 仓库复跑（使用已有 GitHub secret，不需将密钥写进代码）：

```bash
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-native-submit-20260914 -f arm=control
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner --ref codex/gui-native-submit-20260914 -f arm=agent -f model=gemini-3.5-flash -f steps=35
```

本地汇总已下载结果：

```bash
python3 analyze.py --run 34809794676:agent-corrected --run 34810108737:agent-repeat
```

`gui_submit_task.py` 会启动 Chrome、创建合成工作目录并操作桌面，请放在专用测试 runner 上运行。本轮没有操作用户本机桌面。
