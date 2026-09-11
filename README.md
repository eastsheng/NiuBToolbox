# NiuB工具箱

[English](README_EN.md) | 简体中文

NiuB工具箱是一款简洁的 Windows 桌面工具软件，提供本地 AI 图片去水印和 PDF 转 Markdown 等实用工具。

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
- PDF 转 Markdown，提取正文与图片
- 自动提取 PDF 中的图片，并在 Markdown 正文中的相应位置显示
- 转换任务在后台运行，界面不会卡死

## 下载与安装

前往项目的 [Releases 页面](https://github.com/eastsheng/NiuBToolbox/releases) 下载最新的 Windows 安装包。

运行安装程序并按照提示完成安装，即可从开始菜单启动 NiuB工具箱。

## 下载 AI 模型

安装包和 GitHub 源码不包含 AI 模型。使用“AI 深度修复”前，请下载 OpenCV 官方 LaMa 模型：

[下载 inpainting_lama_2025jan.onnx（92.6 MB）](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

下载完成后，请保持文件名不变，并保存到软件目录的 `models` 文件夹：

```text
NiuBToolbox/models/inpainting_lama_2025jan.onnx
```

安装版会自动创建 `models` 文件夹；源码运行时则将模型放入项目根目录下的 `models` 文件夹。放置完成后重新启动软件即可使用。

## 从源码运行

需要 Windows 10/11（64 位）和 Python 3.11。以下命令直接使用系统 Python，无需创建虚拟环境。

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m pip install -r requirements.txt
python qt_app.py
```

安装依赖后，也可以双击 `run.bat` 启动。

## 使用方法

### 图片去水印

1. 点击“选择图片”导入需要处理的图片。
2. 调整画笔大小，涂抹需要移除的水印或对象。
3. 选择“AI 深度修复”或“快速修复”。
4. 点击“开始修复”等待处理完成。
5. 如果效果不满意，可以点击“撤销”恢复。
6. 点击“导出图片”保存最终结果。

### PDF 转 Markdown

1. 在左侧选择“PDF 转 Markdown”。
2. 点击“选择 PDF”并选择文件。
3. 点击“开始转换”。
4. 转换完成后点击“打开输出文件夹”。

软件会在原 PDF 旁创建 `文件名_markdown` 文件夹，其中包括：

```text
文件名_markdown/
├─ 文件名.md
└─ images/    PDF 中提取的图片
```

Markdown 正文由 [Microsoft MarkItDown](https://github.com/microsoft/markitdown) 提取。软件会按照 PDF 内容块的位置，将提取的图片插入正文中的相应位置。

## 切换语言和主题

- 点击窗口右上角的太阳或月亮图标切换浅色、深色模式。
- 点击左下角“设置”，可以在简体中文和 English 之间切换。
- 软件会自动记住选择的语言、主题和本地模型。

## 使用本地 AI 模型

点击左下角“设置”，选择“添加本地模型”，也可以使用本机其他位置的 `.onnx` 模型。

当前支持兼容 LaMa 接口、输入名称为 `image` 和 `mask` 的 ONNX 模型。点击“使用默认模型”可以切回 `models` 文件夹中的默认模型。
