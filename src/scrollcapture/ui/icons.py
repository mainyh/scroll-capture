"""Monochrome line icons (24×24, drawn for this project) rendered from inline SVG."""
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from PySide6.QtCore import QByteArray, QRectF, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

# Bodies use {c} for the colour (for fills); strokes inherit from the root element.
_BODIES: dict[str, str] = {
    "target": '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.5"/>'
              '<circle cx="12" cy="12" r="1.2" fill="{c}" stroke="none"/>',
    "area": '<path d="M4 8V5.5A1.5 1.5 0 0 1 5.5 4H8M16 4h2.5A1.5 1.5 0 0 1 20 5.5V8M20 16v2.5'
            'a1.5 1.5 0 0 1-1.5 1.5H16M8 20H5.5A1.5 1.5 0 0 1 4 18.5V16"/>',
    "list": '<path d="M9 6.5h11M9 12h11M9 17.5h11"/>'
            '<circle cx="4.75" cy="6.5" r="1" fill="{c}"/><circle cx="4.75" cy="12" r="1" fill="{c}"/>'
            '<circle cx="4.75" cy="17.5" r="1" fill="{c}"/>',
    "sliders": '<path d="M4 7h9M17 7h3M4 17h3M11 17h9"/><circle cx="15" cy="7" r="2"/><circle cx="9" cy="17" r="2"/>',
    "record": '<circle cx="12" cy="12" r="5" fill="{c}" stroke="none"/>',
    "crop": '<path d="M6.5 3v12.5a2 2 0 0 0 2 2H21"/><path d="M17.5 21V8.5a2 2 0 0 0-2-2H3"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10.5a5.5 5.5 0 0 1 0 11H11"/>',
    "reset": '<path d="M3.5 12a8.5 8.5 0 1 0 2.6-6.1L3.5 8.5"/><path d="M3.5 3.5v5h5"/>',
    "save": '<path d="M12 3.5v11"/><path d="m7.5 10 4.5 4.5 4.5-4.5"/><path d="M4.5 19.5h15"/>',
    "save_as": '<path d="M4.5 19.5h7"/><path d="M15 19.5l1-3.5 4.5-4.5a1.6 1.6 0 0 1 2.3 2.3L18.3 18.3z"/>'
               '<path d="M10 3.5v9"/><path d="m6 9 4 4 4-4"/>',
    "copy": '<rect x="8.5" y="8.5" width="12" height="12" rx="2"/><path d="M15.5 8.5V5.5a2 2 0 0 0-2-2h-8a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h3"/>',
    "check": '<path d="M4.5 12.5 9.5 17.5 19.5 6.5"/>',
    "x": '<path d="M6 6l12 12M18 6 6 18"/>',
    "stop": '<rect x="7" y="7" width="10" height="10" rx="1.5" fill="{c}" stroke="none"/>',
    "folder": '<path d="M3.5 7.5a2 2 0 0 1 2-2h4l2 2.5h7a2 2 0 0 1 2 2v7.5a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2z"/>',
    "fit": '<path d="M3.5 12h17"/><path d="m7.5 8-4 4 4 4"/><path d="m16.5 8 4 4-4 4"/>',
    "window": '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><path d="M3.5 9h17"/>'
              '<circle cx="6.5" cy="6.8" r=".6" fill="{c}"/><circle cx="8.6" cy="6.8" r=".6" fill="{c}"/>',
    "chevron_down": '<path d="m6 9 6 6 6-6"/>',
    "chevron_up": '<path d="m6 15 6-6 6 6"/>',
    "github": '<path d="M9 19c-4.3 1.4-4.3-2.5-6-3m12 5v-3.5c0-1 .1-1.4-.5-2 2.8-.3 5.5-1.4 5.5-6a4.6 4.6 0 0 0-1.3-3.2'
              ' 4.2 4.2 0 0 0-.1-3.2s-1.1-.3-3.5 1.3a12.3 12.3 0 0 0-6.2 0C6.5 2.8 5.4 3.1 5.4 3.1a4.2 4.2 0 0 0-.1'
              ' 3.2A4.6 4.6 0 0 0 4 9.5c0 4.6 2.7 5.7 5.5 6-.6.6-.6 1.2-.5 2V21"/>',
    "doc": '<path d="M14 3.5H7a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8.5z"/><path d="M14 3.5v5h5M9 13h6M9 16.5h4"/>',
}


def svg(name: str, color: str, stroke: float = 1.8) -> str:
    body = _BODIES[name].replace("{c}", color)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def pixmap(name: str, color: str, size: int, dpr: float = 2.0) -> QPixmap:
    px = QPixmap(round(size * dpr), round(size * dpr))
    px.fill(Qt.GlobalColor.transparent)
    r = QSvgRenderer(QByteArray(svg(name, color).encode()))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    r.render(p, QRectF(0, 0, px.width(), px.height()))
    p.end()
    px.setDevicePixelRatio(dpr)
    return px


def icon(name: str, color: str, disabled: str | None = None) -> QIcon:
    ic = QIcon()
    for s in (16, 20, 24, 32):
        ic.addPixmap(pixmap(name, color, s), QIcon.Mode.Normal)
        if disabled:
            ic.addPixmap(pixmap(name, disabled, s), QIcon.Mode.Disabled)
    return ic


_cache_dir = Path(tempfile.gettempdir()) / "ScrollCapture-ui"


def svg_file(name: str, color: str, stroke: float = 2.2) -> str:
    """Write the icon as an .svg file (for Qt style sheets) and return a QSS-friendly path."""
    data = svg(name, color, stroke)
    key = hashlib.sha1(data.encode()).hexdigest()[:10]
    _cache_dir.mkdir(parents=True, exist_ok=True)
    p = _cache_dir / f"{name}-{key}.svg"
    if not p.exists():
        p.write_text(data, encoding="utf-8")
    return p.as_posix()
