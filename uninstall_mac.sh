#!/bin/bash
# 自動起動を解除してアプリを削除（設定・履歴 ~/.koetype は残す）
launchctl bootout "gui/$(id -u)/com.koetype.app" 2>/dev/null || true
rm -f "$HOME/Library/LaunchAgents/com.koetype.app.plist"
rm -rf "$HOME/Applications/KoeType.app"
echo "アンインストールしました（設定と履歴は ~/.koetype に残っています）"
