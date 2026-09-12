# NiuB Toolbox

English | [简体中文](README_ZH.md)

NiuB Toolbox is a lightweight Windows desktop utility that brings together practical image processing and file conversion tools in one clean interface.

It can remove unwanted image content with AI, compress and convert common image formats, convert between video and GIF, and turn PDF files into Markdown. The application supports light and dark themes, Simplified Chinese and English, and background processing for a responsive experience. Local content is processed on your device.

## Download

Download the latest Windows installer from the [Releases page](https://github.com/eastsheng/NiuBToolbox/releases).

The installer supports 64-bit Windows 10 and Windows 11. After installation, tools other than AI repair are ready to use without additional configuration.

## Local AI Model

The installer and source repository do not include the optional AI model. Download the official OpenCV LaMa model and place it in the `models` folder:

[Download inpainting_lama_2025jan.onnx](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

```text
NiuBToolbox/models/inpainting_lama_2025jan.onnx
```

## Run from Source

Requires 64-bit Windows 10/11 and Python 3.11.

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m pip install -r requirements.txt
python qt_app.py
```

You can also double-click `run.bat` after installing the dependencies.

## Privacy

Images and files are processed locally and do not need to be uploaded.
