@echo off
chcp 65001 >nul
rem 動作確認用：コンソールに記録を表示しながら KoeType を起動（この画面を閉じると終了）
cd /d "%~dp0"
.venv\Scripts\python -u -m koetype --console
pause
