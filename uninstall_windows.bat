@echo off
chcp 65001 >nul
rem Remove KoeType from startup (settings in %USERPROFILE%\.koetype are kept)
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\KoeType.lnk" 2>nul
echo 自動起動を解除しました。動作中のKoeTypeはタスクトレイのアイコンから「終了」してください。
pause
