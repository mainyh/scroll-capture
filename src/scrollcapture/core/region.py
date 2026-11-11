"""Find the part of a window that actually scrolls."""
from __future__ import annotations

import logging

import numpy as np

from .capture import wait_stable
from .grabber import Grabber
from .win32utils import (Rect, WHEEL_DELTA, client_rect, get_cursor_pos, raw_window_rect,
                         send_wheel, set_cursor_pos, smallest_child_at)

log = logging.getLogger(__name__)

MIN_SIZE = 80
TEST_NOTCHES = 2


def base_rect(top_hwnd: int, anchor: tuple[int, int]) -> Rect:
    """Rect of the deepest child window under the anchor, clipped to the client area."""
    client = client_rect(top_hwnd)
    child = smallest_child_at(top_hwnd, *anchor, min_size=MIN_SIZE)
    if child and child != top_hwnd:
        r = raw_window_rect(child).intersect(client)
        if r.width >= MIN_SIZE and r.height >= MIN_SIZE:
            return r
    return client


def _changed_bbox(a: np.ndarray, b: np.ndarray) -> tuple[int, int, int, int] | None:
    diff = np.any(np.abs(a.astype(np.int16) - b.astype(np.int16)) > 8, axis=2)
    if diff.sum() < 50:
        return None
    rows = np.flatnonzero(diff.any(axis=1))
    cols = np.flatnonzero(diff.any(axis=0))
    return int(cols[0]), int(rows[0]), int(cols[-1]) + 1, int(rows[-1]) + 1


def detect_scroll_region(top_hwnd: int, anchor: tuple[int, int],
                         delay_ms: int = 250, settle_ms: int = 1000) -> Rect:
    """Test-scroll at ``anchor`` and return the bounding box of what moved.

    Falls back to the window under the anchor when nothing moves.
    """
    base = base_rect(top_hwnd, anchor)
    orig = get_cursor_pos()
    grab = Grabber()
    try:
        set_cursor_pos(*anchor)
        before = wait_stable(grab, base, 50, settle_ms)
        bbox = None
        for direction in (-1, 1):            # try down first, then up (if at the bottom)
            set_cursor_pos(*anchor)
            send_wheel(direction * TEST_NOTCHES * WHEEL_DELTA)
            after = wait_stable(grab, base, delay_ms, settle_ms)
            set_cursor_pos(*anchor)
            send_wheel(-direction * TEST_NOTCHES * WHEEL_DELTA)   # undo
            wait_stable(grab, base, delay_ms, settle_ms)
            bbox = _changed_bbox(before, after)
            if bbox:
                break
    finally:
        grab.close()
        set_cursor_pos(*orig)

    if not bbox:
        log.info("region: nothing scrolled, using base %s", base)
        return base

    x0, y0, x1, y1 = bbox
    w, h = base.width, base.height
    # Content often doesn't span the full width (centered pages): widen to the base.
    if (x1 - x0) >= 0.5 * w:
        x0, x1 = 0, w
    # Include thin unchanged strips at the edges (headers / padding).
    if y0 < 0.08 * h:
        y0 = 0
    if h - y1 < 0.08 * h:
        y1 = h
    if y1 - y0 < MIN_SIZE or x1 - x0 < MIN_SIZE:
        return base
    r = Rect(base.left + x0, base.top + y0, base.left + x1, base.top + y1)
    log.info("region: base=%s detected=%s", base, r)
    return r
