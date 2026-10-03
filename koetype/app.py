"""KoeType 本体：ホットキー → 録音 → 文字起こし → 整形 → カーソル位置に入力。"""
import json
import os
import queue
import subprocess
import sys
import threading
import time
from datetime import datetime

import pystray
from PIL import Image, ImageDraw

from . import audio as audio_mod
from . import cleanup, stt
from .config import (CONFIG_PATH, HISTORY_PATH, IS_MAC, load_api_key, load_config,
                     save_config)

if IS_MAC:
    from . import platform_mac as plat
else:
    from . import platform_win as plat

COLORS = {"idle": (140, 140, 140), "recording": (230, 60, 60),
          "handsfree": (230, 120, 30), "processing": (240, 190, 40)}


def make_icon(state: str) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c = COLORS[state]
    d.rounded_rectangle((22, 6, 42, 38), radius=10, fill=c)       # マイク本体
    d.arc((14, 18, 50, 46), start=0, end=180, fill=c, width=4)    # 支え
    d.line((32, 46, 32, 56), fill=c, width=4)
    d.line((22, 57, 42, 57), fill=c, width=4)
    return img


def log(msg: str) -> None:
    line = f"[koetype {datetime.now():%H:%M:%S}] {msg}"
    if sys.stdout is None:  # Windowsの pythonw（コンソールなし）ではファイルに書く
        with open(HISTORY_PATH.parent / "koetype.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    else:
        print(line, flush=True)


class KoeType:
    def __init__(self):
        self.cfg = load_config()
        self.api_key = load_api_key()
        self.recorder = audio_mod.Recorder()
        self.handsfree = False
        self.state = "idle"
        self.jobs: queue.Queue = queue.Queue()
        self.icon: pystray.Icon | None = None
        self.last_text = ""
        self.stats = {"count": 0, "chars": 0}
        self._press_time = 0.0
        self._translate_once = False
        self.active = False  # 論理的な録音中フラグ（ホットキー側で管理）
        self.audio_cmds: queue.Queue = queue.Queue()

    # ---------- ホットキーのコールバック（素早く返すこと） ----------
    # マイクの開始・停止はここでは行わず、録音スレッドに依頼する。
    # macOSの音声システムが固まってもキー監視（メインスレッド）を巻き込まないため。
    def on_press(self):
        if self.handsfree:
            # 録音継続中にもう一度押したら終了して入力
            self.handsfree = False
            self._finish(cancel=False)
            return
        if self.active:
            return
        self.active = True
        self._press_time = time.time()
        self._translate_once = False
        self._set_state("recording")
        self._sound("start")
        self.audio_cmds.put(("start",))

    def on_release(self, combo: bool):
        if self.handsfree or not self.active:
            return
        # Fnを短くタップしただけなら「タップで開始 → もう一度タップで確定」モードにする
        if not combo and time.time() - self._press_time < 0.35:
            self.on_toggle_handsfree()
            return
        # Fn+矢印などのショートカットとして使われた場合は録音を破棄
        self._finish(cancel=combo)

    def on_toggle_handsfree(self):
        if self.active and not self.handsfree:
            self.handsfree = True
            self._set_state("handsfree")
            log("録音継続中（もう一度Fnを押すと確定、Escでキャンセル）")

    def on_translate(self):
        if not self._translate_once:
            self._translate_once = True
            self._sound("start")
            log("この回は英語に翻訳して入力します")

    def on_cancel(self):
        self.handsfree = False
        self._finish(cancel=True)

    def is_active(self) -> bool:
        return self.active

    def _finish(self, cancel: bool):
        if not self.active:
            return
        self.active = False
        if cancel:
            self._set_state("idle")
            self._sound("cancel")
        else:
            self._sound("stop")
            self._set_state("processing")
        self.audio_cmds.put(("stop", cancel, self._translate_once))
        self._translate_once = False

    # ---------- 録音スレッド ----------
    def _guarded(self, fn, what: str, timeout: float = 5.0):
        """音声システムが固まったら自動で再起動する（launchdが10秒後に起動し直す）。"""
        def hung():
            log(f"{what}が{timeout:.0f}秒応答しないため、KoeTypeを再起動します")
            os._exit(1)
        timer = threading.Timer(timeout, hung)
        timer.daemon = True
        timer.start()
        try:
            return fn()
        finally:
            timer.cancel()

    def audio_loop(self):
        while True:
            cmd = self.audio_cmds.get()
            if cmd[0] == "start":
                try:
                    self._guarded(self.recorder.start, "マイクの開始")
                except Exception as e:
                    log(f"録音を開始できません: {e}")
                    self.active = False
                    self.handsfree = False
                    self._set_state("idle")
                    self._sound("error")
            else:
                _, cancel, translate = cmd
                audio = self._guarded(self.recorder.stop, "マイクの停止")
                if not cancel:
                    self.jobs.put((audio, translate))

    # ---------- 処理スレッド ----------
    def worker(self):
        while True:
            audio, translate = self.jobs.get()
            try:
                self._process(audio, translate)
            except Exception as e:
                log(f"エラー: {e}")
                self._sound("error")
            finally:
                if self.jobs.empty() and not self.active:
                    self._set_state("idle")

    def _process(self, audio, translate=False):
        dur = audio_mod.duration(audio)
        if dur < self.cfg["min_record_seconds"] or audio_mod.is_silent(audio):
            log(f"短すぎる/無音のためスキップ（{dur:.1f}秒）")
            return
        t0 = time.time()
        app_name = plat.frontmost_app()
        selected = self._get_selection(app_name) if self.cfg.get("edit_selected_text") else None

        cfg = self.cfg
        if translate:
            cfg = {**self.cfg, "output_language": self.cfg.get("translate_language") or "English",
                   "cleanup_engine": "groq"}
        raw = stt.transcribe(audio, cfg, self.api_key)
        t1 = time.time()
        if not raw:
            log("認識結果が空でした")
            return

        if selected:
            result = cleanup.edit_selection(selected, raw, cfg, self.api_key, app_name)
            mode = "edit"
        else:
            result = cleanup.clean_dictation(raw, cfg, self.api_key, app_name)
            mode = "translate" if cfg.get("output_language") else "dictation"
        t2 = time.time()

        self._insert(result)
        self.last_text = result
        self.stats["count"] += 1
        self.stats["chars"] += len(result)
        log(f"[{mode}] {app_name} / 録音{dur:.1f}秒 認識{t1 - t0:.1f}秒 整形{t2 - t1:.1f}秒")
        if self.cfg.get("history_enabled"):  # 履歴オフなら文章はログにも残さない
            log(f"  生: {raw}")
            log(f"  出: {result}")
        self._save_history(mode, app_name, dur, raw, result, selected)

    def _copy_allowed(self, app_name: str | None) -> bool:
        name = (app_name or "").lower()
        return not any(a.lower() == name or (len(a) > 4 and a.lower() in name)
                       for a in self.cfg.get("selection_skip_apps", []))

    def _get_selection(self, app_name: str | None) -> str | None:
        """選択中のテキストを取得。なければ None。"""
        # 1) Mac: アクセシビリティAPIで直接読む（キー送信もクリップボードも使わない）
        if hasattr(plat, "selected_text_ax"):
            try:
                ok, text = plat.selected_text_ax()
            except Exception:
                ok, text = False, None
            if ok:
                return text if text and text.strip() else None
        # 2) 非対応アプリ: Cmd/Ctrl+C を送ってクリップボードが変わるかで判定。
        #    ターミナル（Ctrl+Cが中断になる）や、未選択時に行全体をコピーするエディタでは行わない。
        if not self._copy_allowed(app_name):
            return None
        saved = plat.clipboard_save()
        before = plat.clipboard_change_count()
        plat.send_copy()
        text = None
        for _ in range(15):
            time.sleep(0.02)
            if plat.clipboard_change_count() != before:
                time.sleep(0.03)
                text = plat.clipboard_get_text()
                break
        if text is not None:
            plat.clipboard_restore(saved)
        return text if text and text.strip() else None

    def _insert(self, text: str):
        saved = plat.clipboard_save()
        plat.clipboard_set_text(text, transient=True)
        ours = plat.clipboard_change_count()
        time.sleep(0.03)
        plat.send_paste()
        time.sleep(0.5)  # 貼り付け先アプリが読み取るのを待ってから復元
        # その間にユーザーが別の物をコピーしていたら上書きしない
        if plat.clipboard_change_count() == ours:
            plat.clipboard_restore(saved)

    def _save_history(self, mode, app_name, dur, raw, result, selected):
        if not self.cfg.get("history_enabled"):
            return
        rec = {"time": datetime.now().isoformat(timespec="seconds"), "mode": mode,
               "app": app_name, "seconds": round(dur, 1), "raw": raw, "text": result}
        if selected:
            rec["selected"] = selected
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # ---------- UI ----------
    def _sound(self, kind):
        if self.cfg.get("sounds"):
            try:
                plat.play_sound(kind)
            except Exception:
                pass

    def _set_state(self, state):
        self.state = state
        if not self.icon:
            return
        img = make_icon(state)
        if IS_MAC:
            from PyObjCTools import AppHelper
            AppHelper.callAfter(self._apply_icon, img)
        else:
            self._apply_icon(img)

    def _apply_icon(self, img):
        self.icon.icon = img

    def _toggle(self, key, on_value, off_value):
        def action(icon, item):
            self.cfg[key] = off_value if self.cfg[key] == on_value else on_value
            save_config(self.cfg)
            log(f"{key} = {self.cfg[key]}")
            if key == "stt_engine":
                threading.Thread(target=stt.warmup_local, args=(self.cfg,), daemon=True).start()
        return action

    def _checked(self, key, value):
        return lambda item: self.cfg.get(key) == value

    def _open(self, path):
        path = str(path)
        if not os.path.exists(path):
            open(path, "a").close()
        if IS_MAC:
            subprocess.Popen(["open", "-t", path])
        else:
            os.startfile(path)

    def _reload(self, icon, item):
        self.cfg = load_config()
        self.api_key = load_api_key()
        log("設定を再読み込みしました")

    def _copy_last(self, icon, item):
        if self.last_text:
            plat.clipboard_set_text(self.last_text)

    def build_menu(self):
        hotkey = "Fn" if IS_MAC else self.cfg["hotkey_windows"]
        return pystray.Menu(
            pystray.MenuItem(lambda i: f"KoeType — {hotkey}長押しで話す", None, enabled=False),
            pystray.MenuItem(
                lambda i: f"今回の起動で {self.stats['count']}回 / {self.stats['chars']}文字",
                None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("AI整形（フィラー除去・句読点）",
                             self._toggle("cleanup_engine", "groq", "none"),
                             checked=self._checked("cleanup_engine", "groq")),
            pystray.MenuItem("常に英語に翻訳して入力",
                             self._toggle("output_language", "English", None),
                             checked=self._checked("output_language", "English")),
            pystray.MenuItem("オフライン認識（ローカルWhisper）",
                             self._toggle("stt_engine", "local", "groq"),
                             checked=self._checked("stt_engine", "local")),
            pystray.MenuItem("選択テキストを音声で編集",
                             self._toggle("edit_selected_text", True, False),
                             checked=self._checked("edit_selected_text", True)),
            pystray.MenuItem("効果音", self._toggle("sounds", True, False),
                             checked=self._checked("sounds", True)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("直前の結果をコピー", self._copy_last),
            pystray.MenuItem("設定ファイルを開く（辞書・文体）", lambda i, it: self._open(CONFIG_PATH)),
            pystray.MenuItem("設定を再読み込み", self._reload),
            pystray.MenuItem("履歴を開く", lambda i, it: self._open(HISTORY_PATH)),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("終了", lambda i, it: i.stop()),
        )

    def run(self):
        # 二重起動防止（2つ動くと同じ文章が2回入力されてしまう）
        import socket
        self._lock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self._lock.bind(("127.0.0.1", 47321))
        except OSError:
            log("KoeType はすでに起動しています。")
            sys.exit(0)
        if not self.api_key and (self.cfg["stt_engine"] == "groq" or self.cfg["cleanup_engine"] == "groq"):
            log("Groq APIキーが未登録です。先に setup_key を実行してください。")
            if self.cfg["stt_engine"] == "groq":
                sys.exit(1)

        threading.Thread(target=self.worker, daemon=True).start()
        threading.Thread(target=self.audio_loop, daemon=True).start()
        threading.Thread(target=stt.warmup_local, args=(self.cfg,), daemon=True).start()

        kwargs = dict(on_press=self.on_press, on_release=self.on_release,
                      on_toggle_handsfree=self.on_toggle_handsfree,
                      on_cancel=self.on_cancel, is_active=self.is_active,
                      on_translate=self.on_translate)
        if not IS_MAC:
            kwargs["hotkey_name"] = self.cfg["hotkey_windows"]
        listener = plat.HotkeyListener(**kwargs)

        self.icon = pystray.Icon("koetype", make_icon("idle"), "KoeType", self.build_menu())

        def setup(icon):
            icon.visible = True
            if not IS_MAC:
                listener.start()

        if IS_MAC:
            # Dockにアイコンを出さずメニューバーだけに常駐
            from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
            NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)
            # イベントタップはメインRunLoopに登録する（pystrayがRunLoopを回す）
            try:
                listener.start()
            except PermissionError as e:
                log(str(e))
                log("許可すると数秒以内に自動で再起動します（ターミナル起動の場合はターミナルを再起動）。")
                sys.exit(1)
        hk = "Fn" if IS_MAC else self.cfg["hotkey_windows"]
        log(f"起動しました。{hk} を押している間だけ録音 → 離すと入力。{hk}+Space でハンズフリー。録音中にShiftで英訳。")
        self.icon.run(setup=setup)


def main():
    KoeType().run()


if __name__ == "__main__":
    main()
