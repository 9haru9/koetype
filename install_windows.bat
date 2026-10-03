@echo off
chcp 65001 >nul
rem Install KoeType and register it to start automatically at Windows login
cd /d "%~dp0"
where py >nul 2>nul || (echo Python が見つかりません。https://www.python.org/ から Python 3.11 以降をインストールしてください。& pause & exit /b 1)
if not exist .venv (
  echo 初回セットアップ中（数分かかります）...
  py -3 -m venv .venv
  .venv\Scripts\python -m pip install -q --upgrade pip
  .venv\Scripts\pip install -q -r requirements.txt
)
if not exist "%USERPROFILE%\.koetype\.env" (
  .venv\Scripts\python -m koetype.setup_key
)
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%STARTUP%\KoeType.lnk'); $s.TargetPath='%~dp0.venv\Scripts\pythonw.exe'; $s.Arguments='-m koetype'; $s.WorkingDirectory='%~dp0'; $s.Save()"
start "" "%~dp0.venv\Scripts\pythonw.exe" -m koetype
echo.
echo 完了。タスクトレイ（画面右下）にマイクのアイコンが出ます。
echo 右Ctrl を押しながら話す → 離すと入力。次回からはログイン時に自動起動します。
pause
