"""設定ファイルとAPIキーの読み書き。

設定: ~/.koetype/config.json（初回起動時にデフォルトで生成）
APIキー: ~/.koetype/.env（setup_key.py で登録、パーミッション600）
"""
import json
import os
import sys
from pathlib import Path

HOME_DIR = Path.home() / ".koetype"
CONFIG_PATH = HOME_DIR / "config.json"
ENV_PATH = HOME_DIR / ".env"
HISTORY_PATH = HOME_DIR / "history.jsonl"

IS_MAC = sys.platform == "darwin"
IS_WIN = sys.platform == "win32"

DEFAULTS = {
    # 音声認識: "groq"（無料枠のクラウド・高精度）/ "local"（完全オフライン）
    "stt_engine": "groq",
    "groq_stt_model": "whisper-large-v3",
    "local_stt_model": "mlx-community/whisper-large-v3-turbo",
    # 整形（フィラー除去・言い直し修正・句読点）: "groq" / "none"
    "cleanup_engine": "groq",
    "groq_llm_model": "openai/gpt-oss-120b",
    "groq_llm_fallback_model": "openai/gpt-oss-20b",
    # 話す言語（"ja" 固定 / null で自動判定）
    "language": "ja",
    # 出力言語（null=話した言語のまま、"English" などにすると翻訳して入力）
    "output_language": None,
    # 録音中にShiftを押したときの翻訳先
    "translate_language": "English",
    # 個人辞書：認識させたい固有名詞・専門用語
    "dictionary": [],
    # アプリごとの文体（アプリ名の部分一致。値は自由記述の指示）
    "app_styles": {
        "Slack": "チャット向けの自然な文体。内容は削らない。",
        "LINE": "チャット向けの自然な文体。内容は削らない。",
        "Discord": "チャット向けの自然な文体。内容は削らない。",
        "Mail": "ビジネスメール向けの丁寧な文体。",
        "Outlook": "ビジネスメール向けの丁寧な文体。",
        "Gmail": "ビジネスメール向けの丁寧な文体。",
        "Code": "コード・技術用語はそのまま。余計な敬語を足さない。",
        "Terminal": "コマンドや技術用語はそのまま。句点は付けない。",
        "iTerm": "コマンドや技術用語はそのまま。句点は付けない。",
        "Claude": "AIへの指示文。意図が明確に伝わるよう簡潔に。",
        "ChatGPT": "AIへの指示文。意図が明確に伝わるよう簡潔に。",
    },
    # Windows用ホットキー（WindowsはFnキーをOSが検知できないため）
    # 選択肢: ctrl_r, alt_r, ctrl_l, alt_l, caps_lock, f13〜f20 など
    "hotkey_windows": "ctrl_r",
    # 選択中テキストがある状態で話すと「編集指示」として扱う
    "edit_selected_text": True,
    # 選択テキストの確認（Ctrl+C送信）をしないアプリ。
    # Windowsのターミナルでは Ctrl+C が「実行中の処理の中断」になるため。
    "selection_skip_apps": ["WindowsTerminal", "cmd", "powershell", "pwsh", "conhost",
                            "wezterm", "alacritty", "mintty", "Terminal", "iTerm"],
    "sounds": True,
    # これより短い録音は誤操作として無視（秒）
    "min_record_seconds": 0.4,
    "history_enabled": True,
}


def load_config() -> dict:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError as e:
            print(f"[koetype] config.json の書式エラー（デフォルトで起動）: {e}")
    else:
        save_config(cfg)
    return cfg


def save_config(cfg: dict) -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


def load_api_key() -> str | None:
    key = os.environ.get("GROQ_API_KEY")
    if key:
        return key.strip()
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            if line.startswith("GROQ_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"') or None
    return None


def save_api_key(key: str) -> None:
    HOME_DIR.mkdir(parents=True, exist_ok=True)
    ENV_PATH.write_text(f"GROQ_API_KEY={key.strip()}\n", encoding="utf-8")
    try:
        os.chmod(ENV_PATH, 0o600)
    except OSError:
        pass
