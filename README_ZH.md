# NiuB工具箱

[English](README.md) | 简体中文

NiuB工具箱是一款轻量、简洁的 Windows 桌面工具软件，将常用的图片处理和文件转换工具集中在一个界面中。

软件可用于 AI 图片修复、常见图片格式压缩与转换、视频和 GIF 相互转换，以及 PDF 转 Markdown。软件支持浅色与深色主题、中英文切换，并通过后台处理保持界面流畅。本地内容均在设备上完成处理。

## 下载

前往项目的 [Releases 页面](https://github.com/eastsheng/NiuBToolbox/releases) 下载最新的 Windows 安装包。

安装包支持 64 位 Windows 10 和 Windows 11。安装完成后，除 AI 修复外的工具无需额外配置即可使用。

## 本地 AI 模型

安装包和源码仓库不包含可选的 AI 模型。请下载 OpenCV 官方 LaMa 模型，并将其放入 `models` 文件夹：

[下载 inpainting_lama_2025jan.onnx](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

```text
NiuBToolbox/models/inpainting_lama_2025jan.onnx
```

## 从源码运行

需要 Windows 10/11（64 位）和 Python 3.11。

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m pip install -r requirements.txt
python qt_app.py
```

安装依赖后，也可以双击 `run.bat` 启动。

## 隐私

图片和文件均在本机处理，无需上传。
