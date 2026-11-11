"""Locating bundled files (works from source and from the PyInstaller exe)."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon

_PKG = Path(__file__).resolve().parent.parent


def resource_path(name: str) -> Path | None:
    candidates = [_PKG / "resources" / name]
    base = getattr(sys, "_MEIPASS", None)
    if base:
        candidates.insert(0, Path(base) / name)
        candidates.insert(0, Path(base) / "scrollcapture" / "resources" / name)
    candidates.append(_PKG.parent.parent / name)  # repo root when running from source
    for c in candidates:
        if c.exists():
            return c
    return None


def app_icon() -> QIcon:
    p = resource_path("icon.ico")
    return QIcon(str(p)) if p else QIcon()

