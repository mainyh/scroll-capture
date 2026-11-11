"""Overlap detection and stitching of vertically scrolled frames.

Approach
--------
* Every frame row is reduced to a 64-bit hash (exact match) plus a small
  grayscale signature (tolerant fallback). The right-most columns are left out
  of both so a moving scrollbar thumb does not break matching.
* Rows that are identical at the top/bottom of consecutive frames are sticky
  headers/footers; they are excluded from offset search and kept only once.
* The vertical offset ``dy`` between two frames is the shift for which the
  most "informative" (non-blank) rows line up.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np

MATCH_THRESHOLD = 0.90      # min share of informative rows that must match exactly
FALLBACK_MAX_DIFF = 3.0     # max mean gray difference (0..255) for the tolerant matcher
MIN_OVERLAP = 16            # rows
MIN_INFORMATIVE = 6         # rows (or row-bands)
SIG_COLS = 96               # width of the grayscale row signature
INFORMATIVE_RANGE = 12      # gray max-min within a row to count as "has content"


def right_margin(width: int) -> int:
    """Columns at the right edge ignored for matching (scrollbars)."""
    return int(min(48, max(16, width * 0.04)))


@lru_cache(maxsize=8)
def _weights(n: int) -> np.ndarray:
    rng = np.random.default_rng(0x5C011)
    return rng.integers(1, 2**63 - 1, size=n, dtype=np.uint64) | np.uint64(1)


@dataclass
class FrameSig:
    hashes: np.ndarray       # (h, BANDS) uint64 - one hash per row per column band
    band_inf: np.ndarray     # (h, BANDS) bool  - band has content
    informative: np.ndarray  # (h,) bool        - row has content
    gray: np.ndarray         # (h, k) float32   - coarse grayscale signature


BANDS = 8


def _hash_rows(block: np.ndarray) -> np.ndarray:
    h = block.shape[0]
    flat = np.ascontiguousarray(block).reshape(h, -1)
    pad = (-flat.shape[1]) % 8
    if pad:
        flat = np.pad(flat, ((0, 0), (0, pad)))
    words = flat.view(np.uint64)
    with np.errstate(over="ignore"):
        hashes = (words * _weights(words.shape[1])).sum(axis=1, dtype=np.uint64)
        hashes ^= hashes >> np.uint64(29)
    return hashes


def signature(frame: np.ndarray) -> FrameSig:
    h, w, _ = frame.shape
    m = right_margin(w)
    body = frame[:, : w - m] if w - m >= 32 else frame
    bw = body.shape[1]
    edges = np.linspace(0, bw, BANDS + 1).astype(int)
    gray = body.astype(np.float32) @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    hashes = np.empty((h, BANDS), np.uint64)
    band_inf = np.empty((h, BANDS), bool)
    for i in range(BANDS):
        x0, x1 = edges[i], max(edges[i + 1], edges[i] + 1)
        hashes[:, i] = _hash_rows(body[:, x0:x1])
        g = gray[:, x0:x1]
        band_inf[:, i] = (g.max(axis=1) - g.min(axis=1)) > INFORMATIVE_RANGE
    informative = (gray.max(axis=1) - gray.min(axis=1)) > INFORMATIVE_RANGE
    k = min(SIG_COLS, bw)
    s = bw // k
    small = gray[:, : k * s].reshape(h, k, s).mean(axis=2)
    return FrameSig(hashes=hashes, band_inf=band_inf, informative=informative, gray=small)


def nearly_identical(a: np.ndarray, b: np.ndarray, tol: float = 0.0005) -> bool:
    """True when at most ``tol`` of the pixels differ (ignores caret blinking etc.)."""
    if a.shape != b.shape:
        return False
    diff = np.any(a != b, axis=2)
    return float(diff.mean()) <= tol


def top_same(a: FrameSig, b: FrameSig) -> int:
    eq = (a.hashes == b.hashes).all(axis=1)
    return len(eq) if eq.all() else int(np.argmin(eq))


def bottom_same(a: FrameSig, b: FrameSig) -> int:
    eq = (a.hashes == b.hashes).all(axis=1)[::-1]
    return len(eq) if eq.all() else int(np.argmin(eq))


def sticky_bounds(a: FrameSig, b: FrameSig, height: int) -> tuple[int, int]:
    """(header, footer) heights for one frame pair, capped to a third of the frame."""
    cap = height // 3
    return min(top_same(a, b), cap), min(bottom_same(a, b), cap)


def find_offset(prev: FrameSig, cur: FrameSig, top: int, bottom: int,
                expected: int | None = None) -> int | None:
    """Vertical scroll distance (px) from ``prev`` to ``cur`` within rows [top, bottom).

    ``cur[y] == prev[y + dy]``. Returns None when no convincing overlap exists.
    """
    n = bottom - top
    if n < MIN_OVERLAP * 2:
        return None
    ha, hb = prev.hashes[top:bottom], cur.hashes[top:bottom]
    ia, ib = prev.band_inf[top:bottom], cur.band_inf[top:bottom]

    cands: list[tuple[int, float, int]] = []
    for dy in range(1, n - MIN_OVERLAP + 1):
        ov = n - dy
        mask = ib[:ov] | ia[dy:]
        cnt = int(mask.sum())
        if cnt < MIN_INFORMATIVE:
            continue
        match = int(((hb[:ov] == ha[dy:]) & mask).sum())
        score = match / cnt
        if score >= MATCH_THRESHOLD:
            cands.append((dy, score, cnt))

    if cands:
        best = max(c[1] for c in cands)
        top_c = [c for c in cands if c[1] >= best - 0.02]
        if expected:
            return min(top_c, key=lambda c: (abs(c[0] - expected), -c[1]))[0]
        return max(top_c, key=lambda c: (c[1], c[2]))[0]

    return _find_offset_tolerant(prev, cur, top, bottom, expected)


def _find_offset_tolerant(prev: FrameSig, cur: FrameSig, top: int, bottom: int,
                          expected: int | None) -> int | None:
    n = bottom - top
    ga, gb = prev.gray[top:bottom], cur.gray[top:bottom]
    ia, ib = prev.informative[top:bottom], cur.informative[top:bottom]
    best_dy, best_d = None, float("inf")
    for dy in range(1, n - MIN_OVERLAP + 1):
        ov = n - dy
        mask = ib[:ov] | ia[dy:]
        if int(mask.sum()) < MIN_INFORMATIVE:
            continue
        # trimmed mean over rows: ignores the worst 10% (floating elements)
        rd = np.abs(gb[:ov][mask] - ga[dy:][mask]).mean(axis=1)
        keep = max(1, int(len(rd) * 0.9))
        d = float(np.partition(rd, keep - 1)[:keep].mean())
        if expected:
            d += abs(dy - expected) * 1e-4  # tie-break towards the expected step
        if d < best_d:
            best_dy, best_d = dy, d
    if best_dy is not None and best_d <= FALLBACK_MAX_DIFF:
        return best_dy
    return None


def scrollbar_trim(prev: np.ndarray, cur: np.ndarray, dy: int, top: int, bottom: int) -> int:
    """Width of non-scrolling columns at the right edge (scrollbar) for this pair."""
    w = prev.shape[1]
    zone = right_margin(w)
    a = prev[top + dy:bottom, w - zone:]
    b = cur[top:bottom - dy, w - zone:]
    if a.shape[0] < MIN_OVERLAP:
        return 0
    mism = np.any(a != b, axis=2).mean(axis=0)
    cols = np.flatnonzero(mism > 0.01)
    return int(zone - cols[0]) if len(cols) else 0


def floating_bottom_band(prev: np.ndarray, cur: np.ndarray, dy: int, top: int, bottom: int,
                         zone: float = 0.55) -> int:
    """Height of the band at the bottom of the frame that holds non-scrolling,
    partial-width elements (floating chat buttons, cookie bars, ...).

    Rows are compared after aligning by ``dy``; a row that still differs holds
    something that did not move with the content.
    """
    h, w, _ = prev.shape
    m = right_margin(w)
    a = prev[top + dy:bottom, : w - m].astype(np.int16)
    b = cur[top:bottom - dy, : w - m].astype(np.int16)
    if a.shape[0] < MIN_OVERLAP:
        return 0
    moved = (np.abs(a - b).max(axis=2) > 16).sum(axis=1) > 3
    rows_prev = top + dy + np.flatnonzero(moved)          # screen rows in ``prev``
    rows_prev = rows_prev[rows_prev >= int(h * zone)]
    return int(h - rows_prev.min()) if len(rows_prev) else 0


@dataclass
class StitchResult:
    image: np.ndarray
    frames_used: int
    gaps: int = 0
    header: int = 0
    footer: int = 0
    trim: int = 0
    offsets: list[int] = field(default_factory=list)


def stitch(frames: list[np.ndarray], remove_sticky: bool = True) -> StitchResult:
    if not frames:
        raise ValueError("no frames")
    uniq = [frames[0]]
    for f in frames[1:]:
        if not nearly_identical(f, uniq[-1]):
            uniq.append(f)
    if len(uniq) == 1:
        return StitchResult(image=uniq[0].copy(), frames_used=1)

    h, w, _ = uniq[0].shape
    sigs = [signature(f) for f in uniq]
    n_pairs = len(uniq) - 1
    if remove_sticky:
        # Per-pair bounds for matching (robust to one noisy pair); the median is
        # used for composing so a sticky footer is appended only once.
        bounds = [sticky_bounds(sigs[i - 1], sigs[i], h) for i in range(1, len(sigs))]
        bounds = [b if h - b[0] - b[1] >= MIN_OVERLAP * 2 else (0, 0) for b in bounds]
        header = int(np.median([b[0] for b in bounds]))
        footer = int(np.median([b[1] for b in bounds]))
    else:
        bounds = [(0, 0)] * n_pairs
        header = footer = 0
    body_bottom = h - footer

    # Pass 1: offsets, scrollbar width and floating (position: fixed) elements.
    expected: int | None = None
    trim = gaps = 0
    float_band = 0
    offsets: list[int] = []
    for i in range(1, len(uniq)):
        ph, pf = bounds[i - 1]
        top, bottom = ph, h - pf
        dy = find_offset(sigs[i - 1], sigs[i], top, bottom, expected)
        if dy is not None and dy > body_bottom - header:
            dy = None
        if dy is None and expected and expected < body_bottom - header:
            dy = expected  # ambiguous (e.g. blank) overlap: assume the usual scroll step
        elif dy is None:
            gaps += 1
            dy = body_bottom - header
        else:
            expected = dy
            trim = max(trim, scrollbar_trim(uniq[i - 1], uniq[i], dy, top, bottom))
            if remove_sticky:
                float_band = max(float_band, floating_bottom_band(uniq[i - 1], uniq[i], dy, top, bottom))
        offsets.append(dy)

    # Floating buttons near the bottom are treated like a footer: new rows are then
    # taken from above them, where the hidden content shows up in the next frame.
    if float_band > footer:
        footer = max(footer, min(float_band, h - header - max(offsets)))
        body_bottom = h - footer

    # Pass 2: compose.
    parts = [uniq[0][:body_bottom]]
    for i, dy in enumerate(offsets, start=1):
        dy = min(dy, body_bottom)
        parts.append(uniq[i][body_bottom - dy:body_bottom])
    parts.append(uniq[-1][body_bottom:])
    img = np.vstack(parts)
    if 0 < trim < w // 4:
        img = img[:, : w - trim]
    else:
        trim = 0
    return StitchResult(image=np.ascontiguousarray(img), frames_used=len(uniq), gaps=gaps,
                        header=header, footer=footer, trim=trim, offsets=offsets)
