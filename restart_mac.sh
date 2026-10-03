#!/bin/bash
# 設定やコードを変えた後に再起動（メニューから終了した後の再開にも使える）
launchctl kickstart -k "gui/$(id -u)/com.koetype.app"
