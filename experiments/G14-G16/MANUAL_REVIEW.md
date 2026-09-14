# 本地打开题目

在本目录执行（只需要 Python 3 标准库和浏览器）：

```bash
python3 serve.py --task G14 --out manual-G14.json
```

打开命令打印的 localhost 地址。题面会同时打印在终端，对应文件是 `tasks/G14/prompt.md`。`--task` 可改为 `G15`、`G16`。

操作完成后，在终端按 Ctrl+C，程序将最终状态、审计记录和判分保存为所指定的 JSON 文件。再次启动就是新的初始状态。手动试玩不计入本批模型成绩。

本页供人审题。模型测试由 GitHub runner 执行，不能把手动打开网页当作三系统模型验证。本地完整证据包的当前 runner 是 `diagnostics/window-fit/gui_batch5.py`，根目录 runner 保留初轮版本；公开窗口修正分支中的根目录 runner 已是修正版。冻结的 `gui_agent_loop.py` 未修改。

G15 的图片是代码内原创 SVG，浏览器即可显示，不需要下载图片或安装插件。所有任务数据为本地合成数据。
