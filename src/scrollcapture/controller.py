"""Application controller: Idle -> Picking -> (Detecting) -> Capturing -> Editing."""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import QMessageBox

from . import APP_NAME
from .core import win32utils as w32
from .core.capture import CaptureControl, CaptureEngine, CaptureOptions, CaptureOutcome
from .core.region import detect_scroll_region
from .core.win32utils import Rect, WindowInfo
from .i18n import tr
from .settings import Settings
from .ui.editor_window import EditorWindow
from .ui.hud import CaptureHud
from .ui.main_window import HOTKEY_CAPTURE, HOTKEY_ESC, MainWindow
from .ui.picker_overlay import PickerSession, PickResult
from .ui.saving import default_path, save_with_ui
from .ui.settings_dialog import SettingsDialog

log = logging.getLogger(__name__)


@dataclass
class Target:
    hwnd: int
    title: str
    exe_path: str
    pid: int
    anchor_rel: tuple[int, int]          # relative to the window's top-left
    region_rel: Rect | None = None       # relative to the window's top-left
    manual: bool = False

    @property
    def exe_name(self) -> str:
        return os.path.basename(self.exe_path) if self.exe_path else ""

    @property
    def region_size(self) -> tuple[int, int] | None:
        return (self.region_rel.width, self.region_rel.height) if self.region_rel else None

    def origin(self) -> tuple[int, int]:
        r = w32.window_rect(self.hwnd)
        return r.left, r.top

    def anchor(self) -> tuple[int, int]:
        ox, oy = self.origin()
        return ox + self.anchor_rel[0], oy + self.anchor_rel[1]

    def region(self) -> Rect | None:
        if self.region_rel is None:
            return None
        ox, oy = self.origin()
        return self.region_rel.translated(ox, oy)

    @classmethod
    def from_window(cls, win: WindowInfo, anchor: tuple[int, int], region: Rect | None) -> "Target":
        o = win.rect
        return cls(hwnd=win.hwnd, title=win.title, exe_path=win.exe_path, pid=win.pid,
                   anchor_rel=(anchor[0] - o.left, anchor[1] - o.top),
                   region_rel=region.translated(-o.left, -o.top) if region else None,
                   manual=region is not None)


class _DetectThread(QThread):
    done = Signal(object)   # Rect | Exception

    def __init__(self, hwnd: int, anchor: tuple[int, int], delay_ms: int):
        super().__init__()
        self.hwnd, self.anchor, self.delay = hwnd, anchor, delay_ms

    def run(self) -> None:
        try:
            self.done.emit(detect_scroll_region(self.hwnd, self.anchor, self.delay))
        except Exception as e:  # pragma: no cover - surfaced to the user
            log.exception("detect failed")
            self.done.emit(e)


class _CaptureThread(QThread):
    progress = Signal(int, int)
    done = Signal(object)   # CaptureOutcome | Exception

    def __init__(self, engine: CaptureEngine):
        super().__init__()
        self.engine = engine
        engine.on_progress = lambda f, h: self.progress.emit(f, h)

    def run(self) -> None:
        try:
            self.done.emit(self.engine.run())
        except Exception as e:  # pragma: no cover
            log.exception("capture failed")
            self.done.emit(e)


