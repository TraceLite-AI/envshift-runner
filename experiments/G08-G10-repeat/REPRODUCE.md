# 复现同一组 GUI 试验

工作流位于 `TraceLite-AI/envshift-runner` 的 `codex/gui-repeat-20260914` 分支。
执行源码始终 checkout `c230fc6a1c2fb98a336b7154ba8d15b16e6605c0`；模型沿用仓库的 `ENVSHIFT_API_KEY`。
以下命令必须保留 tasks、oslist、trials 参数，避免使用工作流继承的其他任务默认值。

先验证参考解和实际错误交付：

```bash
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner \
  --ref codex/gui-repeat-20260914 \
  -f arm=control -f oslist='["ubuntu-24.04"]' \
  -f tasks='["G08","G10"]' -f trials='[1]'
```

确认两题均产生 oracle reward=1、wrong-result reward=0 后，运行两题各五次：

```bash
gh workflow run gui-run.yml --repo TraceLite-AI/envshift-runner \
  --ref codex/gui-repeat-20260914 \
  -f arm=agent -f oslist='["ubuntu-24.04"]' \
  -f tasks='["G08","G10"]' -f trials='[1,2,3,4,5]' \
  -f model=gemini-3.5-flash -f steps=60
```

每个矩阵 job 使用新的 runner、浏览器配置目录和业务初始状态，最多 3 个并发。
不要把旧探索结果加入这五次的分母；成功也必须保留。

GitHub 的绿色勾只表示装置正常完成。**agent 是否成功看 artifact 内 `meta.json` 的 `reward`，运行是否有效看 `valid_model_run`。**
失败轨迹因达到 60 步而正常结束时，工作流依然可以是绿色。

下载每个 `gui-repeat-...` artifact，解开其中 `evidence.tar.xz`。`evidence/` 中有：

- `meta.json`：最终业务状态、审计流水、各项判分、模型运行有效性。
- `agent/loop.json` 和 `agent/step*.png`：完整动作与每步看到的屏幕。
- `agent-final.png`：最后一次动作后的屏幕。
- `instruction.txt`：完整题面。
- `environment.json` 和 `repeat_metadata/`：软件版本、runner 镜像、源代码摘要。
- `EVIDENCE_SHA256.json`：原始文件 SHA256 清单。

环境标签与模型别名不是永久快照。后续重跑应比较运行环境记录，不能仅凭分支名相同就称条件完全相同。
