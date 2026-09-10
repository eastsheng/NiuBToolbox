# NiuB Toolbox

English | [简体中文](README.md)

A Windows desktop toolbox built with Python and PySide6. The project uses an extensible structure for adding more utilities over time. Its first tool removes watermarks or unwanted objects from images using fully local image inpainting.

> Images and AI inference stay on your device and are never uploaded to a server.

## Features

- Paint over the exact area you want to remove
- AI inpainting with a bundled LaMa ONNX model
- Fast repair mode powered by OpenCV
- Support for compatible local LaMa ONNX models
- Undo completed repairs and clear selections
- Remove the current image and export results as PNG
- Light and dark themes
- Instant switching between Simplified Chinese and English
- Saved language and theme preferences
- Background AI inference that keeps the interface responsive
- Frameless, rounded Windows desktop interface

## Requirements

- 64-bit Windows 10 or Windows 11
- Python 3.11 recommended

## Run from Source

```powershell
git clone <your-repository-url>
cd NiuBToolbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python qt_app.py
```

After installing the dependencies, you can also launch the application by double-clicking `run.bat`.

The interface language can be changed from **Settings** in the lower-left corner. Changes take effect immediately and are remembered for the next launch.

## AI Model

The bundled model is stored at:

```text
models/inpainting_lama_2025jan.onnx
```

This file is approximately 92.6 MB and is close to GitHub's single-file size limit. The repository configures ONNX files for [Git LFS](https://git-lfs.com/) through `.gitattributes`. Before your first commit, make sure Git LFS is enabled:

```powershell
git lfs install
```

To use another model, open **Settings** and select a local `.onnx` file. Custom models must be compatible with the LaMa interface and expose inputs named `image` and `mask`.

## Build the Windows Installer

Building requires Python and Inno Setup 6. The script creates an isolated environment and installs pinned versions of PyInstaller and all runtime dependencies automatically:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-installer.ps1
```

The generated installer is placed in `installer-output/`. This directory is ignored by Git; attach the `.exe` separately to a GitHub Release when publishing a version.

## Project Structure

```text
NiuBToolbox/
├─ assets/                 Icons and UI resources
├─ models/                 Local AI models
├─ tools/                  Standalone LaMa inference backend
├─ qt_app.py               Qt desktop application entry point
├─ requirements.txt        Runtime dependencies
├─ requirements-build.txt  Packaging dependencies
├─ run.bat                 Local launcher
├─ installer.iss           Inno Setup configuration
└─ build-installer.ps1     Installer build script
```

## Usage

1. Click **Choose Image**.
2. Paint over the watermark or object you want to remove.
3. Select **AI Deep Repair** or **Quick Repair**.
4. Click **Start Repair**.
5. Use **Undo** if needed, or export the finished image.

AI repair time depends on your CPU, model, and image content. The interface remains responsive while inference runs in the background.

## Notes

- Only process images you own or have permission to modify.
- Repair quality depends on background complexity, selection size, and model capability.
- This project currently has no declared open-source license. A public repository does not automatically grant permission to copy, modify, or redistribute the code. Add an appropriate `LICENSE` before opening the project for broader collaboration.
