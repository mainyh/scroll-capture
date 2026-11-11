"""Settings dialog (General / Capture / Hotkeys / About)."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QHBoxLayout, QKeySequenceEdit, QLabel, QLineEdit, QMessageBox,
                               QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from .. import APP_NAME, REPO_URL, __version__
from ..i18n import tr
from ..settings import Settings
from . import theme
from .resources import app_icon, resource_path


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.s = settings
        self.setWindowTitle(tr("set.title"))
        self.setMinimumWidth(560)
        tabs = QTabWidget()
        tabs.addTab(self._general(), tr("set.tab_general"))
        tabs.addTab(self._capture(), tr("set.tab_capture"))
        tabs.addTab(self._hotkeys(), tr("set.tab_hotkeys"))
        tabs.addTab(self._about(), tr("set.tab_about"))
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(tr("set.ok"))
        bb.button(QDialogButtonBox.StandardButton.Ok).setObjectName("primary")
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("set.cancel"))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(14)
        lay.addWidget(tabs)
        lay.addWidget(bb)

    # ------------------------------------------------------------------ tabs
    def _general(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setHorizontalSpacing(16)
        f.setVerticalSpacing(12)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.lang = QComboBox()
        for code, text in (("system", tr("set.lang_system")), ("ko", "한국어"), ("en", "English")):
            self.lang.addItem(text, code)
        self.lang.setCurrentIndex(max(0, self.lang.findData(self.s.language)))
        f.addRow(tr("set.language"), self.lang)

        row = QHBoxLayout()
        self.dir = QLineEdit(self.s.save_dir)
        b = QPushButton()
        b.setIcon(theme.current().icon("folder"))
        b.setFixedSize(36, 36)
        b.clicked.connect(self._browse)
        row.addWidget(self.dir)
        row.addWidget(b)
        f.addRow(tr("set.save_dir"), row)

        self.fmt = QComboBox()
        self.fmt.addItem("PNG", "png")
        self.fmt.addItem("JPG", "jpg")
        self.fmt.setCurrentIndex(self.fmt.findData(self.s.image_format))
        f.addRow(tr("set.format"), self.fmt)

        self.quality = QSpinBox()
        self.quality.setRange(60, 100)
        self.quality.setValue(self.s.jpg_quality)
        f.addRow(tr("set.jpg_quality"), self.quality)

        self.pattern = QLineEdit(self.s.filename_pattern)
        f.addRow(tr("set.pattern"), self.pattern)
        help_ = QLabel(tr("set.pattern_help"))
        help_.setObjectName("muted")
        help_.setWordWrap(True)
        f.addRow("", help_)

        self.instant = QCheckBox(tr("set.instant"))
        self.instant.setChecked(self.s.save_instantly)
        self.open_folder = QCheckBox(tr("set.open_folder"))
        self.open_folder.setChecked(self.s.open_folder_after_save)
        self.meta = QCheckBox(tr("set.metadata"))
        self.meta.setChecked(self.s.embed_metadata)
        for c in (self.instant, self.open_folder, self.meta):
            f.addRow("", c)
        return w

    def _capture(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setHorizontalSpacing(16)
        f.setVerticalSpacing(12)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.top = QCheckBox(tr("set.start_top"))
        self.top.setChecked(self.s.start_from_top)
        f.addRow("", self.top)
        self.notches = QComboBox()
        self.notches.addItem(tr("set.scroll_auto"), 0)
        for n in (1, 2, 3, 5, 8, 12):
            self.notches.addItem(tr("set.scroll_notches", n=n), n)
        self.notches.setCurrentIndex(max(0, self.notches.findData(self.s.scroll_notches)))
        f.addRow(tr("set.scroll_amount"), self.notches)
        self.delay = QSpinBox()
        self.delay.setRange(50, 3000)
        self.delay.setSingleStep(50)
        self.delay.setSuffix(" ms")
        self.delay.setValue(self.s.frame_delay_ms)
        f.addRow(tr("set.delay"), self.delay)
        self.maxh = QSpinBox()
        self.maxh.setRange(2000, 200000)
        self.maxh.setSingleStep(5000)
        self.maxh.setGroupSeparatorShown(True)
        self.maxh.setSuffix(" px")
        self.maxh.setValue(self.s.max_height)
        f.addRow(tr("set.max_height"), self.maxh)
        self.sticky = QCheckBox(tr("set.sticky"))
        self.sticky.setChecked(self.s.remove_sticky)
        f.addRow("", self.sticky)
        return w

    def _hotkeys(self) -> QWidget:
        w = QWidget()
        f = QFormLayout(w)
        f.setHorizontalSpacing(16)
        f.setVerticalSpacing(12)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.hotkey = QKeySequenceEdit(QKeySequence(self.s.hotkey))
        self.hotkey.setMaximumSequenceLength(1)
        f.addRow(tr("set.hotkey_capture"), self.hotkey)
        esc = QLineEdit("Esc")
        esc.setEnabled(False)
        f.addRow(tr("set.hotkey_stop"), esc)
        note = QLabel(tr("set.hotkey_note"))
        note.setObjectName("muted")
        f.addRow("", note)
        return w

    def _about(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(6)
        head = QHBoxLayout()
        head.setSpacing(14)
        logo = QLabel()
        logo.setPixmap(app_icon().pixmap(QSize(56, 56)))
        names = QVBoxLayout()
        names.setSpacing(2)
        name = QLabel(APP_NAME)
        name.setObjectName("hero")
        ver = QLabel(tr("set.version", v=__version__))
        ver.setObjectName("muted")
        names.addWidget(name)
        names.addWidget(ver)
        head.addWidget(logo)
        head.addLayout(names, 1)
        v.addLayout(head)
        v.addSpacing(10)
        v.addWidget(QLabel(tr("set.license")))
        v.addSpacing(8)
        th = theme.current()
        row = QHBoxLayout()
        row.setSpacing(8)
        b_gh = QPushButton(tr("set.github"))
        b_gh.setIcon(th.icon("github"))
        b_gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO_URL)))
        b = QPushButton(tr("set.notices"))
        b.setIcon(th.icon("doc"))
        b.clicked.connect(self._open_notices)
        row.addWidget(b_gh)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)
        v.addStretch(1)
        return w

    # ------------------------------------------------------------------ actions
    def _browse(self) -> None:
        d = QFileDialog.getExistingDirectory(self, tr("main.browse"), self.dir.text())
        if d:
            self.dir.setText(d)

    def _open_notices(self) -> None:
        p = resource_path("THIRD_PARTY_NOTICES.md")
        if p and Path(p).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(p)))
        else:
            QDesktopServices.openUrl(QUrl(REPO_URL + "/blob/main/THIRD_PARTY_NOTICES.md"))

    def accept(self) -> None:
        s = self.s
        new_lang = self.lang.currentData()
        lang_changed = new_lang != s.language
        s.language = new_lang
        s.save_dir = self.dir.text().strip() or s.save_dir
        s.image_format = self.fmt.currentData()
        s.jpg_quality = self.quality.value()
        s.filename_pattern = self.pattern.text().strip() or "ScrollCapture_{title}_{datetime}"
        s.save_instantly = self.instant.isChecked()
        s.open_folder_after_save = self.open_folder.isChecked()
        s.embed_metadata = self.meta.isChecked()
        s.start_from_top = self.top.isChecked()
        s.scroll_notches = int(self.notches.currentData())
        s.frame_delay_ms = self.delay.value()
        s.max_height = self.maxh.value()
        s.remove_sticky = self.sticky.isChecked()
        seq = self.hotkey.keySequence().toString(QKeySequence.SequenceFormat.PortableText)
        if seq:
            s.hotkey = seq
        s.save()
        if lang_changed:
            QMessageBox.information(self, APP_NAME, tr("set.lang_restart"))
        super().accept()
