"""Windows: 画面下（タスクバーの上）に「入力中」「考え中」を表示する小さなバー。

tkinter を専用スレッドで動かす（tkの操作はすべてこのスレッド内）。
クリックを透過し、フォーカスも奪わない（入力先のアプリはそのまま）。
"""
import ctypes
import ctypes.wintypes as wt
import math
import queue
import random
import threading
import time

from .overlay_common import BAR_COUNT, COLORS, Layout

user32 = ctypes.windll.user32
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
SW_HIDE = 0
SW_SHOWNOACTIVATE = 4
HWND_TOPMOST = -1
SWP_NOACTIVATE = 0x0010
SPI_GETWORKAREA = 0x0030


def _hex(c):
    return "#%02x%02x%02x" % c


# 角丸の外側を透明にするための色（背景色とほぼ同じにして、縁のにじみを目立たなくする）
KEY = _hex((COLORS["bg"][0], COLORS["bg"][1], COLORS["bg"][2] + 1))


class Overlay:
    def __init__(self, get_level):
        self.get_level = get_level
        self.q: queue.Queue = queue.Queue()
        self._ready = threading.Event()
        threading.Thread(target=self._run, daemon=True).start()
        self._ready.wait(5)

    # ---- 公開API（どのスレッドから呼んでもよい） ----
    def show(self, kind, text, hint=None, badge=None):
        self.q.put(("show", kind, text, hint, badge, None))

    def flash(self, kind, text, seconds=0.8):
        self.q.put(("show", kind, text, None, None, seconds))

    def hide(self):
        self.q.put(("hide", False))

    # ---- tkスレッド ----
    def _run(self):
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # 高解像度画面でぼやけないように
        except Exception:
            pass
        import tkinter as tk
        import tkinter.font as tkfont

        self.tk = tk
        root = tk.Tk()
        root.overrideredirect(True)
        root.configure(bg=KEY)
        root.attributes("-topmost", True)
        root.attributes("-transparentcolor", KEY)
        root.attributes("-alpha", 0.95)
        self.scale = root.winfo_fpixels("1i") / 96.0
        self.canvas = tk.Canvas(root, bg=KEY, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True)
        fam = "Yu Gothic UI"
        self.f_text = tkfont.Font(root, family=fam, size=-self._px(Layout.font), weight="bold")
        self.f_hint = tkfont.Font(root, family=fam, size=-self._px(Layout.hint_font))
        self.f_badge = tkfont.Font(root, family=fam, size=-self._px(Layout.badge_font), weight="bold")
        root.geometry("1x1+-100+-100")
        root.update_idletasks()
        self.root = root
        self.hwnd = user32.GetParent(root.winfo_id()) or root.winfo_id()
        ex = user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        ex |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_TOPMOST
        user32.SetWindowLongW(self.hwnd, GWL_EXSTYLE, ex)
        user32.ShowWindow(self.hwnd, SW_HIDE)

        self.state = {"kind": "recording", "text": "", "hint": None, "badge": None}
        self.bars = [0.0] * BAR_COUNT
        self.phase = 0
        self.visible = False
        self.flash_until = None
        self.size = (0, 0)
        self._ready.set()
        root.after(40, self._tick)
        root.mainloop()

    def _px(self, v):
        return int(round(v * self.scale))

    def _tick(self):
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "show":
                    _, kind, text, hint, badge, seconds = msg
                    self.state = {"kind": kind, "text": text, "hint": hint, "badge": badge}
                    self.flash_until = time.time() + seconds if seconds else None
                    self._layout()
                    if not self.visible:
                        user32.ShowWindow(self.hwnd, SW_SHOWNOACTIVATE)
                        self.visible = True
                    user32.SetWindowPos(self.hwnd, HWND_TOPMOST, 0, 0, 0, 0,
                                        0x0001 | 0x0002 | SWP_NOACTIVATE)  # NOSIZE|NOMOVE
                elif msg[0] == "hide" and self.flash_until is None:
                    self._hide()
        except queue.Empty:
            pass
        if self.flash_until and time.time() >= self.flash_until:
            self.flash_until = None
            self._hide()
        if self.visible:
            self.phase += 1
            if self.state["kind"] == "recording":
                lvl = min(1.0, (self.get_level() * 14) ** 0.6)
                for i in range(BAR_COUNT):
                    center = 1 - abs(i - (BAR_COUNT - 1) / 2) / BAR_COUNT
                    target = lvl * center * random.uniform(0.6, 1.0)
                    self.bars[i] += (target - self.bars[i]) * 0.5
            self._draw()
        self.root.after(40, self._tick)

    def _hide(self):
        if self.visible:
            user32.ShowWindow(self.hwnd, SW_HIDE)
            self.visible = False

    def _layout(self):
        L, st = Layout, self.state
        w = self._px(L.pad_x * 2 + L.indicator_w + L.gap) + self.f_text.measure(st["text"])
        if st["badge"]:
            w += self._px(L.gap + 12) + self.f_badge.measure(st["badge"])
        if st["hint"]:
            w += self._px(L.gap) + self.f_hint.measure(st["hint"])
        h = self._px(L.height)
        area = wt.RECT()
        user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(area), 0)  # タスクバーを除く
        x = area.left + (area.right - area.left - w) // 2
        y = area.bottom - h - self._px(L.margin_bottom)
        self.size = (w, h)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _round_rect(self, x0, y0, x1, y1, r, color):
        c = self.canvas
        c.create_oval(x0, y0, x0 + 2 * r, y1, fill=color, outline=color)
        c.create_oval(x1 - 2 * r, y0, x1, y1, fill=color, outline=color)
        c.create_rectangle(x0 + r, y0, x1 - r, y1, fill=color, outline=color)

    def _draw(self):
        L, st, px = Layout, self.state, self._px
        c = self.canvas
        c.delete("all")
        w, h = self.size
        cy = h / 2
        self._round_rect(0, 0, w - 1, h - 1, h / 2, _hex(COLORS["bg"]))
        kind = st["kind"]
        accent = _hex(COLORS[kind])
        x = px(L.pad_x)
        if kind == "recording":
            for i, v in enumerate(self.bars):
                bh = px(L.bar_min + (L.bar_max - L.bar_min) * v)
                bx = x + i * px(L.bar_w + L.bar_gap)
                c.create_rectangle(bx, cy - bh / 2, bx + px(L.bar_w), cy + bh / 2,
                                   fill=accent, outline=accent)
        elif kind == "processing":
            d = px(L.dot)
            for i in range(3):
                a = 0.3 + 0.7 * max(0.0, math.sin(self.phase * 0.35 - i * 0.9))
                col = _hex(tuple(int(COLORS["bg"][j] + (COLORS[kind][j] - COLORS["bg"][j]) * a)
                                 for j in range(3)))
                dx = x + i * (d + px(4))
                c.create_oval(dx, cy - d / 2, dx + d, cy + d / 2, fill=col, outline=col)
        else:
            d = px(L.dot + 2)
            c.create_oval(x + px(4), cy - d / 2, x + px(4) + d, cy + d / 2, fill=accent, outline=accent)
        x += px(L.indicator_w + L.gap)

        c.create_text(x, cy, text=st["text"], anchor="w", fill=_hex(COLORS["text"]), font=self.f_text)
        x += self.f_text.measure(st["text"])
        if st["badge"]:
            x += px(L.gap)
            bw = self.f_badge.measure(st["badge"]) + px(12)
            bh = px(L.badge_font + 6)
            self._round_rect(x, cy - bh / 2, x + bw, cy + bh / 2, bh / 2, _hex(COLORS["badge"]))
            c.create_text(x + bw / 2, cy, text=st["badge"], fill=_hex(COLORS["text"]), font=self.f_badge)
            x += bw
        if st["hint"]:
            x += px(L.gap)
            c.create_text(x, cy, text=st["hint"], anchor="w", fill=_hex(COLORS["hint"]), font=self.f_hint)
