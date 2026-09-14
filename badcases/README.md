# GUI badcase 留存

每条 badcase 保留原始判分、动作轨迹、截图、运行号与证据 SHA256。后续通过不覆盖失败；恢复轨迹作为同一 case 的补充证据。

当前保留 1 条：`BC-G01-Ubuntu-file-activation`。本批 G02–G04 共 9 次模型运行全部正确，没有新增 badcase。

`INDEX.json` 是结构化索引。G01 完整证据在对应目录的 `evidence.zip`（GitHub）或旁边同名 ZIP（本地题包）。稳定 OS 失败、单次未完成、错误交付、虚假完成和装置/接口故障必须分别标记；不能把接口故障计为模型失败。
