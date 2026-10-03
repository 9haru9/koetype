"""控えめな効果音を生成（短いサイン波の「ポッ」）。~/.koetype/sounds/ に保存して使う。"""
import numpy as np
import soundfile as sf

from .config import HOME_DIR

SR = 44100
SOUND_DIR = HOME_DIR / "sounds"

# 種類: (周波数のリスト[Hz], 1音の長さ[秒], 音量)
SPECS = {
    "start": ([880], 0.06, 0.18),          # 短く高め
    "stop": ([660], 0.06, 0.15),           # 短く低め
    "cancel": ([520, 390], 0.05, 0.13),    # 下がる2音
    "error": ([300, 300], 0.07, 0.18),     # 低い2音
}


def _tone(freqs, length, vol):
    parts = []
    for f in freqs:
        t = np.arange(int(SR * length)) / SR
        env = np.minimum(1, t / 0.005) * np.exp(-t / (length / 3))  # 立ち上がり5ms・自然に減衰
        parts.append(np.sin(2 * np.pi * f * t) * env * vol)
        parts.append(np.zeros(int(SR * 0.025)))
    return np.concatenate(parts).astype("float32")


def ensure_sounds() -> dict:
    SOUND_DIR.mkdir(parents=True, exist_ok=True)
    paths = {}
    for kind, (freqs, length, vol) in SPECS.items():
        p = SOUND_DIR / f"{kind}.wav"
        sf.write(p, _tone(freqs, length, vol), SR, subtype="PCM_16")
        paths[kind] = str(p)
    return paths
