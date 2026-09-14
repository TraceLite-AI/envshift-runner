# 接续记录

用户要求从 16 道补齐 20 道，新题 G17–G20，出完直接 GitHub runner 验证，沿用现有模型、最多 3 并发。旧 7 题 / 30 条失败及工具混杂标记保留，不回溯改分。

顺序：判分边界检查 → headless UI smoke → 发布合成源码/计划 → dispatch control → 12 格含滚动探针的正反对照全部通过 → dispatch agent → 收集审阅 → 汇总发布和本地 ZIP。模型每格一次，共 12 次，未测完前不报新 badcase。

v3 仅修 Windows 纵向滚轮参数并更新标签。完整新证据永久公开曾被自动审批拒绝，只存本地，不绕过。合成题、汇总与 runner 运行已有用户授权，不重复询问。已有 RUN 或 DISPATCH_PENDING 时先核对，不重复派发。最后更新 REPORT/VIEWER/badcases/ZIP 和全局 ENVSHIFT_STATUS；下一批从 G21 开始。
