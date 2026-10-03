#!/bin/bash
# ダブルクリックで起動（初回は依存関係を自動インストール）
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt
fi
if [ ! -f "$HOME/.koetype/.env" ]; then
  .venv/bin/python -m koetype.setup_key
fi
.venv/bin/python -u -m koetype 2>&1 | tee -a "$HOME/.koetype/koetype.log"
