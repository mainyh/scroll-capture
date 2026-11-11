"""Mapping between physical screen pixels (Win32) and Qt logical coordinates.

Qt keeps every screen's *top-left* in native pixels and scales only the size,
so a monitor is matched to its QScreen by device name first and by top-left
position second (never by list order, which can differ between the two APIs).
"""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF
from PySide6.QtGui import QGuiApplication, QScreen

from ..core.win32utils import MonitorInfo, Rect, monitors


def _norm(name: str) -> str:
    return name.replace("\\", "").replace(".", "").upper()


def match_screen(mon: MonitorInfo, screens: list[QScreen] | None = None) -> QScreen | None:
    screens = screens if screens is not None else QGuiApplication.screens()
    for s in screens:
        if _norm(s.name()) == _norm(mon.device):
            return s
    for s in screens:
        g = s.geometry()
        if g.x() == mon.rect.left and g.y() == mon.rect.top:
            return s
    # last resort: the screen whose logical rect contains the monitor's top-left
    for s in screens:
        if s.geometry().contains(QPoint(mon.rect.left, mon.rect.top)):
            return s
    return None


class ScreenMap:
    def __init__(self, screen: QScreen, phys: Rect):
        self.screen = screen
        self.phys = phys
        geo = screen.geometry()
        self.geo = geo
        self.scale = phys.width / geo.width() if geo.width() else screen.devicePixelRatio()

    # physical -> screen-local logical
    def to_local(self, x: float, y: float) -> QPointF:
        return QPointF((x - self.phys.left) / self.scale, (y - self.phys.top) / self.scale)

    def rect_to_local(self, r: Rect) -> QRectF:
        tl = self.to_local(r.left, r.top)
        return QRectF(tl.x(), tl.y(), r.width / self.scale, r.height / self.scale)

    # global logical -> physical
    def global_to_phys(self, p: QPoint | QPointF) -> tuple[int, int]:
        return (round(self.phys.left + (p.x() - self.geo.x()) * self.scale),
                round(self.phys.top + (p.y() - self.geo.y()) * self.scale))

    def phys_to_global(self, x: float, y: float) -> QPoint:
        l = self.to_local(x, y)
        return QPoint(round(self.geo.x() + l.x()), round(self.geo.y() + l.y()))


def screen_maps() -> list[ScreenMap]:
    out = []
    screens = QGuiApplication.screens()
    for m in monitors():
        s = match_screen(m, screens)
        if s is not None:
            out.append(ScreenMap(s, m.rect))
    if not out:  # should not happen; keep the app usable
        for s in screens:
            g = s.geometry()
            r = s.devicePixelRatio()
            out.append(ScreenMap(s, Rect(g.x(), g.y(), g.x() + round(g.width() * r),
                                         g.y() + round(g.height() * r))))
    return out


def map_for_point(x: int, y: int) -> ScreenMap:
    maps = screen_maps()
    for m in maps:
        if m.phys.contains(x, y):
            return m
    return maps[0]
