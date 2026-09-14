# G21–G25 参考与范围

查阅日期：2026-09-15。参考的是公开 benchmark 的任务方向与验收方式；五题的业务数据、网页界面与判据均在本地自行实现，不是官方原题复刻，也不报告官方 benchmark 分数。

| 题目 | 参考方向 | 本题新增操作与验收重点 |
|---|---|---|
| G21 邮件规则 | [MiniWoB++ 环境目录](https://miniwob.farama.org/environments/list/) 的邮箱、表单与选择操作 | 保存复合过滤条件，并实际处理匹配邮件；同时检查未来匹配语义 |
| G22 文档修订 | [OSWorld](https://os-world.github.io/) 的办公文档操作 | 逐项接受/拒绝修订，检查保存的正文、修订状态与评论锚点 |
| G23 图片导出 | [OSWorld](https://os-world.github.io/) 与 [Windows Agent Arena](https://microsoft.github.io/WindowsAgentArena/) 的图像编辑方向 | 原图坐标裁切、方向旋转、PNG 文件导出；独立坐标映射核对像素 |
| G24 统计图表 | [WorkArena](https://github.com/ServiceNow/WorkArena) 的企业知识工作、表单与仪表板方向 | 过滤、分组、SUM 聚合、排序与保存查询；扰动数据重算 |
| G25 权限继承 | WorkArena 的企业 GUI 工作流方向（泛方向参考） | 自行设计权限继承任务；区分父目录与单个文档、同名人员、角色与公开链接 |

G25 不声称来自 WorkArena 的某道同名官方权限题。各任务使用合成邮件、文档、图像与账号；没有接入真实邮箱、云盘或权限系统。

这五题首先是 GUI 候选任务。未实测前不预设哪一 OS 失败，也不把全系统失败或人为不同配置称为 OS 差异。正式比较继续使用同一模型、同一工具版本、相同题面与初始数据。
