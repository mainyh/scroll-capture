"""Compact main window: target card, pick buttons, format/folder, start button."""
from __future__ import annotations

import ctypes.wintypes as wt
import os

from PySide6.QtCore import QFileInfo, QSize, Qt, Signal
from PySide6.QtGui import QIcon, QKeySequence
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFileDialog, QFileIconProvider, QFrame,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMenu,
                               QPushButton, QVBoxLayout, QWidget)

from .. import APP_NAME
from ..core import win32utils as w32
from ..i18n import tr
from ..settings import Settings
from . import theme

HOTKEY_CAPTURE = 1
HOTKEY_ESC = 2


def parse_hotkey(text: str) -> tuple[int, int] | None:
    """'Ctrl+Shift+S' -> (MOD_*, VK). None if unsupported."""
    seq = QKeySequence(text)
    if seq.isEmpty():
        return None
    combo = seq[0]
    mods = combo.keyboardModifiers()
    key = combo.key()
    m = 0
    if mods & Qt.KeyboardModifier.ControlModifier:
        m |= w32.MOD_CONTROL
    if mods & Qt.KeyboardModifier.ShiftModifier:
        m |= w32.MOD_SHIFT
    if mods & Qt.KeyboardModifier.AltModifier:
        m |= w32.MOD_ALT
    if mods & Qt.KeyboardModifier.MetaModifier:
        m |= w32.MOD_WIN
    k = int(key.value) if hasattr(key, "value") else int(key)
    if Qt.Key.Key_A.value <= k <= Qt.Key.Key_Z.value or Qt.Key.Key_0.value <= k <= Qt.Key.Key_9.value:
        vk = k
    elif Qt.Key.Key_F1.value <= k <= Qt.Key.Key_F24.value:
        vk = 0x70 + (k - Qt.Key.Key_F1.value)
    elif k == Qt.Key.Key_Print.value:
        vk = 0x2C
    elif k == Qt.Key.Key_Pause.value:
        vk = 0x13
    elif k == Qt.Key.Key_Insert.value:
        vk = 0x2D
    else:
        return None
    return m, vk


