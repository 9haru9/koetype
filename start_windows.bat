@echo off
chcp 65001 >nul
rem Run KoeType in a console window (for testing / viewing logs)
cd /d "%~dp0"
if not exist .venv (
  py -3 -m venv .venv
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\pip install -q -r requirements.txt
)
if not exist "%USERPROFILE%\.koetype\.env" (
  .venv\Scripts\python -m koetype.setup_key
)
.venv\Scripts\python -u -m koetype
pause
