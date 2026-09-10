# NiuB Toolbox

English | [简体中文](README.md)

NiuB Toolbox is a clean Windows desktop utility. It currently provides local AI-powered image watermark removal, with more useful tools planned for future updates.

All image processing and AI inference run locally on your device. Images do not need to be uploaded.

## Features

- AI deep repair for watermarks and unwanted objects
- Fast repair powered by OpenCV
- Adjustable brush for selecting repair areas
- Undo completed repairs and clear selections
- Remove the current image and export results as PNG
- Add compatible local ONNX models
- Light and dark themes
- Instant switching between Simplified Chinese and English
- Background AI processing that keeps the interface responsive

## Download and Install

Visit the project's [Releases page](https://github.com/eastsheng/NiuBToolbox/releases) to download the latest Windows installer.

Run the installer and follow the prompts. You can then launch NiuB Toolbox from the Start menu.

## Download the AI Model

The installer and GitHub source do not include the AI model. Before using **AI Deep Repair**, download the official OpenCV LaMa model:

[Download inpainting_lama_2025jan.onnx (92.6 MB)](https://huggingface.co/opencv/inpainting_lama/resolve/main/inpainting_lama_2025jan.onnx?download=true)

Keep the original filename and save it in the application's `models` folder:

```text
NiuBToolbox/models/inpainting_lama_2025jan.onnx
```

The installer creates the `models` folder automatically. When running from source, place the model in the `models` folder at the repository root. Restart the application after adding the file.

## Run from Source

Requires 64-bit Windows 10/11 and Python 3.11.

```powershell
git clone https://github.com/eastsheng/NiuBToolbox.git
cd NiuBToolbox
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python qt_app.py
```

After installing the dependencies, you can also launch the application by double-clicking `run.bat`.

## How to Use

1. Click **Choose Image** and select an image.
2. Adjust the brush size and paint over the watermark or object to remove.
3. Select **AI Deep Repair** or **Quick Repair**.
4. Click **Start Repair** and wait for processing to finish.
5. Click **Undo** if you want to restore the previous result.
6. Click **Export** to save the finished image.

## Language and Theme

- Use the sun or moon button in the upper-right corner to switch themes.
- Open **Settings** in the lower-left corner to select Simplified Chinese or English.
- The application remembers your language, theme, and local model selections.

## Use a Local AI Model

Open **Settings** and click **Add Local Model** to select another `.onnx` model from anywhere on your computer.

The model must be compatible with the LaMa interface and provide inputs named `image` and `mask`. Click **Use Default Model** to switch back to the model in the `models` folder.
