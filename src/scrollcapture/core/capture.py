"""Scroll-and-grab loop: drives the target window with mouse-wheel input and
collects overlapping frames, then stitches them."""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from . import stitcher
from .grabber import Grabber
from .win32utils import Rect, WHEEL_DELTA, get_cursor_pos, send_wheel, set_cursor_pos

log = logging.getLogger(__name__)

MAX_FRAMES = 600
MAX_NOTCHES = 40


@dataclass
class CaptureOptions:
    start_from_top: bool = True
    frame_delay_ms: int = 250
    settle_timeout_ms: int = 1000
    max_height: int = 30000
    notches: int = 0            # 0 = automatic
    remove_sticky: bool = True


@dataclass
class CaptureControl:
    """Shared flags the UI thread flips to stop or cancel a running capture."""
    stop: bool = False
    cancel: bool = False


@dataclass
class CaptureOutcome:
    image: np.ndarray | None
    reason: str                 # end | stopped | max_height | cancelled | max_frames
    frames: int = 0
    gaps: int = 0
    info: dict = field(default_factory=dict)


ProgressFn = Callable[[int, int], None]   # (frames, height_px)


def wait_stable(grab: Grabber, rect: Rect, delay_ms: int, settle_ms: int) -> np.ndarray:
    """Wait ``delay_ms`` then grab until two consecutive frames match (smooth scrolling)."""
    time.sleep(delay_ms / 1000)
    a = grab.grab(rect)
    deadline = time.monotonic() + settle_ms / 1000
    while time.monotonic() < deadline:
        time.sleep(0.06)
        b = grab.grab(rect)
        if stitcher.nearly_identical(a, b, tol=0.0002):
            return b
        a = b
    return a


class CaptureEngine:
    def __init__(self, region: Rect, anchor: tuple[int, int], options: CaptureOptions,
                 control: CaptureControl | None = None, on_progress: ProgressFn | None = None):
        self.region = region
        self.anchor = anchor
        self.opt = options
        self.control = control or CaptureControl()
        self.on_progress = on_progress or (lambda f, h: None)

    # ------------------------------------------------------------------ helpers
    def _wheel(self, notches: int) -> None:
        """notches > 0 scrolls down."""
        set_cursor_pos(*self.anchor)
        send_wheel(-notches * WHEEL_DELTA)

    def _stable(self, grab: Grabber) -> np.ndarray:
        return wait_stable(grab, self.region, self.opt.frame_delay_ms, self.opt.settle_timeout_ms)

    def _scroll_to_top(self, grab: Grabber) -> None:
        prev = grab.grab(self.region)
        unchanged = 0
        for _ in range(120):
            if self.control.cancel or self.control.stop:
                return
            # Several normal-sized wheel events: some apps ignore or throttle huge deltas.
            for _ in range(8):
                self._wheel(-3)
                time.sleep(0.01)
            cur = self._stable(grab)
            if stitcher.nearly_identical(prev, cur):
                unchanged += 1
                if unchanged >= 2:
                    return
            else:
                unchanged = 0
            prev = cur

    # ------------------------------------------------------------------ main
    def run(self) -> CaptureOutcome:
        ctl, opt = self.control, self.opt
        orig_cursor = get_cursor_pos()
        grab = Grabber()
        try:
            set_cursor_pos(*self.anchor)
            if opt.start_from_top:
                self._scroll_to_top(grab)
            if ctl.cancel:
                return CaptureOutcome(None, "cancelled")

            frames = [self._stable(grab)]
            h = frames[0].shape[0]
            sig_prev = stitcher.signature(frames[0])
            auto = opt.notches <= 0
            notches = 1 if auto else opt.notches
            px_per_notch: float | None = None
            last_dy: int | None = None
            total = h
            same = 0
            reason = "end"
            self.on_progress(1, total)

            while True:
                if ctl.cancel:
                    return CaptureOutcome(None, "cancelled", len(frames))
                if ctl.stop:
                    reason = "stopped"
                    break
                if total >= opt.max_height:
                    reason = "max_height"
                    break
                if len(frames) >= MAX_FRAMES:
                    reason = "max_frames"
                    break

                self._wheel(notches)
                cur = self._stable(grab)
                if stitcher.nearly_identical(cur, frames[-1]):
                    same += 1
                    if same >= 2:      # nothing moved twice in a row -> bottom reached
                        break
                    continue
                same = 0

                sig = stitcher.signature(cur)
                header, footer = (stitcher.sticky_bounds(sig_prev, sig, h)
                                  if opt.remove_sticky else (0, 0))
                body = h - header - footer
                dy = stitcher.find_offset(sig_prev, sig, header, h - footer, last_dy)
                if dy is None and notches > 1:
                    # Scrolled past the overlap: go back and use a smaller step.
                    log.debug("no overlap at %d notches, backing off", notches)
                    self._wheel(-notches)
                    self._stable(grab)
                    notches = max(1, notches // 2)
                    if px_per_notch:
                        px_per_notch = body / (notches + 1)
                    continue
                if dy is None:
                    dy = last_dy if last_dy and last_dy < body else body

                frames.append(cur)
                sig_prev = sig
                total += dy
                last_dy = dy
                if auto:
                    step = dy / notches
                    if px_per_notch is None or step > px_per_notch:
                        px_per_notch = step
                    notches = int(max(1, min(MAX_NOTCHES, (0.55 * body) // px_per_notch)))
                self.on_progress(len(frames), total)

            res = stitcher.stitch(frames, remove_sticky=opt.remove_sticky)
            img = res.image
            if img.shape[0] > opt.max_height:
                img = np.ascontiguousarray(img[: opt.max_height])
            log.info("capture %s: frames=%d -> %dx%d gaps=%d header=%d footer=%d trim=%d",
                     reason, res.frames_used, img.shape[1], img.shape[0], res.gaps,
                     res.header, res.footer, res.trim)
            return CaptureOutcome(img, reason, res.frames_used, res.gaps,
                                  {"header": res.header, "footer": res.footer, "trim": res.trim})
        finally:
            grab.close()
            set_cursor_pos(*orig_cursor)
