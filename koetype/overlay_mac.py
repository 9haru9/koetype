"""macOS: 画面下（Dockの上）に「入力中」「考え中」を表示する小さなバー。

クリックを透過し、フォーカスも奪わない（入力先のアプリはそのまま）。
AppKitの操作はすべてメインスレッドで行う（AppHelper.callAfter 経由）。
"""
import math
import random

import objc
from AppKit import (NSBackingStoreBuffered, NSBezierPath, NSColor, NSEvent, NSFont,
                    NSFontAttributeName, NSForegroundColorAttributeName, NSMakeRect,
                    NSPanel, NSRunLoop, NSRunLoopCommonModes, NSScreen, NSString,
                    NSTimer, NSView, NSWindowCollectionBehaviorCanJoinAllSpaces,
                    NSWindowCollectionBehaviorFullScreenAuxiliary,
                    NSWindowCollectionBehaviorStationary, NSWindowStyleMaskBorderless,
                    NSWindowStyleMaskNonactivatingPanel)
from PyObjCTools import AppHelper

from .overlay_common import COLORS, BAR_COUNT, Layout

NSStatusWindowLevel = 25
_S = {"kind": "recording", "text": "", "hint": None, "badge": None, "level": 0.0,
      "phase": 0, "bars": [0.0] * BAR_COUNT}


def _rgb(c, a=1.0):
    return NSColor.colorWithCalibratedRed_green_blue_alpha_(c[0] / 255, c[1] / 255, c[2] / 255, a)


def _attrs(size, color, bold=False):
    font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
    attrs = {NSFontAttributeName: font}
    if color is not None:
        attrs[NSForegroundColorAttributeName] = color
    return attrs


class _PillView(NSView):
    def isFlipped(self):
        return False

    def drawRect_(self, rect):
        b = self.bounds()
        w, h = b.size.width, b.size.height
        L = Layout
        _rgb(COLORS["bg"], 0.92).setFill()
        NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(b, h / 2, h / 2).fill()

        kind = _S["kind"]
        accent = _rgb(COLORS[kind])
        x = L.pad_x
        cy = h / 2
        # 左のインジケーター
        if kind == "recording":
            for i, v in enumerate(_S["bars"]):
                bh = L.bar_min + (L.bar_max - L.bar_min) * v
                accent.setFill()
                NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                    NSMakeRect(x + i * (L.bar_w + L.bar_gap), cy - bh / 2, L.bar_w, bh),
                    L.bar_w / 2, L.bar_w / 2).fill()
        elif kind == "processing":
            for i in range(3):
                a = 0.3 + 0.7 * max(0.0, math.sin(_S["phase"] * 0.35 - i * 0.9))
                _rgb(COLORS[kind], a).setFill()
                d = L.dot
                NSBezierPath.bezierPathWithOvalInRect_(
                    NSMakeRect(x + i * (d + 4), cy - d / 2, d, d)).fill()
        else:
            accent.setFill()
            d = L.dot + 2
            NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(x + 4, cy - d / 2, d, d)).fill()
        x += L.indicator_w + L.gap

        # 文字
        text = NSString.stringWithString_(_S["text"])
        ta = _attrs(L.font, _rgb(COLORS["text"]), bold=True)
        ts = text.sizeWithAttributes_(ta)
        text.drawAtPoint_withAttributes_((x, cy - ts.height / 2), ta)
        x += ts.width

        # 英訳バッジ
        if _S["badge"]:
            x += L.gap
            badge = NSString.stringWithString_(_S["badge"])
            ba = _attrs(L.badge_font, _rgb(COLORS["text"]), bold=True)
            bs = badge.sizeWithAttributes_(ba)
            bw, bh = bs.width + 12, bs.height + 2
            _rgb(COLORS["badge"]).setFill()
            NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                NSMakeRect(x, cy - bh / 2, bw, bh), bh / 2, bh / 2).fill()
            badge.drawAtPoint_withAttributes_((x + 6, cy - bs.height / 2), ba)
            x += bw

        # 操作のヒント
        if _S["hint"]:
            x += L.gap
            hint = NSString.stringWithString_(_S["hint"])
            ha = _attrs(L.hint_font, _rgb(COLORS["hint"]))
            hs = hint.sizeWithAttributes_(ha)
            hint.drawAtPoint_withAttributes_((x, cy - hs.height / 2), ha)


