# NiuB Toolbox

English | [简体中文](README_ZH.md)

NiuB Toolbox is a lightweight Windows desktop application for everyday image processing and file conversion. It provides a clean bilingual interface, light and dark themes, resizable windows, and background processing to keep the application responsive.

All processing runs locally. Generated results are written to your chosen location only after you click **Save Result** or **Export**.

## Download

Download the latest installer from the [GitHub Releases page](https://github.com/eastsheng/NiuBToolbox/releases).

Version 1.0.8 supports 64-bit Windows 10 and Windows 11.

## Local AI Models

AI-powered tools use local ONNX models. Use the download button in the corresponding tool, then place the downloaded model file directly in the application's `models` folder. Do not create subfolders inside `models`.

The AI watermark remover uses:

[Download inpainting_lama_2025jan.onnx](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

The expected model filenames are:

```text
models/inpainting_lama_2025jan.onnx
models/RealESRGAN_x4plus.onnx
models/modnet_photographic.onnx
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

Images and files remain on your computer and are not uploaded by NiuB Toolbox.
