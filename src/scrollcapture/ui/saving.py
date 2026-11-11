"""Save helpers shared by the editor and the 'save instantly' flow."""
from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from .. import APP_NAME, __version__
from ..core import exporter
from ..i18n import tr
from ..settings import Settings

log = logging.getLogger(__name__)


def default_path(settings: Settings, title: str, fmt: str) -> Path:
    name = exporter.build_filename(settings.filename_pattern, title, fmt)
    return exporter.unique_path(settings.save_dir, name)


def save_with_ui(parent: QWidget | None, img: np.ndarray, path: Path, fmt: str,
                 settings: Settings, title: str) -> list[Path] | None:
    """Save, asking the user what to do when a JPG is too tall. None = cancelled/failed."""
    meta = None
    if settings.embed_metadata and fmt == "png":
        meta = {"Software": f"{APP_NAME} {__version__}", "Title": title,
                "Creation Time": datetime.now().isoformat(timespec="seconds")}
    split = False
    if fmt == "jpg" and img.shape[0] > exporter.JPEG_MAX:
        box = QMessageBox(QMessageBox.Icon.Warning, APP_NAME, tr("err.jpg_limit", h=f"{img.shape[0]:,}"),
                          parent=parent)
        b_png = box.addButton(tr("err.jpg_png"), QMessageBox.ButtonRole.AcceptRole)
        b_split = box.addButton(tr("err.jpg_split"), QMessageBox.ButtonRole.ActionRole)
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        if box.clickedButton() is b_png:
            fmt, path = "png", path.with_suffix(".png")
        elif box.clickedButton() is b_split:
            split = True
        else:
            return None
    QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
    try:
        paths = exporter.save_image(img, path, fmt, jpg_quality=settings.jpg_quality,
                                    metadata=meta, split_jpeg=split)
    except Exception as e:  # disk full, permissions, ...
        log.exception("save failed")
        QApplication.restoreOverrideCursor()
        QMessageBox.critical(parent, APP_NAME, tr("dlg.save_failed", err=e))
        return None
    QApplication.restoreOverrideCursor()
    log.info("saved %s", paths)
    if settings.open_folder_after_save and paths:
        try:
            os.startfile(paths[0].parent)  # noqa: S606 - opening Explorer on purpose
        except OSError:
            pass
    return paths
