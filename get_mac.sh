#!/bin/bash
# KoeType かんたんインストール（Mac）
#   curl -fsSL https://raw.githubusercontent.com/9haru9/koetype/main/get_mac.sh | bash
# Git（Xcodeコマンドラインツール）がなければ入れ、~/koetype に取得して install_mac.sh を実行する。
set -e
if ! xcode-select -p >/dev/null 2>&1; then
  echo "Xcodeコマンドラインツール（Gitを含む）をインストールします。"
  echo "表示された画面で「インストール」を押してください。完了すると自動で続きを行います..."
  xcode-select --install >/dev/null 2>&1 || true
  until xcode-select -p >/dev/null 2>&1; do sleep 5; done
  echo "インストールが完了しました。"
fi
DIR="$HOME/koetype"
if [ -d "$DIR/.git" ]; then
  git -C "$DIR" pull --ff-only
elif [ -e "$DIR" ]; then
  echo "$DIR が既にあります（git管理ではありません）。名前を変えるか削除してから、もう一度実行してください。"
  exit 1
else
  git clone https://github.com/9haru9/koetype.git "$DIR"
fi
# パイプ実行でもキー入力（APIキーなど）を受け付けられるよう、端末から入力を読む
exec "$DIR/install_mac.sh" < /dev/tty
