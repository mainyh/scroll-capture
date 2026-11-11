"""Zoomable image view with a crop rectangle (8 resize handles)."""
from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QCursor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QScrollArea, QWidget

ACCENT = QColor("#2f6fed")
HANDLE = 10
MIN_ZOOM, MAX_ZOOM = 0.02, 8.0

_CURSORS = {
    "tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
    "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
    "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
    "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
    "move": Qt.CursorShape.SizeAllCursor,
}


def to_qimage(arr: np.ndarray) -> QImage:
    h, w, _ = arr.shape
    return QImage(arr.data, w, h, arr.strides[0], QImage.Format.Format_RGB888)


class ImageCanvas(QWidget):
    cropChanged = Signal()
    zoomChanged = Signal()

    def __init__(self, area: QScrollArea):
        super().__init__()
        self.area = area
        self.setMouseTracking(True)
        self._arr: np.ndarray | None = None
        self._img: QImage | None = None
        self.zoom = 1.0
        self.crop_mode = False
        self.crop: QRect | None = None   # image coordinates
        self._drag: str | None = None
        self._drag_start = QPointF()
        self._drag_rect = QRect()
        self._pan_start: QPoint | None = None
        self._pan_scroll = (0, 0)

    # ------------------------------------------------------------------ image
    def set_image(self, arr: np.ndarray) -> None:
        self._arr = np.ascontiguousarray(arr)
        self._img = to_qimage(self._arr)
        self.crop = None
        self._resize()
        self.update()

    def image_size(self) -> tuple[int, int]:
        if self._arr is None:
            return 0, 0
        return self._arr.shape[1], self._arr.shape[0]

    def qimage(self) -> QImage | None:
        return self._img

    # ------------------------------------------------------------------ zoom
    def _resize(self) -> None:
        w, h = self.image_size()
        self.setFixedSize(max(1, round(w * self.zoom)), max(1, round(h * self.zoom)))

    def set_zoom(self, z: float, focus: QPointF | None = None) -> None:
        z = max(MIN_ZOOM, min(MAX_ZOOM, z))
        if abs(z - self.zoom) < 1e-6:
            return
        hs, vs = self.area.horizontalScrollBar(), self.area.verticalScrollBar()
        vp = self.area.viewport()
        if focus is None:
            focus = QPointF(vp.width() / 2, vp.height() / 2)
        img_pt = QPointF((hs.value() + focus.x()) / self.zoom, (vs.value() + focus.y()) / self.zoom)
        self.zoom = z
        self._resize()
        hs.setValue(round(img_pt.x() * z - focus.x()))
        vs.setValue(round(img_pt.y() * z - focus.y()))
        self.update()
        self.zoomChanged.emit()

    def fit_width(self) -> None:
        w, _ = self.image_size()
        if w:
            sb = self.area.verticalScrollBar()
            avail = self.area.width() - 2 * self.area.frameWidth() - sb.sizeHint().width() - 2
            self.set_zoom(min(1.0, avail / w))

    # ------------------------------------------------------------------ coords
    def _to_img(self, p: QPointF) -> QPointF:
        return QPointF(p.x() / self.zoom, p.y() / self.zoom)

    def _to_widget(self, r: QRect) -> QRectF:
        z = self.zoom
        return QRectF(r.x() * z, r.y() * z, r.width() * z, r.height() * z)

    def _hit(self, p: QPointF) -> str | None:
        if self.crop is None:
            return None
        r = self._to_widget(self.crop)
        pts = {
            "tl": r.topLeft(), "tr": r.topRight(), "bl": r.bottomLeft(), "br": r.bottomRight(),
            "t": QPointF(r.center().x(), r.top()), "b": QPointF(r.center().x(), r.bottom()),
            "l": QPointF(r.left(), r.center().y()), "r": QPointF(r.right(), r.center().y()),
        }
        for k, c in pts.items():
            if abs(p.x() - c.x()) <= HANDLE and abs(p.y() - c.y()) <= HANDLE:
                return k
        if r.contains(p):
            return "move"
        return None

    # ------------------------------------------------------------------ crop
    def set_crop_mode(self, on: bool) -> None:
        self.crop_mode = on
        if not on:
            self.crop = None
        self.setCursor(Qt.CursorShape.CrossCursor if on else Qt.CursorShape.ArrowCursor)
        self.update()
        self.cropChanged.emit()

    def _clamp(self, r: QRect) -> QRect:
        w, h = self.image_size()
        return r.normalized().intersected(QRect(0, 0, w, h))

    # ------------------------------------------------------------------ events
    def paintEvent(self, e):
        if self._img is None:
            return
        p = QPainter(self)
        r = QRectF(e.rect())
        z = self.zoom
        src = QRectF(r.x() / z, r.y() / z, r.width() / z, r.height() / z)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, z < 1.0)
        p.drawImage(r, self._img, src)

        if self.crop_mode and self.crop is not None and not self.crop.isEmpty():
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            cr = self._to_widget(self.crop)
            full = QPainterPath()
            full.addRect(QRectF(self.rect()))
            hole = QPainterPath()
            hole.addRect(cr)
            p.fillPath(full.subtracted(hole), QColor(0, 0, 0, 120))
            p.setPen(QPen(ACCENT, 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(cr)
            p.setPen(QPen(ACCENT, 2))
            p.setBrush(QColor("white"))
            for c in (cr.topLeft(), cr.topRight(), cr.bottomLeft(), cr.bottomRight(),
                      QPointF(cr.center().x(), cr.top()), QPointF(cr.center().x(), cr.bottom()),
                      QPointF(cr.left(), cr.center().y()), QPointF(cr.right(), cr.center().y())):
                p.drawRect(QRectF(c.x() - 5, c.y() - 5, 10, 10))
            txt = f"{self.crop.width():,} × {self.crop.height():,}"
            f = QFont(self.font())
            f.setPointSizeF(9)
            p.setFont(f)
            tw = p.fontMetrics().horizontalAdvance(txt) + 12
            th = p.fontMetrics().height() + 4
            lbl = QRectF(cr.right() - tw, cr.bottom() + 6, tw, th)
            if lbl.bottom() > self.height():
                lbl.moveTop(cr.bottom() - th - 6)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACCENT)
            p.drawRoundedRect(lbl, 3, 3)
            p.setPen(QColor("white"))
            p.drawText(lbl, Qt.AlignmentFlag.AlignCenter, txt)

    def mousePressEvent(self, e):
        pos = e.position()
        if e.button() == Qt.MouseButton.MiddleButton or (e.button() == Qt.MouseButton.LeftButton and not self.crop_mode):
            self._pan_start = e.globalPosition().toPoint()
            self._pan_scroll = (self.area.horizontalScrollBar().value(), self.area.verticalScrollBar().value())
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return
        hit = self._hit(pos)
        self._drag_start = self._to_img(pos)
        if hit:
            self._drag = hit
            self._drag_rect = QRect(self.crop)
        else:
            self._drag = "new"
            p = self._drag_start.toPoint()
            self.crop = QRect(p, p)
            self.cropChanged.emit()
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self._pan_start is not None:
            d = e.globalPosition().toPoint() - self._pan_start
            self.area.horizontalScrollBar().setValue(self._pan_scroll[0] - d.x())
            self.area.verticalScrollBar().setValue(self._pan_scroll[1] - d.y())
            return
        if not self.crop_mode:
            return
        if self._drag is None:
            hit = self._hit(pos)
            self.setCursor(_CURSORS.get(hit, Qt.CursorShape.CrossCursor))
            return
        ip = self._to_img(pos)
        dx = round(ip.x() - self._drag_start.x())
        dy = round(ip.y() - self._drag_start.y())
        r = QRect(self._drag_rect)
        k = self._drag
        if k == "new":
            r = QRect(self._drag_start.toPoint(), ip.toPoint())
        elif k == "move":
            w, h = self.image_size()
            r.translate(dx, dy)
            r.moveLeft(max(0, min(r.left(), w - r.width())))
            r.moveTop(max(0, min(r.top(), h - r.height())))
        else:
            if "l" in k:
                r.setLeft(r.left() + dx)
            if "r" in k:
                r.setRight(r.right() + dx)
            if "t" in k:
                r.setTop(r.top() + dy)
            if "b" in k:
                r.setBottom(r.bottom() + dy)
        self.crop = self._clamp(r)
        # auto-scroll when dragging near the viewport edges (long images)
        self.area.ensureVisible(int(pos.x()), int(pos.y()), 40, 40)
        self.update()
        self.cropChanged.emit()

    def mouseReleaseEvent(self, e):
        if self._pan_start is not None:
            self._pan_start = None
            self.setCursor(Qt.CursorShape.CrossCursor if self.crop_mode else Qt.CursorShape.ArrowCursor)
            return
        if self._drag is not None:
            self._drag = None
            if self.crop is not None and (self.crop.width() < 4 or self.crop.height() < 4):
                self.crop = None
            self.update()
            self.cropChanged.emit()

    def wheelEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.25 if e.angleDelta().y() > 0 else 0.8
            vp_pos = self.area.viewport().mapFromGlobal(QCursor.pos())
            self.set_zoom(self.zoom * factor, QPointF(vp_pos))
            e.accept()
        else:
            e.ignore()
