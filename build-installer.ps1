$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYINSTALLER_CONFIG_DIR = Join-Path $PSScriptRoot ".pyinstaller-cache"
$buildPython = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path $buildPython)) {
  python -m venv ".venv-build"
}
& $buildPython -m pip install --disable-pip-version-check -r "requirements-build.txt"
if ($LASTEXITCODE -ne 0) { throw "Installing build dependencies failed." }
& $buildPython -m PyInstaller --noconfirm --clean --windowed --onedir --distpath dist-system --workpath build-system `
  --noupx `
  --name "NiuBToolbox" `
  --icon "assets\app-icon.ico" `
  --add-data "assets;assets" `
  --exclude-module tkinter `
  --exclude-module _tkinter `
  --exclude-module PIL.ImageTk `
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
