# G08 / G10 GUI 固定配置复测

沿用原版 agent，在 Ubuntu 上每题新增 5 次独立运行，每次使用干净的 GitHub runner。
模型为 gemini-3.5-flash，60 步，gui_native_v2；不启用 notebook，不改变题面、工具说明或判据。
执行源码固定在 c230fc6a1c2fb98a336b7154ba8d15b16e6605c0。

先重跑两题的 oracle / wrong-result 对照，要求正确状态通过、实际产生的错误状态被拒绝。
先前探索样本单独保留，不混入新增 5 次的分母；有效失败不会被替换。
记录每次的软件版本、源码 SHA256、全部截图、动作、最终业务状态和判分。
本轮只检验固定配置下是否反复失败，不声称跨操作系统翻转或无限次必败。
网关后端和模型别名无法冻结；请求仍不显式指定温度或随机种子，与原版一致。

查看结果：[报告](REPORT.md)、[逐次行为分析](OBSERVATIONS.md)、[复现命令](REPRODUCE.md)。

本地证据包解压后，直接用浏览器打开 `VIEWER.html`，可逐步查看截图、动作、最终业务状态。
从 GitHub 检出本目录时，先在目录内运行 `python3 unpack_archives.py` 恢复原始截图，再打开 `VIEWER.html`。解压与查看不调用模型。
