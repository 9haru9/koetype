# KoeType — Typeless風の音声入力（Mac / Windows）

どのアプリでも、**ホットキーを押すと入力開始 → 話し終わったらもう一度押すと、整った文章がカーソル位置に入る**。

| 操作 | Mac | Windows |
|---|---|---|
| 入力を開始 | `Fn` を押す | `右Ctrl` を押す（キーは変更可） |
| 入力を終了して文章を入れる | もう一度 `Fn` を押す | もう一度 `右Ctrl` を押す |
| その回だけ英語に翻訳して入力 | 入力中に `Shift` を1回押す | 同じ |
| 入力を取り消す | `Esc` | `Esc` |
| 選択したテキストを声で編集 | 文字を選択してから `Fn` で開始 →「もっと丁寧に」「英語にして」など → `Fn` で終了 | 同じ |

画面下（Dock・タスクバーの上）に「入力中（音量の波形つき）」「考え中」「入力しました」が表示されるので、今の状態がひと目でわかります（メニューの「画面下に状態を表示」でオン・オフ）。

機能: フィラー（えー・あの）の除去、言い直しの修正（「3時、いや4時」→「4時」）、句読点、箇条書き、個人辞書、アプリごとの文体、英語に翻訳して入力、履歴、オフライン認識。

## 費用
- 標準設定は **Groq の無料枠**を使います（音声認識は1日2,000回・約8時間ぶんまで）。クレジットカードの登録は不要です。
- メニューの「オフライン認識」をオンにすると、音声認識はMacの中だけで処理します（完全無料・ネット不要。Apple Silicon搭載Macのみ）。AI整形を使う場合だけGroqにテキストが送られます。

## セットアップ（Mac）
必要なもの: Apple Silicon または Intel の Mac（macOS 13以降）。GitとPythonは、入っていなければ下の手順の中で自動で用意されます

1. https://console.groq.com/keys でAPIキーを無料で発行する
2. **ターミナル**（アプリケーション > ユーティリティ）を開いて、次を実行する
   ```
   xcode-select --install
   ```
   （Gitもこれで入ります。「すでにインストールされています」と出ればOK。画面が出たら「インストール」を押して完了を待つ）
   ```
   git clone https://github.com/9haru9/koetype.git ~/koetype && ~/koetype/install_mac.sh
   ```
   - Python 3.11以降が見つからない場合は「自動でダウンロードしますか？」と聞かれるので Enter（KoeType専用に入り、管理者パスワードは不要）
   - 途中でAPIキーを聞かれたら貼り付ける（画面には表示されません）
3. **システム設定 > プライバシーとセキュリティ** で、「KoeType」を次の3つすべてで許可する
   - アクセシビリティ / 入力監視（一覧にない場合は「＋」で `~/Applications/KoeType.app` を追加）
   - マイク（初めて Fn を押したときに聞かれる）
   - 許可すると10秒ほどで自動的に使えるようになる。以後はログイン時に自動で起動する
4. **システム設定 > キーボード >「🌐キーを押して」を「何もしない」にする**（絵文字パネルや音声入力が開かないように）

- **更新**: `~/koetype/update_mac.sh` を実行する（GitHubから差分だけ取得して起動し直す）
- 起動し直す: `~/koetype/restart_mac.sh` / アンインストール: `~/koetype/uninstall_mac.sh`
- ZIPでダウンロードした場合は、ダブルクリックせずにターミナルで `bash install_mac.sh` を実行する（ダブルクリックすると「開発元が未確認」の警告が出るため）

動作確認（マイクを使わずにテストする）:
```
~/koetype/.venv/bin/python -m koetype.selftest
```

## セットアップ（Windows）
1. Python が入っていなくても大丈夫です（`install_windows.bat` が見つからなければ自動で入れます。そのときは画面の案内どおりもう一度実行）
2. Git をインストールして、このリポジトリを取得する（PowerShellで）
   ```
   winget install Git.Git
   cd $HOME
   git clone https://github.com/9haru9/koetype.git koetype-git
   ```
   （Gitを使わずZIPでダウンロードしても動きますが、その場合は差分更新ができません）
3. 取得したフォルダの `install_windows.bat` をダブルクリックする
4. Groq APIキーを貼り付ける（Macと同じキーでOK）
5. タスクトレイ（画面右下）にマイクのアイコンが出たら完了。次回からはログイン時に自動で起動する

- ホットキー: **右Ctrl** を押すと入力開始 → もう一度押すと終了して入力 / 入力中に`Shift`で英訳 / `Esc`で取り消し
- KoeType はバックグラウンドで動き、黒い画面（コンソール）は残りません。終了はタスクトレイのアイコン →「終了」
- 終了した後にまた起動したいときは `start_windows.bat`。記録を見ながら動かしたいときは `debug_windows.bat`。記録は `%USERPROFILE%\.koetype\koetype.log` に残る
- 自動起動を解除するときは `uninstall_windows.bat`
- **更新**: `update_windows.bat` をダブルクリック。GitHubから差分だけ取得し、必要なら部品を入れ直して、起動し直す
- ターミナル（Windows Terminal・PowerShell・cmd）では「選択テキストの音声編集」は自動でオフになる（Ctrl+C が処理の中断になってしまうため）

## 設定
`~/.koetype/config.json`（メニューの「設定ファイルを開く」から開けます）。編集したら「設定を再読み込み」を押します。
- `dictionary`: 固有名詞・専門用語のリスト。例 `["KoeType", "GitHub", "山田商事"]`
- `app_styles`: アプリ名ごとの文体（アプリ名の部分一致）
- `hotkey_windows`: `ctrl_r` / `alt_r` / `caps_lock` / `f13` など
- `language`: `"ja"` で日本語に固定 / `null` で言語を自動判定
- 履歴: `~/.koetype/history.jsonl`

## プライバシーとセキュリティ
- 録音した音声と認識したテキストは、Groq（https://groq.com）に送って処理します。「オフライン認識」をオンにすると、音声はPCの外に出ません（AI整形をオンにしている場合は、テキストだけ送ります）。
- APIキーは各PCの `~/.koetype/.env` に保存されます（Mac/Linuxでは本人以外は読めない権限600）。このリポジトリにキーは含まれません。
- 履歴（`~/.koetype/history.jsonl`）には入力した文章がそのまま保存されます。不要なら `config.json` の `history_enabled` を `false` にしてください。
- キーボードの監視で反応するのは Fn / 右Ctrl / Shift / Esc だけです。ほかのキー入力は記録も送信もしません。

## ライセンス
MIT License（[LICENSE](LICENSE)）
