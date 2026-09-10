# NiuB工具箱

[English](README_EN.md) | 简体中文

NiuB工具箱是一款简洁的 Windows 桌面工具软件。当前提供本地 AI 图片去水印功能，后续将持续增加更多实用工具。

图片处理和 AI 推理均在本机完成，无需上传图片。

## 主要功能

- AI 深度修复图片中的水印或多余对象
- OpenCV 快速修复模式
- 画笔自由选择需要修复的区域
- 支持撤销修复和清除选区
- 支持删除当前图片及导出 PNG
- 支持添加兼容的本地 ONNX 模型
- 支持浅色和深色模式
- 支持简体中文与 English 即时切换
- 后台执行 AI 修复，处理时界面仍可正常响应

## 下载与安装

前往项目的 [Releases 页面](https://github.com/eastsheng/NiuBToolbox/releases) 下载最新的 Windows 安装包。

运行安装程序并按照提示完成安装，即可从开始菜单启动 NiuB工具箱。

## 从源码运行

需要 Windows 10/11（64 位）和 Python 3.11。

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python qt_app.py
```

安装依赖后，也可以双击 `run.bat` 启动。

## 使用方法

1. 点击“选择图片”导入需要处理的图片。
2. 调整画笔大小，涂抹需要移除的水印或对象。
3. 选择“AI 深度修复”或“快速修复”。
4. 点击“开始修复”等待处理完成。
5. 如果效果不满意，可以点击“撤销”恢复。
6. 点击“导出图片”保存最终结果。

## 切换语言和主题

- 点击窗口右上角的太阳或月亮图标切换浅色、深色模式。
- 点击左下角“设置”，可以在简体中文和 English 之间切换。
- 软件会自动记住选择的语言、主题和本地模型。

## 使用本地 AI 模型

点击左下角“设置”，选择“添加本地模型”，即可使用本机的 `.onnx` 模型。

当前支持兼容 LaMa 接口、输入名称为 `image` 和 `mask` 的 ONNX 模型。点击“恢复内置模型”可以随时切回软件自带模型。

