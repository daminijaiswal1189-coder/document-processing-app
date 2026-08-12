@echo off
cd /d "%~dp0..\backend"
call .venv\Scripts\activate
python ..\desktop\launch.py
if errorlevel 1 pause
