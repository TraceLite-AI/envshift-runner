# EnvShift GUI 第六批：G17–G20

四道原创合成浏览器 GUI 题。出题完成不等于模型验证完成，最终成绩以 REPORT.md 为准。

| 题号 | 任务 | 题面 |
|---|---|---|
| G17 | 实时表格公式、格式与保存 | [prompt.md](tasks/G17/prompt.md) |
| G18 | 周期事件的单次例外 | [prompt.md](tasks/G18/prompt.md) |
| G19 | 幻灯片排序、隐藏与备注 | [prompt.md](tasks/G19/prompt.md) |
| G20 | 已批准版本筛选和复制交付 | [prompt.md](tasks/G20/prompt.md) |

来源见 [BENCHMARK_REFERENCES.md](BENCHMARK_REFERENCES.md)，计划见 [TEST_PLAN.md](TEST_PLAN.md)。用 `python3 serve.py --task G17 --out manual.json` 本地审题，Ctrl+C 保存判分，人工试玩不计模型结果。

沿用 gemini-3.5-flash，当前截图＋最近六条动作，60 步、最多三个模型并发。gui_native_v3_scroll 仅调整 Windows 纵向滚轮单位；先三系统无模型探针和正反 GUI 对照，通过后才启动模型。旧 7 个 badcase 题目 / 30 条端到端失败轨迹保留，旧工具混杂标记不改。完整新证据仅本地保存，公开 Git 发布合成源码和汇总。
