"""状態表示バーの見た目（Mac・Windows共通）。"""

COLORS = {
    "bg": (28, 28, 30),
    "text": (245, 245, 247),
    "hint": (160, 160, 168),
    "badge": (10, 132, 255),
    "recording": (255, 69, 58),
    "processing": (255, 179, 64),
    "done": (48, 209, 88),
    "error": (255, 69, 58),
    "info": (142, 142, 147),
}

BAR_COUNT = 5


class Layout:
    height = 36
    pad_x = 16
    gap = 10
    margin_bottom = 18      # Dock / タスクバーからの距離
    font = 14
    hint_font = 12
    badge_font = 11
    bar_w = 3
    bar_gap = 3
    bar_min = 4
    bar_max = 20
    dot = 7
    indicator_w = BAR_COUNT * 3 + (BAR_COUNT - 1) * 3  # = 27
