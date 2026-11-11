"""Screen pixel capture (BitBlt via mss). Works for GPU-accelerated apps too."""
from __future__ import annotations

import numpy as np
import mss

from .win32utils import Rect

_MSS = getattr(mss, "MSS", None) or mss.mss


class Grabber:
    """Not thread-safe: create one per thread."""

    def __init__(self) -> None:
        self._sct = _MSS()

    def grab(self, rect: Rect) -> np.ndarray:
        """Return an RGB ``uint8`` array of shape (h, w, 3)."""
        shot = self._sct.grab({"left": rect.left, "top": rect.top,
                               "width": rect.width, "height": rect.height})
        bgra = np.frombuffer(shot.bgra, dtype=np.uint8).reshape(shot.height, shot.width, 4)
        return np.ascontiguousarray(bgra[:, :, 2::-1])

    def close(self) -> None:
        try:
            self._sct.close()
        except Exception:
            pass

    def __enter__(self) -> "Grabber":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
