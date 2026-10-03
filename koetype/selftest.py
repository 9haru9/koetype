"""動作確認：合成音声を Groq で認識→整形して表示（Macのみ。マイク・キー操作は使わない）。"""
import subprocess
import tempfile
import time

import numpy as np
import soundfile as sf

from . import cleanup, stt
from .config import load_api_key, load_config

SAMPLES = [
    "えーと、明日の会議なんですけど、あの、3時から、いや、4時からに変更でお願いします。",
    "買うものは、まず牛乳、次に卵、それからパンと、えー、バナナです。",
]


def main():
    cfg, key = load_config(), load_api_key()
    for text in SAMPLES:
        with tempfile.NamedTemporaryFile(suffix=".aiff") as f:
            subprocess.run(["say", "-v", "Kyoko", "-o", f.name, text], check=True)
            a, sr = sf.read(f.name, dtype="float32")
        x = np.interp(np.arange(0, len(a), sr / 16000), np.arange(len(a)), a).astype("float32")
        t = time.time()
        raw = stt.transcribe(x, cfg, key)
        t1 = time.time()
        out = cleanup.clean_dictation(raw, cfg, key, "Slack")
        t2 = time.time()
        print(f"認識({t1 - t:.1f}s): {raw}\n整形({t2 - t1:.1f}s): {out}\n")


if __name__ == "__main__":
    main()
