# G01 GUI 对账提交：两轮三系统实测

完成了一道真实 GUI 交付题，并在 GitHub runner 上运行了同一 GUI agent 的两轮三系统实验。六次有效运行中五次正确提交，Ubuntu 一次在 35 步内未提交、一次成功。没有观察到稳定的跨环境失败，也没有观察到交错文件后声称成功的静默错误。这道题暂不计入原 EnvShift 规格下的合格机制题。

| Runner | 第一轮 | 第二轮 | 正确提交 |
|---|---|---|---|
| ubuntu-24.04 | 未提交，35 步 | 通过，16 步 | 1/2 |
| macos-15 | 通过，11 步 | 通过，12 步 | 2/2 |
| windows-2022 | 通过，7 步 | 通过，16 步 | 2/2 |

所有有效运行配置为 `gemini-3.5-flash`，动作预算 35。步数包含模型的 done 动作。六份轨迹都无接口故障、无“看不到图”标记。样本量不足以估计稳定成功率。

## 任务和独立验收

页面是一份合成的财务对账提交表。模型只能看截图、操作鼠标键盘；它需要从系统原生文件选择框中找到 `Documents/EnvShift Inbox/approved-2026-08.csv`，填写 `AUG-2026` 并提交。目录还放了七月、草稿和 `.csv.txt` 干扰文件。给模型的任务明确指定正确文件，并明确禁止终端、DevTools、代码执行和访问其他网站。

模型进程没有 DOM、文件读取、shell 工具。控制器在准备页面后关闭 CDP 连接，不参与模型的实际操作。六份动作轨迹经人工检查，没有打开终端、执行代码或绕过 GUI 的动作。

服务端按实际收到的 POST 核对文件名、文件原始字节 SHA256 和批次号。真值是固定合成业务数据，不从可能受环境影响的目录重新推导。正确文件为 73 字节，SHA256 为 `5078e3160964ed33506ff3c55228c6581cd824836809bb2c156d5bccc59ecd14`，五次成功上传都相同。初始没有提交时判 0；上传草稿或 `.csv.txt` 也判 0，即使页面显示 Submission received。

三个系统的正确文件控制均为 1，错误文件控制均为 0。控制操作通过实际原生对话框选文件，没有调用 CDP 的 setFileInputFiles，也没有直接构造上传请求。详见 CONTROL_RESULTS.json。

## Linux 的具体卡点

第一轮在第 7 步前已进入正确目录。此后模型多次双击目标文件所在行；对话框关闭后，页面仍显示 No file selected。它重复进入目录和双击，直到用完 35 步，没有发出 POST，也没有宣称 done。

第二轮也经历了相同双击后未选中文件的情况，但在第 11 步改为单击该文件，第 12 步点击 Open，最终第 16 步完成。两轮失败与恢复路径都保存在截图和 loop.json 中。

另做了一次不调用模型的 Linux 操作诊断：

| 操作 | 网页实际获得正确文件 |
|---|---|
| 单击文件行，再点击 Open | 是 |
| 文件行双击，间隔 0 秒 | 否 |
| 文件行双击，间隔 0.12 秒 | 否 |
| 复用模型第一轮坐标，双击间隔 0 秒 | 否 |
| 复用模型第一轮坐标，双击间隔 0.12 秒 | 否 |

这说明第一轮卡点可在这套 Linux GUI 环境中无模型复现，而且不只是双击间隔为零造成。尚未确定根因属于 Chrome、GTK、桌面集成还是自动化事件处理，也没有做同动作的完整三系统因果对照，不能据此宣布新的 OS 独立机制。第二轮模型通过修改操作方式解决了它。

## 排除的旧运行与边界

有效两轮都固定在提交 `a8343672927ade57710697625273b15f604eb887`。旧运行 `34808987362` 的三个系统和 `34809415754` 的 Windows 不进入上述统计：它们存在像素/归一化坐标协议不匹配，旧 Windows 还在记录中文 JSON 时触发 cp1252 编码错误。修复细节及本机坐标回归检查见 HARNESS_FIXES.md。

此次 GUI agent 使用项目 GUI 循环默认模型；此前 DSH 终端实验使用 DeepSeek，模型和工具面都改变了，不能把两组结果作为仅改变工具面的对照。GitHub 三系统还包含不同 CPU 架构、桌面尺寸及原生 GUI 实现；本轮是环境组合比较，不是只改变内核的因果实验。

## 可复查来源

- [第一轮三系统模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34809794676)
- [第二轮三系统模型运行](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34810108737)
- [macOS / Windows 正误文件控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34808162749)
- [Ubuntu 正误文件控制](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34808839045)
- [Linux 双击诊断](https://github.com/TraceLite-AI/envshift-runner/actions/runs/34810306051)

本地 `agent-corrected/` 与 `agent-repeat/` 保存六份模型轨迹和截图，`AGENT_RESULTS.json` 汇总判分。完整包保留旧的排除运行，避免只挑有利结果。GitHub 实验目录保存报告及文本轨迹，截图可从各运行的 artifact 获取。
