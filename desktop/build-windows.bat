@echo off
REM Build standalone Windows desktop app: POC-UI.exe
REM Run this on the Windows machine (32-bit or 64-bit Python matching your target PCs).

setlocal
cd /d "%~dp0.."

echo === 1/4 Build React UI ===
cd frontend
call npm ci
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1
cd ..

if not exist "frontend\dist\index.html" (
  echo ERROR: frontend\dist missing after build
  exit /b 1
)

echo === 2/4 Activate backend venv / install project deps ===
cd backend
if not exist .venv\Scripts\activate.bat (
  echo Creating venv...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-32bit.txt
pip install pywebview pyinstaller
cd ..

echo === 3/4 Ensure editable config next to output ===
if not exist desktop\config.json (
  echo ERROR: desktop\config.json missing
  exit /b 1
)

echo === 4/4 PyInstaller onedir -^> desktop\dist\POC-UI\POC-UI.exe ===
cd desktop
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
pyinstaller --noconfirm poc-ui.spec
if errorlevel 1 exit /b 1

REM Copy editable config beside EXE so users can change API URL without rebuild
copy /Y config.json dist\POC-UI\config.json >nul

echo.
echo DONE.
echo Run:  desktop\dist\POC-UI\POC-UI.exe
echo Edit: desktop\dist\POC-UI\config.json  (localhost vs domain)
echo The EXE starts its bundled backend automatically.
echo.
echo Optional MSI/Setup: use Inno Setup on the folder desktop\dist\POC-UI
endlocal
