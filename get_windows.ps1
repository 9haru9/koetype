# KoeType かんたんインストール（Windows）
#   PowerShell で:  irm https://raw.githubusercontent.com/9haru9/koetype/main/get_windows.ps1 | iex
# Git と Python がなければ winget で入れ、%USERPROFILE%\koetype-git に取得して install_windows.bat を実行する。
$ErrorActionPreference = "Stop"

function Update-SessionPath {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    $launcher = Join-Path $env:LOCALAPPDATA "Programs\Python\Launcher"
    if (Test-Path $launcher) { $env:Path += ";$launcher" }
}

if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Host "winget が見つかりません。Microsoft Store で「アプリ インストーラー」を更新してから、もう一度実行してください。"
    return
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Host "Git をインストールしています..."
    winget install -e --id Git.Git --accept-package-agreements --accept-source-agreements
    Update-SessionPath
}
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "Python をインストールしています..."
    winget install -e --id Python.Python.3.12 --scope user --accept-package-agreements --accept-source-agreements
    Update-SessionPath
}
if (-not (Get-Command git -ErrorAction SilentlyContinue) -or -not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "インストールは完了しましたが、まだ認識されていません。PowerShell を開き直して、同じコマンドをもう一度実行してください。"
    return
}

$dir = Join-Path $HOME "koetype-git"
if (Test-Path (Join-Path $dir ".git")) {
    git -C $dir pull --ff-only
} elseif (Test-Path $dir) {
    Write-Host "$dir が既にあります（git管理ではありません）。名前を変えるか削除してから、もう一度実行してください。"
    return
} else {
    git clone https://github.com/9haru9/koetype.git $dir
}
& cmd /c "`"$(Join-Path $dir 'install_windows.bat')`""
