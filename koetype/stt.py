"""音声→テキスト。Groq（クラウド無料枠）またはローカルWhisper。"""
import importlib.util
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import requests

from . import audio as audio_mod
from .config import IS_MAC

GROQ_STT_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# Whisperが無音・雑音から生成しがちな定型文
HALLUCINATIONS = [
    "ご視聴ありがとうございました",
    "ご覧いただきありがとうございます",
    "チャンネル登録",
    "おやすみなさい",
    "Thank you for watching",
    "Thanks for watching",
]


def _whisper_prompt(cfg: dict) -> str:
    # Whisperのpromptは「直前の文脈」として働く。辞書の語を含めると表記が寄る。
    words = [w for w in cfg.get("dictionary", []) if w]
    base = "こんにちは。今日は、えー、会議の件で連絡しました。"
    if words:
        base += " " + "、".join(words[:60]) + "。"
    return base


OFFLINE_REQUIREMENTS = Path(__file__).resolve().parent.parent / "requirements-offline.txt"


def local_supported() -> bool:
    """オフライン認識が使える機種か（MacはApple製チップのみ）。"""
    if IS_MAC:
        return platform.machine() == "arm64"
    return sys.platform == "win32"


def local_installed() -> bool:
    return importlib.util.find_spec("mlx_whisper" if IS_MAC else "faster_whisper") is not None


def install_local() -> bool:
    """オフライン認識の部品をインストール（数分かかる）。"""
    flags = 0x08000000 if sys.platform == "win32" else 0  # Windows: コンソールを出さない
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", str(OFFLINE_REQUIREMENTS)],
                       capture_output=True, text=True, creationflags=flags)
    if r.returncode != 0:
        print(f"[koetype] オフライン認識のインストールに失敗: {r.stderr[-500:]}", flush=True)
    importlib.invalidate_caches()
    return r.returncode == 0 and local_installed()


def transcribe(audio: np.ndarray, cfg: dict, api_key: str | None) -> str:
    if cfg["stt_engine"] == "local" and not local_installed():
        cfg = {**cfg, "stt_engine": "groq"}  # 部品がなければGroqで認識
    if cfg["stt_engine"] == "local":
        text = _transcribe_local(audio, cfg)
    else:
        text = _transcribe_groq(audio, cfg, api_key)
    return _filter_hallucination(text.strip())


def _transcribe_groq(audio: np.ndarray, cfg: dict, api_key: str | None) -> str:
    if not api_key:
        raise RuntimeError("Groq APIキーが未登録です（setup_key を実行してください）")
    data = {
        "model": cfg["groq_stt_model"],
        "response_format": "json",
        "temperature": "0",
        "prompt": _whisper_prompt(cfg),
    }
    if cfg.get("language"):
        data["language"] = cfg["language"]
    r = requests.post(
        GROQ_STT_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        files={"file": ("audio.wav", audio_mod.to_wav_bytes(audio), "audio/wav")},
        data=data,
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Groq音声認識エラー {r.status_code}: {r.text[:300]}")
    return r.json().get("text", "")


_local_model = None


def _transcribe_local(audio: np.ndarray, cfg: dict) -> str:
    global _local_model
    lang = cfg.get("language") or None
    prompt = _whisper_prompt(cfg)
    if IS_MAC:
        import mlx_whisper

        result = mlx_whisper.transcribe(
            audio,
            path_or_hf_repo=cfg["local_stt_model"],
            language=lang,
            initial_prompt=prompt,
            temperature=0.0,
            condition_on_previous_text=False,
        )
        return result.get("text", "")
    from faster_whisper import WhisperModel

    if _local_model is None:
        name = cfg.get("local_stt_model_windows", "large-v3-turbo")
        _local_model = WhisperModel(name, device="auto", compute_type="int8")
    segments, _ = _local_model.transcribe(
        audio, language=lang, initial_prompt=prompt, vad_filter=True, beam_size=5
    )
    return "".join(s.text for s in segments)


def warmup_local(cfg: dict) -> None:
    """ローカルモデルを事前ロード（初回の待ち時間を減らす）。"""
    if cfg["stt_engine"] == "local" and local_installed():
        try:
            _transcribe_local(np.zeros(audio_mod.SAMPLE_RATE // 2, dtype=np.float32), cfg)
        except Exception as e:
            print(f"[koetype] ローカルモデルのロード失敗: {e}")


def _filter_hallucination(text: str) -> str:
    stripped = re.sub(r"[\s。、！!？?.,]", "", text)
    for h in HALLUCINATIONS:
        hs = re.sub(r"[\s。、！!？?.,]", "", h)
        if stripped == hs or (hs in stripped and len(stripped) <= len(hs) + 4):
            return ""
    # Whisper promptの例文がそのまま返ってきた場合
    if "会議の件で連絡しました" in text and len(text) < 40:
        return ""
    return text