def _measure() -> float:
    L = Layout
    w = L.pad_x * 2 + L.indicator_w + L.gap
    w += NSString.stringWithString_(_S["text"]).sizeWithAttributes_(
        _attrs(L.font, None, bold=True)).width
    if _S["badge"]:
        w += L.gap + NSString.stringWithString_(_S["badge"]).sizeWithAttributes_(
            _attrs(L.badge_font, None, bold=True)).width + 12
    if _S["hint"]:
        w += L.gap + NSString.stringWithString_(_S["hint"]).sizeWithAttributes_(
            _attrs(L.hint_font, None)).width
    return math.ceil(w)


class Overlay:
    def __init__(self, get_level):
        self.get_level = get_level
        self._gen = 0
        self._flashing = False
        self.panel = None
        self.view = None
        self.timer = None
        self._create()  # メインスレッドで呼ぶこと（app.run() 内）

    # ---- 公開API（どのスレッドから呼んでもよい） ----
    def show(self, kind, text, hint=None, badge=None):
        AppHelper.callAfter(self._show, kind, text, hint, badge, None)

    def flash(self, kind, text, seconds=0.8):
        AppHelper.callAfter(self._show, kind, text, None, None, seconds)

    def hide(self):
        AppHelper.callAfter(self._hide, False)

    # ---- メインスレッド ----
    def _create(self):
        style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel
        p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, 200, Layout.height), style, NSBackingStoreBuffered, False)
        p.setLevel_(NSStatusWindowLevel)
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setIgnoresMouseEvents_(True)
        p.setHidesOnDeactivate_(False)
        p.setFloatingPanel_(True)
        p.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                 | NSWindowCollectionBehaviorStationary
                                 | NSWindowCollectionBehaviorFullScreenAuxiliary)
        self.view = _PillView.alloc().initWithFrame_(NSMakeRect(0, 0, 200, Layout.height))
        p.setContentView_(self.view)
        self.panel = p

    def _place(self, width):
        mouse = NSEvent.mouseLocation()
        screen = NSScreen.mainScreen()
        for s in NSScreen.screens():
            f = s.frame()
            if f.origin.x <= mouse.x <= f.origin.x + f.size.width and \
               f.origin.y <= mouse.y <= f.origin.y + f.size.height:
                screen = s
                break
        vf = screen.visibleFrame()  # Dockとメニューバーを除いた領域
        x = vf.origin.x + (vf.size.width - width) / 2
        y = vf.origin.y + Layout.margin_bottom
        self.panel.setFrame_display_(NSMakeRect(x, y, width, Layout.height), True)

    def _show(self, kind, text, hint, badge, seconds):
        self._gen += 1
        gen = self._gen
        self._flashing = seconds is not None
        _S.update(kind=kind, text=text, hint=hint, badge=badge)
        self._place(_measure())
        self.view.setNeedsDisplay_(True)
        self.panel.orderFrontRegardless()
        self._ensure_timer()
        if seconds is not None:
            AppHelper.callLater(seconds, self._end_flash, gen)

    def _end_flash(self, gen):
        if gen == self._gen:
            self._hide(True)

    def _hide(self, force):
        if self._flashing and not force:
            return  # 完了・エラー表示は自分のタイマーで消える
        self._flashing = False
        self.panel.orderOut_(None)
        if self.timer:
            self.timer.invalidate()
            self.timer = None

    def _ensure_timer(self):
        if self.timer:
            return
        self.timer = NSTimer.timerWithTimeInterval_repeats_block_(1 / 24, True, self._tick)
        NSRunLoop.mainRunLoop().addTimer_forMode_(self.timer, NSRunLoopCommonModes)

    def _tick(self, timer):
        _S["phase"] += 1
        if _S["kind"] == "recording":
            lvl = min(1.0, (self.get_level() * 14) ** 0.6)
            bars = _S["bars"]
            for i in range(BAR_COUNT):
                center = 1 - abs(i - (BAR_COUNT - 1) / 2) / BAR_COUNT  # 中央ほど高く
                target = lvl * center * random.uniform(0.6, 1.0)
                bars[i] += (target - bars[i]) * 0.5
        self.view.setNeedsDisplay_(True)
