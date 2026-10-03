@echo off
chcp 65001 >nul
rem KoeType をバックグラウンドで起動（この黒い画面はすぐ閉じます）
cd /d "%~dp0"
if not exist .venv\Scripts\pythonw.exe (
  echo 先に install_windows.bat を実行してください。
  pause
  exit /b 1
)
start "" "%~dp0.venv\Scripts\pythonw.exe" -m koetype
