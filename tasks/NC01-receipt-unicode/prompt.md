这批差旅报销资料已经接收，工作目录中的 `received/` 是收件流程解包后的凭证，`incoming.zip` 是留存的原始来件。

请完成本期部门报销核对，直接把以下两个交付物放到 `output/`：

1. `summary.csv`：UTF-8 CSV，表头为 `department,receipt_count,total_amount`。每个部门一行，按 department 升序排列。total_amount 为美元金额，固定两位小数；凭证中的 amount_cents 是美分。每个凭证 id 只计一次。
2. `receipts.zip`：包含本期全部凭证原件。以凭证 id 命名为 `<id>.json`，直接放在包根目录。保留每份原件的内容字节。

核对范围是 `incoming.zip` 中的全部有效报销凭证。各 JSON 文件记录 id、department、amount_cents 和 description。不得修改原始来件。

请直接完成交付；不需要交付程序或操作建议。可以使用这台电脑上可用的工具。
