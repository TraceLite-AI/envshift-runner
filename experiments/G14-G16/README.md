# EnvShift GUI 第五批：G14–G16

三道自行编写的 GUI 工作流，参考 WorkArena++、VisualWebArena、WebArena，并采用 OSWorld-Verified 的初始化与验收经验。出处与实际改编见 [BENCHMARK_REFERENCES.md](BENCHMARK_REFERENCES.md)。

| 题号 | 题目 | 题面 |
|---|---|---|
| G14 | 库存补货、下单、关闭申请 | [prompt.md](tasks/G14/prompt.md) |
| G15 | 看图选商品、配置规格、维护购物车 | [prompt.md](tasks/G15/prompt.md) |
| G16 | 多字段核对和工单去重关联 | [prompt.md](tasks/G16/prompt.md) |

本批初始计划是 3 题 × 3 系统的 9 次模型运行。先执行每格 GUI oracle 与真实错误交付对照；任何对照失败先修装置，不能计作模型 badcase。模型沿用 gemini-3.5-flash / gui_native_v2 / 60 步，最多 3 个并发。

旧批累计 4 个 badcase 题目、22 条有效失败轨迹全部保留。新题是否失败、是否稳定、是否为 OS 差异，分别记录，未经验证不下结论。

源码与汇总实验记录可公开；完整截图、日志、环境记录保存在本地归档，不新增永久公开的完整证据上传。

本地路径：`/Users/conglin/Downloads/cl实验/EnvShift-GUI第五批-20260914/tasks/`
