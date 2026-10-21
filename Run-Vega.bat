@echo off
cd /d "%~dp0"
python vega_assistant.py
if errorlevel 1 pause

