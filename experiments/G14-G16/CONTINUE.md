# 接续记录

当前批 G14–G16，题目参考见 BENCHMARK_REFERENCES.md，固定测试计划见 TEST_PLAN.md。
用户要求出完直接用 GitHub runner 验证，沿用现有模型，保留全部旧 badcase；无需再次询问普通题目发布与运行。
完整截图/日志/环境的永久公开 Git 上传曾被自动审批拒绝；仅公开源码和汇总记录，完整证据保留本地。
执行顺序：check_verifiers.py → local_preview.py → publish_workflow.py → dispatch.py control → watch.py control → 九格对照均通过后 dispatch.py agent → watch.py agent → 审阅和归档。
不得重跑已有 *_RUN.json 的 dispatch；先读记录和 GitHub 确认已有运行。模型循环不得改动。