class MainWindow(QMainWindow):
    pickRequested = Signal(str)          # "window" | "area"
    windowChosen = Signal(object)        # WindowInfo
    startRequested = Signal()
    settingsRequested = Signal()
    hotkeyPressed = Signal(int)

    def __init__(self, settings: Settings):
        super().__init__()
        self.s = settings
        self.setWindowTitle(APP_NAME)
        self._icons = QFileIconProvider()

        self.theme = theme.current()

        root = QWidget()
        root.setObjectName("page")
        v = QVBoxLayout(root)
        v.setContentsMargins(18, 18, 18, 16)
        v.setSpacing(14)

        # target card
        card = QFrame()
        card.setObjectName("card")
        cl = QHBoxLayout(card)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(12)
        tile = QFrame()
        tile.setObjectName("iconTile")
        tile.setFixedSize(42, 42)
        tile_l = QVBoxLayout(tile)
        tile_l.setContentsMargins(0, 0, 0, 0)
        self.t_icon = QLabel()
        self.t_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tile_l.addWidget(self.t_icon)
        tl = QVBoxLayout()
        tl.setSpacing(2)
        self.t_title = QLabel()
        self.t_title.setObjectName("title")
        self.t_title.setMinimumWidth(10)
        self.t_sub = QLabel()
        self.t_sub.setObjectName("muted")
        tl.addWidget(self.t_title)
        tl.addWidget(self.t_sub)
        cl.addWidget(tile)
        cl.addLayout(tl, 1)
        v.addWidget(card)

        # pick buttons
        row = QHBoxLayout()
        row.setSpacing(8)
        self.b_pick = QPushButton(tr("main.pick_window"))
        self.b_area = QPushButton(tr("main.select_area"))
        self.b_list = QPushButton(tr("main.window_list"))
        self.b_pick.clicked.connect(lambda: self.pickRequested.emit("window"))
        self.b_area.clicked.connect(lambda: self.pickRequested.emit("area"))
        self.b_list.clicked.connect(self._show_list)
        for b in (self.b_pick, self.b_area, self.b_list):
            b.setIconSize(QSize(18, 18))
            row.addWidget(b, 1)
        v.addLayout(row)

        # settings form
        form = QGridLayout()
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(12)
        form.setColumnMinimumWidth(0, 70)
        form.setColumnStretch(1, 1)

        seg = QHBoxLayout()
        seg.setSpacing(0)
        self.fmt_group = QButtonGroup(self)
        for i, (key, text) in enumerate((("png", "PNG"), ("jpg", "JPG"))):
            b = QPushButton(text)
            b.setCheckable(True)
            b.setObjectName("segLeft" if i == 0 else "segRight")
            b.setProperty("fmt", key)
            b.setChecked(key == settings.image_format)
            self.fmt_group.addButton(b)
            seg.addWidget(b)
        seg.addStretch(1)
        self.fmt_group.buttonClicked.connect(self._fmt_changed)
        form.addWidget(self._label(tr("main.format")), 0, 0)
        form.addLayout(seg, 0, 1)

        drow = QHBoxLayout()
        drow.setSpacing(6)
        self.dir = QLineEdit(settings.save_dir)
        self.dir.setCursorPosition(0)
        self.dir.editingFinished.connect(self._dir_changed)
        self.b_browse = QPushButton()
        self.b_browse.setToolTip(tr("main.browse"))
        self.b_browse.setFixedSize(36, 36)
        self.b_browse.clicked.connect(self._browse)
        drow.addWidget(self.dir, 1)
        drow.addWidget(self.b_browse)
        form.addWidget(self._label(tr("main.save_to")), 1, 0)
        form.addLayout(drow, 1, 1)

        orow = QHBoxLayout()
        orow.setSpacing(18)
        self.c_top = QCheckBox(tr("main.opt_top"))
        self.c_top.setChecked(settings.start_from_top)
        self.c_inst = QCheckBox(tr("main.opt_instant"))
        self.c_inst.setChecked(settings.save_instantly)
        self.c_top.toggled.connect(self._opts_changed)
        self.c_inst.toggled.connect(self._opts_changed)
        orow.addWidget(self.c_top)
        orow.addWidget(self.c_inst)
        orow.addStretch(1)
        form.addWidget(self._label(tr("main.options")), 2, 0)
        form.addLayout(orow, 2, 1)
        v.addLayout(form)

        # start
        srow = QHBoxLayout()
        srow.setSpacing(8)
        self.b_start = QPushButton()
        self.b_start.setObjectName("primary")
        self.b_start.setIconSize(QSize(18, 18))
        self.b_start.setMinimumHeight(46)
        self.b_start.clicked.connect(self.startRequested)
        self.b_settings = QPushButton()
        self.b_settings.setToolTip(tr("main.settings"))
        self.b_settings.setFixedSize(46, 46)
        self.b_settings.setIconSize(QSize(20, 20))
        self.b_settings.clicked.connect(self.settingsRequested)
        srow.addWidget(self.b_start, 1)
        srow.addWidget(self.b_settings)
        v.addSpacing(2)
        v.addLayout(srow)

        self.setCentralWidget(root)
        self.status = QLabel(tr("status.ready"))
        self.statusBar().addWidget(self.status, 1)
        self.statusBar().setSizeGripEnabled(False)

        self._target = None
        self._refresh_icons()
        self.theme.changed.connect(self._refresh_icons)
        self.update_hotkey_label()
        self.setFixedWidth(440)
        self.adjustSize()

    def _refresh_icons(self) -> None:
        th = self.theme
        self.b_pick.setIcon(th.icon("target"))
        self.b_area.setIcon(th.icon("area"))
        self.b_list.setIcon(th.icon("list"))
        self.b_browse.setIcon(th.icon("folder"))
        self.b_settings.setIcon(th.icon("sliders"))
        self.b_start.setIcon(th.icon("record", th.t.on_accent))
        self.set_target(self._target)

    @staticmethod
    def _label(text: str) -> QLabel:
        l = QLabel(text)
        l.setObjectName("muted")
        return l

    # ------------------------------------------------------------------ display
    def update_hotkey_label(self) -> None:
        key = QKeySequence(self.s.hotkey).toString(QKeySequence.SequenceFormat.NativeText) or self.s.hotkey
        self.b_start.setText("  " + tr("main.start", key=key))

    def set_status(self, text: str) -> None:
        self.status.setText(text)

    def set_target(self, target) -> None:
        self._target = target
        th = self.theme
        if target is None:
            self.t_title.setText(tr("main.no_target"))
            self.t_sub.setText(tr("main.no_target_sub"))
            self.t_icon.setPixmap(th.icon("window", th.t.accent).pixmap(QSize(22, 22)))
            return
        fm = self.t_title.fontMetrics()
        self.t_title.setText(fm.elidedText(target.title or target.exe_name, Qt.TextElideMode.ElideRight, 300))
        self.t_title.setToolTip(target.title)
        parts = [target.exe_name]
        if target.region_size:
            key = "main.area_manual" if target.manual else "main.area_auto"
            parts.append(tr(key, w=target.region_size[0], h=target.region_size[1]))
        self.t_sub.setText(" · ".join(p for p in parts if p))
        icon = self._icons.icon(QFileInfo(target.exe_path)) if target.exe_path else QIcon()
        if icon.isNull():
            icon = th.icon("window", th.t.accent)
        self.t_icon.setPixmap(icon.pixmap(QSize(28, 28)))

    # ------------------------------------------------------------------ handlers
    def _fmt_changed(self, b) -> None:
        self.s.image_format = b.property("fmt")
        self.s.save()

    def sync_from_settings(self) -> None:
        for b in self.fmt_group.buttons():
            b.setChecked(b.property("fmt") == self.s.image_format)
        self.dir.setText(self.s.save_dir)
        self.c_top.setChecked(self.s.start_from_top)
        self.c_inst.setChecked(self.s.save_instantly)
        self.update_hotkey_label()

    def _dir_changed(self) -> None:
        t = self.dir.text().strip()
        if t and t != self.s.save_dir:
            self.s.save_dir = t
            self.s.save()

    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("main.browse"), self.dir.text())
        if d:
            self.dir.setText(os.path.normpath(d))
            self._dir_changed()

    def _opts_changed(self) -> None:
        self.s.start_from_top = self.c_top.isChecked()
        self.s.save_instantly = self.c_inst.isChecked()
        self.s.save()

    def _show_list(self) -> None:
        menu = QMenu(self)
        wins = w32.enum_top_windows(os.getpid(), include_minimized=True, require_title=True)
        if not wins:
            a = menu.addAction(tr("main.no_windows"))
            a.setEnabled(False)
        for win in wins[:40]:
            icon = self._icons.icon(QFileInfo(win.exe_path)) if win.exe_path else QIcon()
            title = win.title if len(win.title) <= 70 else win.title[:67] + "…"
            act = menu.addAction(icon, f"{title}   ·  {win.exe_name}")
            act.triggered.connect(lambda _=False, wi=win: self.windowChosen.emit(wi))
        menu.exec(self.b_list.mapToGlobal(self.b_list.rect().bottomLeft()))

    # ------------------------------------------------------------------ hotkeys
    def register_hotkey(self, hid: int, text_or_vk) -> bool:
        if isinstance(text_or_vk, str):
            parsed = parse_hotkey(text_or_vk)
            if not parsed:
                return False
            mods, vk = parsed
        else:
            mods, vk = 0, text_or_vk
        w32.unregister_hotkey(int(self.winId()), hid)
        return w32.register_hotkey(int(self.winId()), hid, mods, vk)

    def unregister_hotkey(self, hid: int) -> None:
        w32.unregister_hotkey(int(self.winId()), hid)

    def nativeEvent(self, event_type, message):
        try:
            if event_type == b"windows_generic_MSG" or event_type == "windows_generic_MSG":
                msg = wt.MSG.from_address(int(message))
                if msg.message == w32.WM_HOTKEY:
                    self.hotkeyPressed.emit(int(msg.wParam))
                    return True, 0
        except Exception:
            pass
        return super().nativeEvent(event_type, message)
