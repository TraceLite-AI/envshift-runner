# G17–G20 参考与边界

查阅日期 2026-09-15。采用公开 benchmark 的任务方向，自编数据、界面与判据；不运行或复制官方套件，不比较排行榜。

| 题目 | 一手来源 | 实际改编与限制 |
|---|---|---|
| G17 | [WindowsAgentArena](https://microsoft.github.io/WindowsAgentArena/)、[OSWorld](https://os-world.github.io/) 的办公任务 | 合成表格支持公式、填充、格式和保存；扰动输入验重算。不是原生 Calc。 |
| G18 | [MiniWoB++](https://miniwob.farama.org/environments/list/) 的 daily-calendar、choose-date、enter-time；[AndroidWorld](https://github.com/google-research/android_world) 日常应用方向 | 组合成周期事件的一次例外。未运行 Android，不声称来源有完全相同的周期任务。 |
| G19 | [OSWorld](https://os-world.github.io/) 办公方向；[MiniWoB++](https://miniwob.farama.org/environments/list/) 的 drag-sort-numbers、drag-items | 扩展为带内容、隐藏状态、备注的已保存幻灯片。拖动/移动按钮均可，不是 Impress。 |
| G20 | [WindowsAgentArena](https://microsoft.github.io/WindowsAgentArena/) 文件管理方向；[MiniWoB++](https://miniwob.farama.org/environments/list/) 的 navigate-tree | 导航、预览审批状态与版本日期、复制并保留源文件。是合成文件管理器，不是 Explorer 或云盘。 |

新题与旧题仍共享表格、输入框、选择、排序等基础控件，不因交付流程变长就称作新的独立失败机制。初始化与验收参考 [OSWorld-Verified](https://xlang.ai/blog/osworld-verified)；本批另测滚动事件，不把参考路径通过等同工具原语完全一致。
