"""Windows: ホットキー監視（pynput）、キー送信、クリップボード、最前面アプリ。

WindowsではFnキーはキーボード内部で処理されOSに届かないため、
デフォルトは「右Ctrl長押し」。config.json の hotkey_windows で変更可。
"""
import ctypes
import ctypes.wintypes as wt
import time

import pyperclip
from pynput import keyboard

_kb = keyboard.Controller()


class HotkeyListener:
    def __init__(self, on_press, on_release, on_toggle_handsfree, on_cancel, is_active,
                 hotkey_name="ctrl_r", on_translate=None):
        self.on_press = on_press
        self.on_release = on_release
        self.on_toggle_handsfree = on_toggle_handsfree
        self.on_cancel = on_cancel
        self.is_active = is_active
        self.on_translate = on_translate
        self.hotkey = getattr(keyboard.Key, hotkey_name)
        self._down = False
        self._combo = False
        self._listener = None

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._press, on_release=self._release)
        self._listener.start()

    def _press(self, key):
        if key == self.hotkey:
            if not self._down:
                self._down = True
                self._combo = False
                self.on_press()
            return
        if key in (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r):
            if self.is_active() and self.on_translate:
                self.on_translate()
            return
        if self._down:
            self._combo = True
            if key == keyboard.Key.space:
                self.on_toggle_handsfree()
        elif key == keyboard.Key.esc and self.is_active():
            self.on_cancel()

    def _release(self, key):
        if key == self.hotkey and self._down:
            self._down = False
            self.on_release(combo=self._combo)


def send_paste() -> None:
    with _kb.pressed(keyboard.Key.ctrl):
        _kb.press("v")
        _kb.release("v")
    time.sleep(0.01)


def send_copy() -> None:
    with _kb.pressed(keyboard.Key.ctrl):
        _kb.press("c")
        _kb.release("c")
    time.sleep(0.01)


def clipboard_save():
    try:
        return pyperclip.paste()
    except Exception:
        return None


def clipboard_restore(saved) -> None:
    if saved is not None:
        pyperclip.copy(saved)


def clipboard_set_text(text: str) -> None:
    pyperclip.copy(text)


def clipboard_get_text() -> str | None:
    try:
        return pyperclip.paste()
    except Exception:
        return None


def clipboard_change_count() -> int:
    return ctypes.windll.user32.GetClipboardSequenceNumber()


def frontmost_app() -> str | None:
    user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(0x1000, False, pid.value)  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return None
    try:
        buf = ctypes.create_unicode_buffer(512)
        size = wt.DWORD(512)
        if kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            name = buf.value.rsplit("\\", 1)[-1]
            return name.rsplit(".", 1)[0]
    finally:
        kernel32.CloseHandle(h)
    return None


_sound_paths = {}


def play_sound(kind: str) -> None:
    import winsound

    from .sounds import ensure_sounds

    if not _sound_paths:
        _sound_paths.update(ensure_sounds())
    path = _sound_paths.get(kind)
    if path:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
