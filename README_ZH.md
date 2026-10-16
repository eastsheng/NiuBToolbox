# NiuB工具箱

[English](README.md) | 简体中文

NiuB工具箱是一款轻量的 Windows 桌面工具软件，集中提供日常图片处理和文件转换能力。软件支持中英文界面、白天与黑夜模式、窗口缩放，并通过后台处理保持界面流畅。

另提供学术成果统计：输入 Google Scholar 和/或 ResearchGate 作者主页、年份区间，即可查看逐年条目数及合计，并手动导出 CSV 或 JSON。两个来源分别统计，不直接相加。

图片与文件处理在本地完成。生成结果只会在点击“保存结果”或“导出图片”并选择保存位置后写入磁盘。学术成果统计会访问填写的主页网站。

## 下载

请前往 [GitHub Releases](https://github.com/eastsheng/NiuBToolbox/releases) 下载最新安装包。

1.0.8 版本支持 64 位 Windows 10 和 Windows 11。

## 本地 AI 模型

AI 功能使用本地 ONNX 模型。可通过对应工具中的下载按钮获取模型，然后将模型文件直接放入软件的 `models` 文件夹，不要在其中创建子文件夹。

AI 去水印模型：

[下载 inpainting_lama_2025jan.onnx](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

模型文件名如下：

```text
models/inpainting_lama_2025jan.onnx
models/RealESRGAN_x4plus.onnx
models/modnet_photographic.onnx
```

## 从源码运行

需要 64 位 Windows 10/11 和 Python 3.11。

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m pip install -r requirements.txt
python -m playwright install chromium
python qt_app.py
```

安装依赖后，也可以双击 `run.bat` 启动。

## 隐私

图片和文件均保留在本机，NiuB工具箱不会上传这些内容。
学术成果统计会访问用户填写的公开主页。ResearchGate 可能需要登录或验证；可连接以 `--remote-debugging-port=9222` 启动的已登录 Chrome，也可使用独立浏览器或 Playwright cookies 文件。统计值是主页可见条目数，不保证等于真实发表总数。
