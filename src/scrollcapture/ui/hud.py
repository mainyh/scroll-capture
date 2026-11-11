"""Small always-on-top progress panel shown while capturing.

It is excluded from screen capture (WDA_EXCLUDEFROMCAPTURE) and placed away
from the capture area so it never ends up in the result.
"""
from __future__ import annotations

from PySide6.QtCore import QElapsedTimer, QRect, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget

from ..core.win32utils import Rect, set_exclude_from_capture
from ..i18n import tr
from . import icons
from .screens import map_for_point

MARGIN = 16


class CaptureHud(QWidget):
    stopRequested = Signal()
    cancelRequested = Signal()

    def __init__(self):
        super().__init__(None, Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
                         | Qt.WindowType.Tool | Qt.WindowType.WindowDoesNotAcceptFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedWidth(300)
        self.setStyleSheet("""
            QLabel { color: #f2f4f7; background: transparent; }
            QLabel#muted { color: #a3acb9; }
            QLabel#hudTitle { font-weight: 600; font-size: 10.5pt; }
            QProgressBar { background: #343a44; border: none; border-radius: 3px;
                           min-height: 6px; max-height: 6px; }
            QProgressBar::chunk { background: #4c84f5; border-radius: 3px; }
            QPushButton { color: #f2f4f7; background: #262b33; border: 1px solid #3a414c;
                          border-radius: 8px; padding: 6px 10px; min-height: 18px; }
            QPushButton:hover { background: #313741; }
            QPushButton:pressed { background: #3a414c; }
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(16, 16)
        self.title = QLabel()
        self.title.setObjectName("hudTitle")
        self.elapsed = QLabel("00:00")
        self.elapsed.setObjectName("muted")
        top.addWidget(self.dot)
        top.addWidget(self.title)
        top.addStretch(1)
        top.addWidget(self.elapsed)
        lay.addLayout(top)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 1000)
        lay.addWidget(self.bar)

        self.stats = QLabel()
        self.maxlbl = QLabel()
        self.maxlbl.setObjectName("muted")
        lay.addWidget(self.stats)
        lay.addWidget(self.maxlbl)

        btns = QHBoxLayout()
        self.btn_stop = QPushButton(tr("hud.stop"))
        self.btn_cancel = QPushButton(tr("hud.cancel"))
        self.btn_stop.setIcon(icons.icon("stop", "#f2f4f7"))
        self.btn_cancel.setIcon(icons.icon("x", "#f2f4f7"))
        for b in (self.btn_stop, self.btn_cancel):
            b.setIconSize(QSize(14, 14))
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.clicked.connect(self.stopRequested)
        self.btn_cancel.clicked.connect(self.cancelRequested)
        btns.addWidget(self.btn_stop)
        btns.addWidget(self.btn_cancel)
        self.btn_row = QWidget()
        self.btn_row.setLayout(btns)
        btns.setContentsMargins(0, 4, 0, 0)
        lay.addWidget(self.btn_row)

        self._clock = QElapsedTimer()
        self._tick = QTimer(self)
        self._tick.setInterval(500)
        self._tick.timeout.connect(self._update_clock)
        self._max = 30000

    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(22, 25, 30, 242))
        p.drawRoundedRect(QRectF(self.rect()), 14, 14)

    def _set_dot(self, name: str, color: str) -> None:
        self.dot.setPixmap(icons.pixmap(name, color, 16))

    def _update_clock(self) -> None:
        s = self._clock.elapsed() // 1000
        self.elapsed.setText(f"{s // 60:02d}:{s % 60:02d}")

    # ------------------------------------------------------------------ API
    def start(self, region: Rect, anchor: tuple[int, int], max_height: int, preparing: bool = False) -> None:
        self._max = max_height
        self._set_dot("record", "#4c84f5" if preparing else "#ff5a52")
        self.title.setText(tr("hud.preparing") if preparing else tr("hud.capturing"))
        self.bar.setValue(0)
        self.bar.setVisible(not preparing)
        self.stats.setText("")
        self.stats.setVisible(not preparing)
        self.maxlbl.setText(tr("hud.max", n=f"{max_height:,}"))
        self.maxlbl.setVisible(not preparing)
        self.btn_row.setVisible(True)
        self.btn_stop.setVisible(not preparing)
        self.adjustSize()
        self._place(region, anchor)
        self._clock.start()
        self._update_clock()
        self._tick.start()
        self.show()
        set_exclude_from_capture(int(self.winId()), True)

    def set_capturing(self) -> None:
        self._set_dot("record", "#ff5a52")
        self.title.setText(tr("hud.capturing"))
        for w in (self.bar, self.stats, self.maxlbl, self.btn_stop):
            w.setVisible(True)
        self.adjustSize()

    def set_progress(self, frames: int, height: int) -> None:
        self.bar.setValue(min(1000, int(height / max(1, self._max) * 1000)))
        self.stats.setText(f"{tr('hud.frames')}  {frames}     {tr('hud.height')}  {height:,} px")

    def finish(self, message: str | None = None, ms: int = 2200) -> None:
        self._tick.stop()
        if not message:
            self.hide()
            return
        self._set_dot("check", "#4cc27e")
        self.title.setText(message)
        for w in (self.bar, self.stats, self.maxlbl, self.btn_row):
            w.setVisible(False)
        self.adjustSize()
        QTimer.singleShot(ms, self.hide)

    # ------------------------------------------------------------------ placement
    def _place(self, region: Rect, anchor: tuple[int, int]) -> None:
        smap = map_for_point(*region.center)
        avail = smap.screen.availableGeometry()
        w, h = self.width(), self.sizeHint().height()
        cands = [
            QRect(avail.right() - w - MARGIN, avail.bottom() - h - MARGIN, w, h),
            QRect(avail.left() + MARGIN, avail.bottom() - h - MARGIN, w, h),
            QRect(avail.right() - w - MARGIN, avail.top() + MARGIN, w, h),
            QRect(avail.left() + MARGIN, avail.top() + MARGIN, w, h),
        ]

        def phys(r: QRect) -> Rect:
            x0, y0 = smap.global_to_phys(r.topLeft())
            x1, y1 = smap.global_to_phys(r.bottomRight())
            return Rect(x0, y0, x1 + 1, y1 + 1)

        chosen = None
        for c in cands:
            pr = phys(c)
            if not pr.intersects(region) and not pr.contains(*anchor):
                chosen = c
                break
        if chosen is None:
            chosen = next((c for c in cands if not phys(c).contains(*anchor)), cands[0])
        self.move(chosen.topLeft())
