"""Mapping between physical screen pixels (Win32) and Qt logical coordinates."""
from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRectF
from PySide6.QtGui import QGuiApplication, QScreen

from ..core.win32utils import Rect, monitors


class ScreenMap:
    def __init__(self, screen: QScreen, phys: Rect):
        self.screen = screen
        self.phys = phys
        geo = screen.geometry()
        self.geo = geo
        self.scale = phys.width / geo.width() if geo.width() else screen.devicePixelRatio()

    # physical -> widget-local (for an overlay covering the whole screen)
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
    mons = monitors()
    by_name = {m.device: m for m in mons}
    out = []
    for i, s in enumerate(QGuiApplication.screens()):
        m = by_name.get(s.name())
        if m is None and i < len(mons):
            m = mons[i]
        if m is None:
            g = s.geometry()
            r = s.devicePixelRatio()
            m_rect = Rect(g.x(), g.y(), g.x() + round(g.width() * r), g.y() + round(g.height() * r))
        else:
            m_rect = m.rect
        out.append(ScreenMap(s, m_rect))
    return out


def map_for_point(x: int, y: int) -> ScreenMap:
    maps = screen_maps()
    for m in maps:
        if m.phys.contains(x, y):
            return m
    return maps[0]
