# 三道新 GUI 题与 badcase 留存

已完成 G02–G04 的题面、合成数据、判分、三系统控制及模型实测。本轮共 9 次有效模型运行，全部交付正确；新增 badcase 为 0。旧 G01 的失败单独保存，后续成功不会覆盖它。

## 保留的失败

`BC-G01-Ubuntu-file-activation` 保留了运行 34809794676 中的 Linux 失败：模型在原生文件选择框内反复操作，35 步后仍没有上传。同条件第二次运行 34810108737 用 16 步完成，故标记为单次 GUI 未完成，`stable_os_failure_proven=false`，不称作稳定翻转或静默交错文件。

证据包含失败和成功两份完整截图/动作轨迹、无模型诊断、原始判分及 SHA256 清单。完整 ZIP 已作为 Git blob 写入实验分支的 `badcases/BC-G01-Ubuntu-file-activation/evidence.zip`，不依赖 Actions artifact 的保留期限。本地重新核对了所有原证据文件的 SHA256，没有改写原始轨迹。

## 新题结果

| Task | ubuntu-24.04 | macos-15 | windows-2022 |
|---|---|---|---|
| G02 不连续多选附件 | reward=1，9 步 | reward=1，10 步 | reward=1，9 步 |
| G03 修改预约日期 | reward=1，10 步 | reward=1，10 步 | reward=1，9 步 |
| G04 替换网页快照 | reward=1，6 步 | reward=1，10 步 | reward=1，7 步 |

使用相同模型配置 `gemini-3.5-flash`、相同 45 步预算及 `gui_modifiers_v1` 工具接口。9 次运行均无接口故障、看不到图标记、动作解析错误或执行异常。人工检查了全部动作，没有终端、DevTools、代码执行或文件 API 绕过。

G02 的三份上传按固定真值逐项核对文件名、数量与原始字节哈希。G03 的实际 POST 数据逐项核对 ISO 日期、服务和参考号。G04 则读取模型实际保存到规定路径的 HTML，核对批准版标记、两条业务记录及旧版标记移除，同时核对交付物哈希与运行记录一致。三系统生成的 HTML 字节可因浏览器保存元数据而不同，判分按任务要求的内容与路径检查。

## 正误对照与排除记录

最终 9 个正确 GUI 控制全部为 1，9 个错误结果控制全部为 0。G02 的负对照实际上传多余附件；G03 实际提交错误日期；G04 实际保存了错误名称的副本，让规定路径仍是旧版。特别加强了 Linux 的 G04 负对照：必须真实生成含批准版内容的副本，不能仅因未保存任何东西而算对照通过。

开发期间的参考脚本失败都留在控制运行中，不计为模型 badcase。修正涉及日期字段自动移到下一段后的重复方向键、控件焦点响应等待、鼠标移动与点击、macOS Replace 按钮、Linux 保存格式选择。先前 Linux G04 的一次负对照没有真正产生副本，已由运行 34814974933 的实际副本对照替代。

控制器启动可能触发 macOS 的 Python 本地网络弹窗。本批在 control 与 agent 开始前，都用可见 UI 清理这个由装置引起的启动弹窗，并保存处理前截图。它不是模型题目的一部分。

多选题需要按住修饰键点击。原执行器只有即时组合键，不能完整表达 Ctrl/Command 加鼠标点击，本批增加了可选 `modifiers` 字段：三系统相同接口，macOS 将 ctrl 映射为 command，每次点击后在 finally 中释放按键。此能力在模型运行前加入；本地用隔离模拟验证了映射和异常释放，没有操控本机桌面。

## 复查来源

- [G02 / G03 六次模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34814295813)，代码 `f578175c111f44c44cab739fe49bf6e884ad6e9c`。
- [G04 三次模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34814651374)，代码 `2022c4f61301857dfc20963623052ae5e6599460`；与前一提交相比仅补充保存参考控制与失败诊断，模型工具和任务判分相同。
- [Linux / macOS 的 G02、G03 控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34813369619)。同一运行内其他失败控制已排除，逐格来源见 CONTROL_RESULTS.json。
- [Windows 三题最终控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34814048973)。
- [macOS G04 最终控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34814058185)。
- [Linux G04 最终正误控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34814974933)。

这是 3 道任务、每系统各一次模型实测。G02 和 G01 共享原生文件选择框这一任务家族；尚未证明 3 条独立 OS 机制。GitHub 的系统、架构、浏览器和桌面实现也不是单因素控制，不能把运行差异直接归因于 OS 内核。
