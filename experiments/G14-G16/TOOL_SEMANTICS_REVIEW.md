# 冻结滚动工具的跨系统语义检查

审阅时间：2026-09-15，全部模型运行结束后。此项为源码核对，没有新增模型运行、修改成绩或进行 Windows GUI 因果对照。

本批 `gui_agent_loop.py` 把模型的 `dy` 原样传给 `pyautogui.scroll(int(dy))`。工具说明把它称作滚轮格数，并明确在当前鼠标位置滚动；动作中额外传入的 x/y 不生效。

运行环境记录 PyAutoGUI==0.9.54。核对 [PyPI 0.9.54 官方发行源包](https://pypi.org/project/PyAutoGUI/0.9.54/) 并验证发行包 SHA256 后，观察到：

| 后端 | 同一数值的实现方式 |
|---|---|
| Windows | `_scroll` 将 clicks 原样作为 dwData；`_sendMouseEvent` 不缩放，直接传给 mouse_event。 |
| X11 | 按数值绝对值重复产生 button 4/5 点击事件。 |
| macOS | 产生以 line 为单位的 Quartz 滚动事件。 |

Microsoft 的 [mouse_event 文档](https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-mouse_event)定义一格为 WHEEL_DELTA=120。因此 Windows 参数 -5 是 -5 个原始滚轮单位，不等于 -5 个完整刻度；输入单位层面相差 120 倍。这不等于网页位移必然相差 120 倍：应用处理、系统设置、滚动累计、鼠标位置等仍会影响实际效果。[PyAutoGUI 文档](https://pyautogui.readthedocs.io/en/latest/mouse.html)也说明每次滚动的实际距离会随平台而变。

本地 `diagnostics/scroll-semantics/` 保存同版本源包、三个后端源码及 SOURCE_REVIEW.json。该源码来自 PyPI；本批 runner 仅留存版本记录，没有单独存档当时已安装库文件的哈希，不能冒充运行时源码取证。

## 对本批结论的影响

- G15 / Windows 修正后先执行 49 次小幅向下 scroll；G16 / Windows 共 24 次 scroll。这些轨迹存在工具单位混杂，不能把每次重复滚动都解释为模型读不懂页面。源码发现与截图推进缓慢相符，但没有实测滚轮事件/页面位移或修正后的模型对照，尚未证明具体因果贡献。
- G14 / Windows 60 个动作均为 click，不涉及此滚动差异。G15 / macOS 有可见 Next 仍只滚动，G16 / Ubuntu 和 Windows 已实际提交错误 canonical；这些观察各自保留，不能用单个工具问题替代全部失败解释。
- 参考解允许 DOM 辅助定位和 scrollIntoView，模型只能截图加键鼠。因此 GUI 正反对照证明业务路径与判分可用，不能证明模型动作原语跨系统完全等价。
- 本批主结果按预先固定的 gui_native_v2 记录，表示“模型＋工具＋环境”在 60 步内的端到端表现。9 格有效通道结果与 8 条失败保留；G15/G16 Windows 增加 tool_semantics_confounded 标记，不能作为已隔离工具因素的模型能力证据。不增加新题或独立机制计数。
- 初轮窗口遮挡三格仍按事先登记规则排除；本次后验源码发现不冒充新的预登记条件，也不悄悄改写此前协议。

后续先做无模型的三系统滚动位移/事件探针，再明确新工具版本的单位。如果修改滚动映射或指令，须使用新版本单独复测；不得混入本批固定装置结果，也不得把修正前后分数变化直接写成 OS 因果证明。
