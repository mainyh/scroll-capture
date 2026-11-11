"""Full-screen overlay to pick a window (click) or an area (drag)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from PySide6.QtCore import QObject, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPainterPath, QPen, QScreen
from PySide6.QtWidgets import QWidget

from ..core.win32utils import (MonitorInfo, Rect, WindowInfo, get_cursor_pos, monitors,
                               raw_window_rect, set_window_rect, top_window_at)
from ..i18n import tr
from .screens import match_screen

HOVER_COLOR = QColor("#ff3b30")
AREA_COLOR = QColor("#ffcc00")
HALO = QColor(0, 0, 0, 150)
DIM = QColor(0, 0, 0, 110)
DRAG_THRESHOLD = 6


@dataclass
class PickResult:
    window: WindowInfo
    anchor: tuple[int, int]
    region: Rect | None   # set when the user dragged an area


class _Overlay(QWidget):
    """Covers exactly one monitor.

    Coordinates are mapped from the overlay's *actual* native window rectangle,
    so the highlight stays exact on mixed-DPI multi-monitor setups even if Qt
    and Windows disagree about logical positions.
    """

    def __init__(self, session: "PickerSession", mon: MonitorInfo, screen: QScreen | None):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool)
        self.session = session
        self.phys = mon.rect
        self._native: Rect | None = None
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        if screen is not None:
            # create the native window on the right monitor (right DPI) from the start
            self.setScreen(screen)
            self.setGeometry(screen.geometry())

    # --------------------------------------------------------------- placement
    def pin(self) -> None:
        """Force the window to cover the monitor's physical rectangle exactly."""
        hwnd = int(self.winId())
        for _ in range(3):
            if raw_window_rect(hwnd) == self.phys:
                break
            set_window_rect(hwnd, self.phys)
        self._native = None
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        self.pin()
        # a DPI change triggered by the move may resize the window once more
        QTimer.singleShot(80, self.pin)

    def moveEvent(self, e):
        self._native = None
        super().moveEvent(e)

    def resizeEvent(self, e):
        self._native = None
        super().resizeEvent(e)

    def _to_local(self, r: Rect) -> QRectF:
        if self._native is None:
            self._native = raw_window_rect(int(self.winId()))
        n = self._native
        sx = n.width / max(1, self.width())
        sy = n.height / max(1, self.height())
        return QRectF((r.left - n.left) / sx, (r.top - n.top) / sy, r.width / sx, r.height / sy)

    # --------------------------------------------------------------- painting
    def paintEvent(self, _e):
        s = self.session
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        full = QRectF(self.rect())
        # alpha 1 everywhere keeps mouse input on the overlay (fully transparent pixels click through)
        p.fillRect(full, QColor(0, 0, 0, 1))

        hole: QRectF | None = None
        color = HOVER_COLOR
        label = ""
        if s.drag_rect is not None:
            hole = self._to_local(s.drag_rect)
            color = AREA_COLOR
            label = f"{s.drag_rect.width} × {s.drag_rect.height}"
        elif s.hover is not None:
            hole = self._to_local(s.hover.rect)
            title = s.hover.title or s.hover.class_name
            exe = os.path.basename(s.hover.exe_path) if s.hover.exe_path else ""
            label = f"{title} · {exe}" if exe else title

        path = QPainterPath()
        path.addRect(full)
        if hole is not None:
            inner = QPainterPath()
            inner.addRect(hole)
            path = path.subtracted(inner)
        p.fillPath(path, DIM)

        if hole is not None and hole.intersects(full):
            # light tint inside so the picked area reads clearly (and stays clickable)
            tint = QColor(color)
            tint.setAlpha(26)
            p.fillRect(hole, tint)
            edge = hole.adjusted(2, 2, -2, -2)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.setPen(QPen(HALO, 7))                  # dark halo: visible on light and dark content
            p.drawRect(edge)
            pen = QPen(color, 4)
            if s.drag_rect is not None:
                pen.setStyle(Qt.PenStyle.DashLine)
            p.setPen(pen)
            p.drawRect(edge)
            self._draw_tag(p, hole.intersected(full), label, color)

        if s.cursor_monitor == self.phys:
            self._draw_hint(p, full)

    def _draw_tag(self, p: QPainter, hole: QRectF, text: str, color: QColor) -> None:
        if not text:
            return
        f = QFont(self.font())
        f.setPointSizeF(9.5)
        p.setFont(f)
        fm = QFontMetrics(f)
        text = fm.elidedText(text, Qt.TextElideMode.ElideRight, int(max(120, min(hole.width(), 600))))
        w, h = fm.horizontalAdvance(text) + 16, fm.height() + 6
        x, y = hole.left(), hole.top() - h
        if y < 0:
            y = hole.top()
        x = max(0.0, min(x, self.width() - w))
        r = QRectF(x, y, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color)
        p.drawRoundedRect(r, 4, 4)
        p.setPen(QColor("black") if color == AREA_COLOR else QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_hint(self, p: QPainter, full: QRectF) -> None:
        text = tr("pick.hint_area") if self.session.mode == "area" else tr("pick.hint_window")
        f = QFont(self.font())
        f.setPointSizeF(10)
        p.setFont(f)
        fm = QFontMetrics(f)
        w, h = fm.horizontalAdvance(text) + 28, fm.height() + 14
        r = QRectF(full.center().x() - w / 2, full.bottom() - h - 40, w, h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 20, 20, 220))
        p.drawRoundedRect(r, 8, 8)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    # --------------------------------------------------------------- input
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.session.cancel()
        elif e.button() == Qt.MouseButton.LeftButton:
            self.session.press()

    def mouseMoveEvent(self, _e):
        self.session.poll()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.session.release()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            self.session.cancel()


