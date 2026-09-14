$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot ".pyinstaller-cache"
python -m pip install --disable-pip-version-check -r "requirements-build.txt"
if ($LASTEXITCODE -ne 0) { throw "Installing build dependencies failed." }
python -m PyInstaller --noconfirm --clean --windowed --onedir --distpath dist-system --workpath build-system `
  --noupx `
  --name "NiuBToolbox" `
  --icon "assets\app-icon.ico" `
  --add-data "assets;assets" `
  --collect-all cajCvtPdf `
  --exclude-module tkinter `
  --exclude-module _tkinter `
  --exclude-module PIL.ImageTk `
  --exclude-module PyQt5 `
  --exclude-module PyQt6 `
  --exclude-module matplotlib `
  --exclude-module IPython `
  --exclude-module astroid `
  --exclude-module nbformat `
  --exclude-module jupyter `
  --exclude-module jupyter_core `
  --exclude-module zmq `
  --exclude-module torch `
  --exclude-module torchvision `
  --exclude-module pandas `
  --exclude-module scipy `
  --exclude-module pytest `
  --exclude-module numba `
  --exclude-module llvmlite `
  --exclude-module win32com `
  --exclude-module pythoncom `
  --exclude-module lz4 `
  --exclude-module pkg_resources `
  --exclude-module setuptools `
  qt_app.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }
$iscc = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $iscc)) { $iscc = "C:\Program Files\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { $iscc = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe" }
if (-not (Test-Path $iscc)) { throw "Inno Setup 6 was not found." }
& $iscc "installer.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }
Write-Host "Installer created in installer-output."
