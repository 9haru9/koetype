#!/bin/bash
# KoeType を常駐アプリとしてインストール（ログイン時に自動起動・異常終了時は自動再起動）
set -e
cd "$(dirname "$0")"
DIR="$(pwd)"
APP="$HOME/Applications/KoeType.app"
PLIST="$HOME/Library/LaunchAgents/com.koetype.app.plist"
LABEL="com.koetype.app"

[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }

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
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "完了。メニューバーにマイクのアイコンが出ます。"
echo "初回はマイク・アクセシビリティ・入力監視で「KoeType」を許可してください。"
