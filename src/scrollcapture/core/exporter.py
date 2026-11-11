"""Saving captures as PNG / JPG."""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image, PngImagePlugin

JPEG_MAX = 65535
_INVALID = re.compile(r'[\\/:*?"<>|\x00-\x1f]+')

Image.MAX_IMAGE_PIXELS = None  # long captures are legitimately huge


class JpegTooLarge(Exception):
    pass


def sanitize(name: str, limit: int = 40) -> str:
    name = _INVALID.sub("_", name).strip(" ._")
    name = re.sub(r"\s+", " ", name)
    return name[:limit].rstrip(" ._")


def build_filename(pattern: str, title: str, fmt: str, when: datetime | None = None) -> str:
    when = when or datetime.now()
    title = sanitize(title) or "capture"
    try:
        base = pattern.format(title=title, date=when.strftime("%Y%m%d"),
                              time=when.strftime("%H%M%S"),
                              datetime=when.strftime("%Y%m%d_%H%M%S"))
    except (KeyError, IndexError, ValueError):
        base = f"ScrollCapture_{title}_{when:%Y%m%d_%H%M%S}"
    base = sanitize(base, limit=150) or "ScrollCapture"
    return f"{base}.{ 'jpg' if fmt == 'jpg' else 'png'}"


def unique_path(folder: str | Path, filename: str) -> Path:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    p = folder / filename
    stem, suffix = p.stem, p.suffix
    i = 1
    while p.exists():
        p = folder / f"{stem}_{i}{suffix}"
        i += 1
    return p


def format_from_path(path: str | Path, default: str = "png") -> str:
    ext = Path(path).suffix.lower()
    if ext in (".jpg", ".jpeg"):
        return "jpg"
    if ext == ".png":
        return "png"
    return default


def save_image(img: np.ndarray, path: str | Path, fmt: str = "png", *, jpg_quality: int = 90,
               metadata: dict[str, str] | None = None, split_jpeg: bool = False) -> list[Path]:
    """Save ``img`` (RGB uint8). Returns the written paths (several when a JPG is split)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "jpg":
        h = img.shape[0]
        if h > JPEG_MAX or img.shape[1] > JPEG_MAX:
            if not split_jpeg:
                raise JpegTooLarge(h)
            return _save_jpeg_parts(img, path, jpg_quality)
        Image.fromarray(img).save(path, "JPEG", quality=int(jpg_quality), subsampling=0, optimize=True)
        return [path]

    pnginfo = None
    if metadata:
        pnginfo = PngImagePlugin.PngInfo()
        for k, v in metadata.items():
            pnginfo.add_itxt(k, str(v))
    Image.fromarray(img).save(path, "PNG", compress_level=6, pnginfo=pnginfo)
    return [path]


def _save_jpeg_parts(img: np.ndarray, path: Path, quality: int) -> list[Path]:
    part_h = 60000
    out = []
    n = (img.shape[0] + part_h - 1) // part_h
    for i in range(n):
        p = path.with_name(f"{path.stem}_part{i + 1}{path.suffix}")
        Image.fromarray(img[i * part_h:(i + 1) * part_h]).save(p, "JPEG", quality=int(quality),
                                                                subsampling=0, optimize=True)
        out.append(p)
    return out
