@echo off
REM Prefer the built EXE when present; otherwise fall back to Python for developers.
cd /d "%~dp0"
if exist "dist\POC-UI\POC-UI.exe" (
  start "" "dist\POC-UI\POC-UI.exe"
  exit /b 0
)
echo POC-UI.exe not found. Building is done with build-windows.bat
echo Falling back to Python launcher for this session...
cd /d "%~dp0..\backend"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python "%~dp0launch.py"
if errorlevel 1 pause
