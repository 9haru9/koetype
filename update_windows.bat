@echo off
chcp 65001 >nul
rem KoeType を GitHub の最新版に更新（差分だけダウンロード）して起動し直す
cd /d "%~dp0"
where git >nul 2>nul || (echo Git が見つかりません。PowerShell で winget install Git.Git を実行してください。& pause & exit /b 1)
if not exist .git (echo このフォルダは git clone したものではありません。README の手順で clone し直してください。& pause & exit /b 1)

echo 動作中の KoeType を終了しています...
powershell -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe' OR Name='python.exe'\" | Where-Object { $_.CommandLine -like '*-m koetype*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

for /f %%i in ('git rev-parse HEAD') do set OLD=%%i
echo 更新を確認しています...
git pull --ff-only || (echo 更新に失敗しました。このフォルダ内のファイルを手で変更していないか確認してください。& pause & exit /b 1)
for /f %%i in ('git rev-parse HEAD') do set NEW=%%i

if "%OLD%"=="%NEW%" (
  echo すでに最新版です。
) else (
  git diff --quiet %OLD% %NEW% -- requirements.txt || (
    echo 部品の構成が変わったため入れ直しています...
    .venv\Scripts\pip install -q -r requirements.txt
  )
  echo 更新しました:
  git log --oneline %OLD%..%NEW%
)

start "" "%~dp0.venv\Scripts\pythonw.exe" -m koetype
echo.
echo KoeType を起動しました。この画面は10秒後に自動で閉じます。
timeout /t 10 >nul