class PickerSession(QObject):
    picked = Signal(object)    # PickResult
    cancelled = Signal()

    def __init__(self, mode: str = "window", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.hover: WindowInfo | None = None
        self.drag_rect: Rect | None = None
        self.cursor_monitor: Rect | None = None
        self._press_pos: tuple[int, int] | None = None
        self._press_window: WindowInfo | None = None
        self._dragging = False
        self._last_pos: tuple[int, int] | None = None
        self._overlays: list[_Overlay] = []
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self.poll)
        self._done = False

    def start(self) -> None:
        mons = monitors()
        self._overlays = [_Overlay(self, m, match_screen(m)) for m in mons]
        for o in self._overlays:
            o.show()
        cx, cy = get_cursor_pos()
        for o in self._overlays:
            if o.phys.contains(cx, cy):
                o.raise_()
                o.activateWindow()
                o.setFocus()
        self.poll(force=True)
        self._timer.start()

    def _update(self) -> None:
        for o in self._overlays:
            o.update()

    def poll(self, force: bool = False) -> None:
        if self._done:
            return
        pos = get_cursor_pos()
        if pos == self._last_pos and not force:
            return
        self._last_pos = pos
        mon = next((o.phys for o in self._overlays if o.phys.contains(*pos)), None)
        if mon != self.cursor_monitor:
            self.cursor_monitor = mon
            self._update()
        if self._press_pos is not None:
            dx, dy = pos[0] - self._press_pos[0], pos[1] - self._press_pos[1]
            if self._dragging or abs(dx) > DRAG_THRESHOLD or abs(dy) > DRAG_THRESHOLD:
                self._dragging = True
                self.drag_rect = Rect.from_points(*self._press_pos, *pos)
                self._update()
                return
        w = top_window_at(*pos, exclude_pid=os.getpid())
        if (w and self.hover and w.hwnd == self.hover.hwnd and w.rect == self.hover.rect) or (w is None and self.hover is None):
            return
        self.hover = w
        self._update()

    def press(self) -> None:
        self._press_pos = get_cursor_pos()
        self._press_window = self.hover
        self._dragging = False

    def release(self) -> None:
        if self._press_pos is None:
            return
        pos = get_cursor_pos()
        if self._dragging and self.drag_rect is not None:
            r = self.drag_rect
            win = self._press_window or top_window_at(*r.center, exclude_pid=os.getpid())
            if win and r.width >= 30 and r.height >= 30:
                self._finish(PickResult(win, r.center, r))
                return
            self.drag_rect = None
            self._dragging = False
            self._press_pos = None
            self._update()
            return
        if self.hover is not None:
            self._finish(PickResult(self.hover, pos, None))
        self._press_pos = None

    def cancel(self) -> None:
        if self._done:
            return
        self._close()
        QTimer.singleShot(0, self.cancelled.emit)

    def _close(self) -> None:
        self._done = True
        self._timer.stop()
        for o in self._overlays:
            o.close()
        self._overlays = []

    def _finish(self, res: PickResult) -> None:
        self._close()
        # give DWM a moment to remove the overlays before anything grabs the screen
        QTimer.singleShot(150, lambda: self.picked.emit(res))