class Controller(QObject):
    def __init__(self, settings: Settings):
        super().__init__()
        self.s = settings
        self.main = MainWindow(settings)
        self.hud = CaptureHud()
        self.target: Target | None = None
        self.state = "idle"
        self._picker: PickerSession | None = None
        self._threads: list[QThread] = []
        self._control: CaptureControl | None = None
        self._capture_after_detect = False
        self._editors: list[EditorWindow] = []

        m = self.main
        m.pickRequested.connect(lambda mode: self.pick(mode, then_capture=False))
        m.windowChosen.connect(self._window_chosen)
        m.startRequested.connect(self.start_capture)
        m.settingsRequested.connect(self.open_settings)
        m.hotkeyPressed.connect(self._hotkey)
        self.hud.stopRequested.connect(self.stop)
        self.hud.cancelRequested.connect(self.cancel)

    # ------------------------------------------------------------------ lifecycle
    def show(self) -> None:
        self.main.show()
        self.apply_hotkey()

    def apply_hotkey(self) -> None:
        if not self.main.register_hotkey(HOTKEY_CAPTURE, self.s.hotkey):
            self.main.set_status(tr("status.hotkey_fail", key=self.s.hotkey))
            log.warning("hotkey registration failed: %s", self.s.hotkey)

    def bring_to_front(self) -> None:
        if self.state == "idle":
            self.main.showNormal()
            self.main.raise_()
            self.main.activateWindow()

    def _hotkey(self, hid: int) -> None:
        if hid == HOTKEY_ESC:
            self.stop()
        elif hid == HOTKEY_CAPTURE:
            if self.state == "capturing":
                self.stop()
            elif self.state == "idle":
                self.pick("window", then_capture=True)

    # ------------------------------------------------------------------ picking
    def pick(self, mode: str, then_capture: bool) -> None:
        if self.state != "idle":
            return
        self.state = "picking"
        self.main.hide()
        self._picker = PickerSession(mode, self)
        self._picker.picked.connect(lambda r: self._picked(r, then_capture))
        self._picker.cancelled.connect(self._pick_cancelled)
        QTimer.singleShot(120, self._picker.start)

    def _pick_cancelled(self) -> None:
        self.state = "idle"
        self._picker = None
        self.main.show()

    def _picked(self, res: PickResult, then_capture: bool) -> None:
        self._picker = None
        self.target = Target.from_window(res.window, res.anchor, res.region)
        log.info("picked %r (%s) anchor=%s region=%s", res.window.title, res.window.exe_name,
                 res.anchor, res.region)
        self.state = "idle"
        if res.region is None:
            self._detect(then_capture)
        elif then_capture:
            self.start_capture()
        else:
            self._show_main_with_target()

    def _window_chosen(self, win: WindowInfo) -> None:
        if self.state != "idle":
            return
        w32.restore_window(win.hwnd)
        win = w32.window_info(win.hwnd)
        anchor = w32.client_rect(win.hwnd).center
        self.target = Target.from_window(win, anchor, None)
        self._detect(then_capture=False)

    def _show_main_with_target(self) -> None:
        self.main.set_target(self.target)
        if self.target:
            self.main.set_status(tr("status.target_set", title=self.target.title or self.target.exe_name))
        self.main.show()
        self.main.raise_()
        self.main.activateWindow()

    # ------------------------------------------------------------------ detection
    def _check_target(self) -> bool:
        t = self.target
        if t is None or not w32.is_window(t.hwnd):
            self.target = None
            self.main.set_target(None)
            self._error(tr("err.window_gone"))
            return False
        if w32.is_process_elevated(t.pid) is True and not w32.current_process_elevated():
            self._error(tr("err.elevated"))
            return False
        return True

    def _detect(self, then_capture: bool) -> None:
        if not self._check_target():
            self.state = "idle"
            self.main.show()
            return
        t = self.target
        self.state = "detecting"
        self.main.hide()
        w32.activate_window(t.hwnd)
        anchor = t.anchor()
        self.main.set_status(tr("status.detecting"))
        self.hud.start(w32.window_rect(t.hwnd), anchor, self.s.max_height, preparing=True)
        self._capture_after_detect = then_capture
        th = _DetectThread(t.hwnd, anchor, self.s.frame_delay_ms)
        th.done.connect(self._detected)
        self._keep(th)
        th.start()

    def _keep(self, th: QThread) -> None:
        """Hold a reference until the thread has really finished."""
        self._threads.append(th)
        th.finished.connect(lambda: self._threads.remove(th) if th in self._threads else None)

    def _detected(self, result) -> None:
        self.state = "idle"
        if isinstance(result, Exception):
            self.hud.finish()
            self._error(tr("err.capture_failed", err=result))
            self.main.show()
            return
        t = self.target
        if t is not None and w32.is_window(t.hwnd):
            ox, oy = t.origin()
            t.region_rel = result.translated(-ox, -oy)
            t.manual = False
        if self._capture_after_detect:
            self.start_capture(from_detect=True)
        else:
            self.hud.finish()
            self._show_main_with_target()

    # ------------------------------------------------------------------ capture
    def start_capture(self, from_detect: bool = False) -> None:
        if self.state != "idle":
            return
        if self.target is None:
            self.pick("window", then_capture=True)
            return
        if not self._check_target():
            self.hud.finish()
            self.main.show()
            return
        if self.target.region_rel is None:
            self._detect(then_capture=True)
            return
        self.state = "capturing"
        self.main.hide()
        delay = 50 if from_detect else 200
        QTimer.singleShot(delay, self._begin_capture)

    def _begin_capture(self) -> None:
        t = self.target
        w32.activate_window(t.hwnd)
        time.sleep(0.1)
        region, anchor = t.region(), t.anchor()
        # keep the capture on the monitor that holds most of the region
        mons = [m.rect for m in w32.monitors()]
        best = max(mons, key=lambda m: max(0, region.intersect(m).width) * max(0, region.intersect(m).height),
                   default=None)
        if best is not None:
            clipped = region.intersect(best)
            if not clipped.is_empty():
                region = clipped
        if not region.contains(*anchor):
            anchor = region.center
        opts = CaptureOptions(start_from_top=self.s.start_from_top, frame_delay_ms=self.s.frame_delay_ms,
                              max_height=self.s.max_height, notches=self.s.scroll_notches,
                              remove_sticky=self.s.remove_sticky)
        self._control = CaptureControl()
        engine = CaptureEngine(region, anchor, opts, self._control)
        self.hud.start(region, anchor, self.s.max_height)
        self.main.register_hotkey(HOTKEY_ESC, w32.VK_ESCAPE)
        th = _CaptureThread(engine)
        th.progress.connect(self.hud.set_progress)
        th.done.connect(self._captured)
        self._keep(th)
        log.info("capture start region=%s anchor=%s opts=%s", region, anchor, opts)
        th.start()

    def stop(self) -> None:
        if self._control is not None:
            self._control.stop = True

    def cancel(self) -> None:
        if self._control is not None:
            self._control.cancel = True
        elif self.state == "detecting":
            pass  # detection is short; let it finish

    def _captured(self, outcome) -> None:
        self.main.unregister_hotkey(HOTKEY_ESC)
        self._control = None
        self.state = "idle"
        if isinstance(outcome, Exception):
            self.hud.finish()
            self._error(tr("err.capture_failed", err=outcome))
            self.main.show()
            return
        assert isinstance(outcome, CaptureOutcome)
        if outcome.image is None:
            self.hud.finish()
            self.main.set_status(tr("status.cancelled"))
            self.main.show()
            return

        img = outcome.image
        notes = []
        if outcome.frames <= 1:
            notes.append(tr("err.no_scroll"))
        if outcome.reason == "max_height":
            notes.append(tr("warn.max_height"))
        if outcome.gaps:
            notes.append(tr("ed.saved_with_gaps"))
        h, w = img.shape[:2]
        self.main.set_status(tr("status.done", w=f"{w:,}", h=f"{h:,}"))
        title = self.target.title if self.target else "capture"

        if self.s.save_instantly:
            path = default_path(self.s, title, self.s.image_format)
            paths = save_with_ui(None, img, path, self.s.image_format, self.s, title)
            if paths:
                self.hud.finish(tr("hud.saved") + f" · {paths[0].name}")
                self.main.set_status(tr("status.saved", file=str(paths[0])))
            else:
                self.hud.finish()
            self.main.showMinimized()
            return

        self.hud.finish()
        ed = EditorWindow(img, title, self.s, "\n".join(notes))
        ed.saved.connect(lambda paths: self.main.set_status(tr("status.saved", file=str(paths[0]))))
        ed.destroyed.connect(lambda *_: self._editors.remove(ed) if ed in self._editors else None)
        self._editors.append(ed)
        self.main.showMinimized()
        ed.show()
        ed.raise_()
        ed.activateWindow()

    # ------------------------------------------------------------------ misc
    def open_settings(self) -> None:
        dlg = SettingsDialog(self.s, self.main)
        if dlg.exec():
            self.main.sync_from_settings()
            self.apply_hotkey()

    def _error(self, text: str) -> None:
        log.warning("user error: %s", text.replace("\n", " "))
        QMessageBox.warning(None, APP_NAME, text)
