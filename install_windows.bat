@echo off
chcp 65001 >nul
rem Install KoeType and register it to start automatically at Windows login
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python が見つかりません。Windows標準の winget で Python 3.12 をインストールします...
  winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
  if errorlevel 1 (
    echo 自動インストールに失敗しました。https://www.python.org/ から Python 3.12 をインストールしてください。
    pause
    exit /b 1
  )
  echo.
  echo Python をインストールしました。この画面を閉じて、install_windows.bat をもう一度実行してください。
  pause
  exit /b 0
)
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
echo 完了。KoeType はバックグラウンドで動いています（タスクトレイのマイクのアイコン）。
echo 右Ctrl を押しながら話す → 離すと入力。次回からはログイン時に自動起動します。
echo この画面は10秒後に自動で閉じます（閉じてもKoeTypeは終了しません）。
timeout /t 10 >nul
