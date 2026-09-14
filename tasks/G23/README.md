# G23 · 图片裁切、旋转与 PNG 导出

题面见 prompt.md，初始数据见 fixture.json，独立交付真值见 truth.json。reference-actions.json / wrong-result-actions.json 是审阅用的合成后端写操作记录；正式模型不得读取这些文件或直接调用 API，界面参考步骤在 ../../reference_ui.py。

在批次根目录运行 `python3 serve.py --task G23`；离线判分用 `python3 verify_delivery.py --task G23 --result <result.json>`，另加 `--artifacts <包含 source.png 与 exports/ 的目录>`。

当前：本地验证通过，模型运行待执行。不能计为新增 badcase。
