#!/bin/bash
# KoeType を GitHub の最新版に更新（差分だけダウンロード）して起動し直す
set -e
cd "$(dirname "$0")"
[ -d .git ] || { echo "このフォルダは git clone したものではありません。READMEの手順で clone し直してください。"; exit 1; }
OLD=$(git rev-parse HEAD)
git pull --ff-only
NEW=$(git rev-parse HEAD)
if [ "$OLD" = "$NEW" ]; then
  echo "すでに最新版です。"
else
  if ! git diff --quiet "$OLD" "$NEW" -- requirements.txt; then
    echo "部品の構成が変わったため入れ直しています..."
    .venv/bin/pip install -q -r requirements.txt
  fi
  if ! git diff --quiet "$OLD" "$NEW" -- installer install_mac.sh; then
    echo "起動用アプリを作り直しています..."
    ./install_mac.sh
  fi
  echo "更新しました:"
  git log --oneline "$OLD..$NEW"
fi
launchctl kickstart -k "gui/$(id -u)/com.koetype.app" 2>/dev/null && echo "KoeType を起動し直しました。" || echo "先に install_mac.sh を実行してください。"
