"""Result window: preview, crop, save, copy."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QGuiApplication, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow,
                               QMessageBox, QPushButton, QScrollArea, QSizePolicy, QToolBar,
                               QVBoxLayout, QWidget)

from .. import APP_NAME
from ..core import exporter
from ..i18n import tr
from ..settings import Settings
from . import theme
from .image_canvas import ImageCanvas
from .saving import default_path, save_with_ui

UNDO_LIMIT = 10


def _checker(a: str, b: str) -> QBrush:
    pm = QPixmap(20, 20)
    pm.fill(QColor(a))
    p = QPainter(pm)
    c = QColor(b)
    p.fillRect(0, 0, 10, 10, c)
    p.fillRect(10, 10, 10, 10, c)
    p.end()
    return QBrush(pm)


class EditorWindow(QMainWindow):
    saved = Signal(list)   # list[Path]

    def __init__(self, img: np.ndarray, title: str, settings: Settings, note: str = ""):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.settings = settings
        self.source_title = title
        self.theme = theme.current()
        self._original = img
        self._img = img
        self._undo: list[np.ndarray] = []
        self._dirty = True

        # --- canvas
        self.area = QScrollArea()
        self.area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.area.setWidgetResizable(False)
        self.area.setFrameShape(QFrame.Shape.NoFrame)
        self.area.viewport().setAutoFillBackground(True)
        self.canvas = ImageCanvas(self.area)
        self.area.setWidget(self.canvas)
        self.canvas.cropChanged.connect(self._refresh)
        self.canvas.zoomChanged.connect(self._refresh)

        # --- toolbar
        tb = QToolBar()
        tb.setMovable(False)
        tb.setIconSize(QSize(18, 18))
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.addToolBar(tb)
        self.act_crop = QAction(tr("ed.crop"), self, checkable=True)
        self.act_crop.setShortcut(QKeySequence("C"))
        self.act_crop.setToolTip(tr("ed.crop") + " (C)")
        self.act_crop.toggled.connect(self._toggle_crop)
        self.act_undo = QAction(tr("ed.undo"), self)
        self.act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        self.act_undo.setToolTip(tr("ed.undo") + " (Ctrl+Z)")
        self.act_undo.triggered.connect(self.undo)
        self.act_orig = QAction(tr("ed.original"), self)
        self.act_orig.triggered.connect(self.reset_original)
        tb.addAction(self.act_crop)
        tb.addSeparator()
        tb.addAction(self.act_undo)
        tb.addAction(self.act_orig)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        tb.addWidget(spacer)
        self.act_fit = QAction(tr("ed.fit"), self)
        self.act_fit.setShortcut(QKeySequence("Ctrl+0"))
        self.act_fit.setToolTip(tr("ed.fit") + " (Ctrl+0)")
        self.act_fit.triggered.connect(self.canvas.fit_width)
        act_100 = QAction("100%", self)
        act_100.setShortcut(QKeySequence("Ctrl+1"))
        act_100.setToolTip("100% (Ctrl+1)")
        act_100.triggered.connect(lambda: self.canvas.set_zoom(1.0))
        tb.addAction(self.act_fit)
        tb.addAction(act_100)

        # --- side panel
        side = QFrame()
        side.setObjectName("sidePanel")
        side.setFixedWidth(212)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(16, 16, 16, 16)
        sl.setSpacing(8)

        self.crop_box = QWidget()
        cl = QVBoxLayout(self.crop_box)
        cl.setContentsMargins(0, 0, 0, 12)
        cl.setSpacing(8)
        cl.addWidget(self._section(tr("ed.crop")))
        self.crop_hint = QLabel(tr("ed.crop_hint"))
        self.crop_hint.setWordWrap(True)
        self.crop_hint.setObjectName("muted")
        cl.addWidget(self.crop_hint)
        self.btn_apply = QPushButton(tr("ed.apply"))
        self.btn_apply.setObjectName("primary")
        self.btn_apply.clicked.connect(self.apply_crop)
        self.btn_cancel_crop = QPushButton(tr("ed.cancel_crop"))
        self.btn_cancel_crop.clicked.connect(lambda: self.act_crop.setChecked(False))
        cl.addWidget(self.btn_apply)
        cl.addWidget(self.btn_cancel_crop)
        sl.addWidget(self.crop_box)

        sl.addWidget(self._section(tr("ed.save_section")))
        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.fmt_group = QButtonGroup(self)
        for i, (key, text) in enumerate((("png", "PNG"), ("jpg", "JPG"))):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setObjectName("segLeft" if i == 0 else "segRight")
            b.setProperty("fmt", key)
            self.fmt_group.addButton(b)
            seg.addWidget(b, 1)
            if key == settings.image_format:
                b.setChecked(True)
        sl.addLayout(seg)
        sl.addSpacing(4)
        self.b_save = QPushButton(tr("ed.save"))
        self.b_save.clicked.connect(self.save)
        self.b_save_as = QPushButton(tr("ed.save_as"))
        self.b_save_as.clicked.connect(self.save_as)
        self.b_copy = QPushButton(tr("ed.copy"))
        self.b_copy.clicked.connect(self.copy)
        for b in (self.b_save, self.b_save_as, self.b_copy):
            b.setIconSize(QSize(18, 18))
            b.setStyleSheet("text-align: left; padding-left: 12px;")
            sl.addWidget(b)
        self.note = QLabel(note)
        self.note.setWordWrap(True)
        self.note.setObjectName("warn")
        self.note.setVisible(bool(note))
        sl.addSpacing(8)
        sl.addWidget(self.note)
        sl.addStretch(1)

        central = QWidget()
        hl = QHBoxLayout(central)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)
        hl.addWidget(self.area, 1)
        hl.addWidget(side)
        self.setCentralWidget(central)

        self.status = QLabel()
        self.statusBar().addWidget(self.status)
        self.statusBar().setSizeGripEnabled(False)

        for seq, fn in (("Ctrl+S", self.save), ("Ctrl+Shift+S", self.save_as), ("Ctrl+C", self.copy)):
            act = QAction(self)
            act.setShortcut(QKeySequence(seq))
            act.triggered.connect(fn)
            self.addAction(act)

        self._apply_theme()
        self.theme.changed.connect(self._apply_theme)
        self._set_image(img, push=False)
        scr = QGuiApplication.primaryScreen().availableGeometry()
        self.resize(min(1120, int(scr.width() * 0.8)), min(840, int(scr.height() * 0.85)))
        self._toggle_crop(False)

    def _apply_theme(self) -> None:
        th = self.theme
        t = th.t
        pal = self.area.viewport().palette()
        pal.setBrush(self.area.viewport().backgroundRole(), _checker(t.checker_a, t.checker_b))
        self.area.viewport().setPalette(pal)
        self.act_crop.setIcon(th.icon("crop"))
        self.act_undo.setIcon(th.icon("undo"))
        self.act_orig.setIcon(th.icon("reset"))
        self.act_fit.setIcon(th.icon("fit"))
        self.btn_apply.setIcon(th.icon("check", t.on_accent))
        self.btn_cancel_crop.setIcon(th.icon("x"))
        self.b_save.setIcon(th.icon("save"))
        self.b_save_as.setIcon(th.icon("save_as"))
        self.b_copy.setIcon(th.icon("copy"))

    @staticmethod
    def _section(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("section")
        return lbl

    # ------------------------------------------------------------------ state
    @property
    def image(self) -> np.ndarray:
        return self._img

    def current_format(self) -> str:
        b = self.fmt_group.checkedButton()
        return b.property("fmt") if b else "png"

    def _set_image(self, img: np.ndarray, push: bool = True) -> None:
        if push:
            self._undo.append(self._img)
            del self._undo[:-UNDO_LIMIT]
            self._dirty = True
        self._img = img
        self.canvas.set_image(img)
        h, w = img.shape[:2]
        self.setWindowTitle(tr("ed.title", w=f"{w:,}", h=f"{h:,}"))
        self.act_undo.setEnabled(bool(self._undo))
        self._refresh()

    def showEvent(self, e):
        super().showEvent(e)
        if not getattr(self, "_fitted", False):
            self._fitted = True
            self.canvas.fit_width()
            self._refresh()

    def _refresh(self) -> None:
        w, h = self.canvas.image_size()
        zoom = round(self.canvas.zoom * 100)
        c = self.canvas.crop
        if self.canvas.crop_mode and c is not None and not c.isEmpty():
            txt = tr("ed.status_crop", zoom=zoom, cw=f"{c.width():,}", ch=f"{c.height():,}",
                     w=f"{w:,}", h=f"{h:,}")
        else:
            txt = tr("ed.status", zoom=zoom, w=f"{w:,}", h=f"{h:,}")
        self.status.setText(txt)
        has_crop = c is not None and not c.isEmpty()
        self.btn_apply.setEnabled(self.canvas.crop_mode and has_crop)

    # ------------------------------------------------------------------ crop
    def _toggle_crop(self, on: bool) -> None:
        self.canvas.set_crop_mode(on)
        self.btn_apply.setVisible(on)
        self.btn_cancel_crop.setVisible(on)
        self.crop_hint.setVisible(on)
        self._refresh()

    def apply_crop(self) -> None:
        c = self.canvas.crop
        if not self.canvas.crop_mode or c is None or c.isEmpty():
            return
        cropped = np.ascontiguousarray(self._img[c.top():c.top() + c.height(), c.left():c.left() + c.width()])
        self.act_crop.setChecked(False)
        self._set_image(cropped)
        self.canvas.fit_width()

    def undo(self) -> None:
        if self._undo:
            self._set_image(self._undo.pop(), push=False)
            self._dirty = True
            self.canvas.fit_width()

    def reset_original(self) -> None:
        if self._img is not self._original:
            self._set_image(self._original)
            self.canvas.fit_width()

    def keyPressEvent(self, e):
        if self.canvas.crop_mode and e.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.apply_crop()
        elif self.canvas.crop_mode and e.key() == Qt.Key.Key_Escape:
            self.act_crop.setChecked(False)
        else:
            super().keyPressEvent(e)

    # ------------------------------------------------------------------ output
    def _after_save(self, paths: list[Path] | None) -> None:
        if paths:
            self._dirty = False
            self.statusBar().showMessage(tr("status.saved", file=str(paths[0])), 6000)
            self.saved.emit(paths)

    def save(self) -> None:
        fmt = self.current_format()
        path = default_path(self.settings, self.source_title, fmt)
        self._after_save(save_with_ui(self, self._img, path, fmt, self.settings, self.source_title))

    def save_as(self) -> None:
        fmt = self.current_format()
        start = default_path(self.settings, self.source_title, fmt)
        filters = [tr("dlg.png"), tr("dlg.jpg")]
        if fmt == "jpg":
            filters.reverse()
        fn, chosen = QFileDialog.getSaveFileName(self, tr("ed.save_as"), str(start), ";;".join(filters))
        if not fn:
            return
        default_fmt = "jpg" if chosen == tr("dlg.jpg") else "png"
        fmt = exporter.format_from_path(fn, default_fmt)
        path = Path(fn)
        if path.suffix.lower() not in (".png", ".jpg", ".jpeg"):
            path = path.with_suffix("." + fmt)
        self._after_save(save_with_ui(self, self._img, path, fmt, self.settings, self.source_title))

    def copy(self) -> None:
        img = self.canvas.qimage()
        if img is None:
            return
        if self._img.shape[0] > 20000:
            QMessageBox.information(self, APP_NAME, tr("ed.copy_large"))
        QGuiApplication.clipboard().setImage(img.copy())
        self.statusBar().showMessage(tr("ed.copied"), 3000)

    def closeEvent(self, e):
        if self._dirty:
            r = QMessageBox.question(self, APP_NAME, tr("ed.unsaved"),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if r != QMessageBox.StandardButton.Yes:
                e.ignore()
                return
        super().closeEvent(e)
