@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 goto :error
python app.py
if errorlevel 1 goto :error
exit /b 0
:error
pause
exit /b 1
