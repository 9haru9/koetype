#!/bin/bash
# KoeType を常駐アプリとしてインストール（ログイン時に自動起動・異常終了時は自動再起動）
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
APP="$HOME/Applications/KoeType.app"
PLIST="$HOME/Library/LaunchAgents/com.koetype.app.plist"
LABEL="com.koetype.app"

# ZIPでダウンロードした場合の「ネットから来た」印を外す（開発元未確認の警告が出ないように）
xattr -dr com.apple.quarantine "$DIR" 2>/dev/null || true

# 必要なツールの確認
if ! xcode-select -p >/dev/null 2>&1; then
  echo "Xcodeコマンドラインツールが必要です。開いた画面で「インストール」を押し、完了後にもう一度実行してください。"
  xcode-select --install || true
  exit 1
fi
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$(command -v "$c")"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Python 3.11 以降が見つかりません（Mac標準の python3 は古いため使えません）。"
  read -r -p "KoeType専用のPython 3.12を自動でダウンロードしますか？（管理者パスワード不要・約30MB）[Y/n] " ans
  case "$ans" in [nN]*)
    echo "https://www.python.org/downloads/ からインストールして、もう一度実行してください。"; exit 1;;
  esac
  # uv（Astral社のPython管理ツール）を ~/.local/bin に入れ、それでPythonを用意する
  if ! command -v uv >/dev/null 2>&1 && [ ! -x "$HOME/.local/bin/uv" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | env UV_NO_MODIFY_PATH=1 sh
  fi
  UV="$(command -v uv || echo "$HOME/.local/bin/uv")"
  "$UV" python install 3.12
  PY="$("$UV" python find 3.12)"
fi

if [ ! -x .venv/bin/python ]; then
  echo "初回セットアップ中（数分かかります）... 使用するPython: $PY"
  "$PY" -m venv .venv
  .venv/bin/python -m pip install -q --upgrade pip
fi
.venv/bin/pip install -q -r requirements.txt

# APIキーの登録（未登録のときだけ）
if [ ! -f "$HOME/.koetype/.env" ]; then
  .venv/bin/python -m koetype.setup_key
  [ -f "$HOME/.koetype/.env" ] || { echo "APIキーが登録されなかったため中止しました。"; exit 1; }
fi

echo "アプリを作成: $APP"
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
clang -O2 -DKOETYPE_DIR="\"$DIR\"" -o "$APP/Contents/MacOS/KoeType" installer/launcher.c
cat > "$APP/Contents/Info.plist" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleIdentifier</key><string>com.koetype.app</string>
  <key>CFBundleName</key><string>KoeType</string>
  <key>CFBundleDisplayName</key><string>KoeType</string>
  <key>CFBundleExecutable</key><string>KoeType</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundleShortVersionString</key><string>1.0</string>
  <key>LSUIElement</key><true/>
  <key>NSMicrophoneUsageDescription</key><string>音声入力のためにマイクを使用します。</string>
</dict></plist>
PL
codesign --force --sign - --identifier com.koetype.app "$APP"

echo "自動起動を登録: $PLIST"
mkdir -p "$HOME/Library/LaunchAgents" "$HOME/.koetype"
cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array><string>$APP/Contents/MacOS/KoeType</string></array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>ProcessType</key><string>Interactive</string>
  <key>StandardOutPath</key><string>$HOME/.koetype/koetype.log</string>
  <key>StandardErrorPath</key><string>$HOME/.koetype/koetype.log</string>
</dict></plist>
PL
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
# 停止が終わるのを待ってから登録（すぐ登録すると失敗することがある）
for i in $(seq 1 20); do
  launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || break
  sleep 0.5
done
for i in 1 2 3; do
  launchctl bootstrap "gui/$(id -u)" "$PLIST" 2>/dev/null && break
  sleep 1
done
launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || { echo "自動起動の登録に失敗しました。もう一度 install_mac.sh を実行してください。"; exit 1; }
echo "完了。メニューバーにマイクのアイコンが出ます。"
echo "初回はマイク・アクセシビリティ・入力監視で「KoeType」を許可してください。"
