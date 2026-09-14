# EnvShift 当前记录

更新时间：2026-09-14。本文件是继续工作的入口，题目数、失败轨迹数、固定配置复测与 OS 翻转必须分别计数。

## 已确认的结果

- 不同 badcase 题目：4 道（G01、G05、G08、G10）。
- 失败轨迹：22 条（G01 1 条；G05 3 条；G08 9 条；G10 9 条）。
- 完成本轮固定配置各 5 次、且全部失败：2 道（G08、G10）。
- 已证实的稳定跨 OS 成功／失败翻转：0 道。
- 旧 badcase 必须保留，即使后续恢复成功。重复运行不算新题，同家族题不算独立机制。

固定配置复测使用 gemini-3.5-flash、gui_native_v2、Ubuntu、每轮 60 步；仅最新截图和最近 6 个动作，无 notebook。
G08 / G10 新增 10 次运行全部有效，没有通道重试、动作执行异常或动作解析失败。
两题参考解通过，实际错误交付被判据拒绝。截图、动作、业务审计及 SHA256 已归档。
结果只说明这套 agent 和界面配置下重复失败，不等于模型本身必败或 OS 特有问题。

## 题面位置

```text
/Users/conglin/Downloads/cl实验/EnvShift-GUI对账提交-20260914/gui_submit_task.py
/Users/conglin/Downloads/cl实验/EnvShift-GUI第三批-20260914/tasks/G05/prompt.md
/Users/conglin/Downloads/cl实验/EnvShift-GUI第三批-20260914/tasks/G08/prompt.md
/Users/conglin/Downloads/cl实验/EnvShift-GUI第三批-20260914/tasks/G10/prompt.md
```

G01 题面位于运行脚本第 133 行；G05/G08/G10 旁有 fixture.json、truth.json、acceptance.json。

## 证据与远端

最新结果提交：`74f0b6cd6a0d74631bc7ee6fe06874f2bf9f868e`。
仓库：`TraceLite-AI/envshift-runner`；结果分支：`codex/gui-repeat-20260914`。
执行源码：`c230fc6a1c2fb98a336b7154ba8d15b16e6605c0`；复测工作流：`527774d8a693da1beeda3374d67126baad4d7dc5`。
模型运行：`34828647869`；对照运行：`34828438040`。

[复测报告](https://github.com/TraceLite-AI/envshift-runner/blob/74f0b6cd6a0d74631bc7ee6fe06874f2bf9f868e/experiments/G08-G10-repeat/REPORT.md)

```text
/Users/conglin/Downloads/cl实验/EnvShift-GUI稳定性复测-20260914/REPORT.md
/Users/conglin/Downloads/cl实验/EnvShift-GUI稳定性复测-20260914/OBSERVATIONS.md
/Users/conglin/Downloads/cl实验/EnvShift-GUI稳定性复测-20260914/VIEWER.html
/Users/conglin/Downloads/cl实验/EnvShift-GUI稳定性复测-20260914.zip
```

完整包 SHA256：`f3ce50de080cdcd493eba86bb4edfb55650dec20587d9b64cfe41f07ec2ec44a`。
远端已验证保留先前 12 条失败证据，新增 10 条；本地证据包 823 文件全部校验。

## 已观察到的行为与限制

- G01：原生文件选择激活失败一次，Ubuntu 同配置另一次成功。
- G05：跨标签对账基线三系统失败；Linux notebook 诊断一次恢复成功。
- G08：五轮都进入编辑后的返回循环；三轮无写入，两轮只保存旧资料草稿。编辑页没有 Cancel，视图切换未写浏览器 history。
- G10：五轮都多次 ack，未 approve；大量 scroll 附加被执行器忽略的 x/y。再次 ack 会重绘表单并重置已选 Manager。失败涉及 agent、接口和页面行为，不能单独归因模型或 OS。

## 下一批

G11–G13 已在 `EnvShift-GUI第四批-20260914/` 实现题面、界面、判据和 runner 脚本；18 项本地判据检查通过。尚未跑 GUI 对照或模型，不计入已验证任务或 badcase：

- G11：原生保存框替换已有 CSV，检查目标文件实际更新。
- G12：可搜索组合框选择确切供应商 ID，检查显示文字与绑定实体。
- G13：横向滚动表格修改指定单元格，检查其他行列保持原值。

沿用现有模型，使用 GitHub runner；先正反对照，再模型运行。记录 OS、架构、视口、浏览器、接口等混杂因素。
关键条件直接给在题面，不以遗漏历史信息、无效通道或人为注入 OS 配置制造新失败。

G11 与 G04 属于同一保存/覆盖家族；G12 与 G08 有实体歧义关联。新题不自动等于独立机制。

题面目录：`/Users/conglin/Downloads/cl实验/EnvShift-GUI第四批-20260914/tasks/`，各题在 `G11/prompt.md`、`G12/prompt.md`、`G13/prompt.md`。

继续入口：`EnvShift-GUI第四批-20260914/CONTINUE.md`。新分支拟为 `codex/gui-batch4-20260914`，尚未创建。
本轮公开上传被自动审批拒绝：已有 runner 授权未被认定为包含向公共仓库 `TraceLite-AI/envshift-runner` 发布本批代码、题目与状态。须得到用户对该公开目的地和内容的明确授权后再提交；不要换通道绕过。此次未启动任何远端对照或模型运行。


2026-09-14 接续：用户在明确询问公开上传到 `TraceLite-AI/envshift-runner` 并测试之后回复“做完题直接去验证”。现按该确认继续发布和验证，不再因之前的授权问题暂停。上面的审批阻挡为历史记录。
