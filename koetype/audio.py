"""マイク録音（16kHz・モノラル）。"""
import io
import threading

import numpy as np
import sounddevice as sd
import soundfile as sf

SAMPLE_RATE = 16000


class Recorder:
    def __init__(self):
        self._chunks: list[np.ndarray] = []
        self._stream: sd.InputStream | None = None
        self._lock = threading.Lock()
        self.level = 0.0  # 直近の音量（状態表示バーの波形用）

    @property
    def recording(self) -> bool:
        return self._stream is not None

    def start(self) -> None:
        with self._lock:
            if self._stream is not None:
                return
            self._chunks = []
            self.level = 0.0
            self._stream = sd.InputStream(
                samplerate=SAMPLE_RATE, channels=1, dtype="float32", callback=self._callback
            )
            self._stream.start()

    def _callback(self, indata, frames, time_info, status):
        self._chunks.append(indata[:, 0].copy())
        self.level = float(np.sqrt(np.mean(indata[:, 0] ** 2)))

    def stop(self) -> np.ndarray:
        with self._lock:
            stream, self._stream = self._stream, None
        if stream is None:
            return np.zeros(0, dtype=np.float32)
        stream.stop()
        stream.close()
        self.level = 0.0
        if not self._chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(self._chunks)


def duration(audio: np.ndarray) -> float:
    return len(audio) / SAMPLE_RATE


def is_silent(audio: np.ndarray, threshold: float = 0.004) -> bool:
    """無音判定（Whisperが無音から幻聴テキストを生成するのを防ぐ）。"""
    if len(audio) == 0:
        return True
    # 20ms窓のRMSの上位10%で判定（一瞬でも話していれば有音）
    win = SAMPLE_RATE // 50
    n = len(audio) // win
    if n == 0:
        return float(np.sqrt(np.mean(audio**2))) < threshold
    rms = np.sqrt(np.mean(audio[: n * win].reshape(n, win) ** 2, axis=1))
    return float(np.percentile(rms, 90)) < threshold


def to_wav_bytes(audio: np.ndarray) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, SAMPLE_RATE, format="WAV", subtype="PCM_16")
    return buf.getvalue()
