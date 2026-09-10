# NiuB工具箱

[English](README_EN.md) | 简体中文

一款使用 Python 与 PySide6 编写的 Windows 桌面工具箱。项目采用可扩展结构，当前提供本地图片去水印功能，后续可以继续添加更多实用工具。

> 图片和 AI 推理均在本机完成，不会上传到服务器。

## 功能

- 使用画笔选择需要移除的区域
- 内置 LaMa ONNX 模型进行 AI 图像修复
- 提供 OpenCV 快速修复模式
- 支持导入兼容 LaMa 接口的本地 ONNX 模型
- 修复结果可撤销，选区可清除
- 支持删除当前图片和导出 PNG
- 支持浅色、深色主题
- 支持简体中文和 English 即时切换，并记住语言设置
- AI 推理在后台线程运行，避免界面无响应
- 无边框圆角 Windows 桌面界面

## 环境要求

- Windows 10 或 Windows 11（64 位）
- Python 3.11（推荐）

## 从源码运行

```powershell
git clone <你的仓库地址>
cd NiuBToolbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python qt_app.py
```

安装依赖后，也可以双击 `run.bat` 启动。

界面语言可在左下角的“设置”中切换，修改后立即生效。

## AI 模型

默认模型位于：

```text
models/inpainting_lama_2025jan.onnx
```

该文件约 92.6 MB，接近 GitHub 的单文件大小限制。本项目已通过 `.gitattributes` 将 ONNX 文件配置为使用 [Git LFS](https://git-lfs.com/)。首次提交前请确认已启用 Git LFS：

```powershell
git lfs install
```

也可以点击软件左下角的“设置”，添加自己的 `.onnx` 模型。自定义模型需要兼容 LaMa 接口，输入名称为 `image` 和 `mask`。

## 生成安装包

构建需要 Python 和 Inno Setup 6。脚本会自动创建独立环境并安装固定版本的 PyInstaller 与运行依赖：

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

生成的安装程序位于 `installer-output/`。该目录属于构建产物，已被 Git 忽略；正式版本可将其中的 `.exe` 作为 GitHub Release 附件发布。

## 项目结构

```text
NiuBToolbox/
├─ assets/                 图标和界面资源
├─ models/                 本地 AI 模型
├─ tools/                  独立的 LaMa 推理后端
├─ qt_app.py               Qt 桌面程序入口
├─ requirements.txt        Python 依赖
├─ requirements-build.txt  打包依赖
├─ run.bat                 本地启动脚本
├─ installer.iss           Inno Setup 配置
└─ build-installer.ps1     安装包构建脚本
```

## 使用说明

1. 点击“选择图片”。
2. 用画笔涂抹需要移除的水印或对象。
3. 选择“AI 深度修复”或“快速修复”。
4. 点击“开始修复”。
5. 如果效果不满意，点击“撤销”；满意后导出图片。

AI 深度修复的耗时取决于 CPU、模型和图片内容。处理期间界面仍可正常响应。

## 注意事项

- 请仅处理自己拥有或已获得授权的图片。
- AI 修复效果受背景复杂度、选区范围和模型能力影响。
- 本项目暂未声明开源许可证；公开仓库不等于自动授予复制、修改或分发权限。如需开放协作，请自行添加合适的 `LICENSE`。
