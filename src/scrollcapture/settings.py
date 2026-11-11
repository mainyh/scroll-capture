"""User settings persisted as JSON in %APPDATA%\\ScrollCapture\\settings.json."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

log = logging.getLogger(__name__)


def app_data_dir() -> Path:
    base = os.environ.get("APPDATA") or str(Path.home())
    d = Path(base) / "ScrollCapture"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_save_dir() -> str:
    pictures = ""
    try:
        from PySide6.QtCore import QStandardPaths
        pictures = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
    except Exception:
        pass
    if not pictures:
        pictures = str(Path.home() / "Pictures")
    return str(Path(pictures) / "ScrollCapture")


@dataclass
class Settings:
    language: str = "system"          # system | ko | en
    save_dir: str = ""
    image_format: str = "png"         # png | jpg
    jpg_quality: int = 90
    filename_pattern: str = "ScrollCapture_{title}_{datetime}"
    save_instantly: bool = False
    open_folder_after_save: bool = False
    embed_metadata: bool = True
    start_from_top: bool = True
    scroll_notches: int = 0           # 0 = auto
    frame_delay_ms: int = 250
    max_height: int = 30000
    remove_sticky: bool = True
    hotkey: str = "Ctrl+Shift+S"

    @property
    def path(self) -> Path:
        return app_data_dir() / "settings.json"

    @classmethod
    def load(cls) -> "Settings":
        s = cls()
        try:
            p = app_data_dir() / "settings.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                names = {f.name for f in fields(cls)}
                for k, v in data.items():
                    if k in names and isinstance(v, type(getattr(s, k))):
                        setattr(s, k, v)
        except Exception:
            log.exception("failed to load settings")
        if not s.save_dir:
            s.save_dir = default_save_dir()
        s.image_format = "jpg" if s.image_format == "jpg" else "png"
        s.jpg_quality = max(60, min(100, s.jpg_quality))
        s.max_height = max(2000, min(200000, s.max_height))
        s.frame_delay_ms = max(50, min(3000, s.frame_delay_ms))
        return s

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            log.exception("failed to save settings")
