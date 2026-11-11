import numpy as np
import pytest

from scrollcapture.core import stitcher


def make_page(height=5000, width=600, seed=1):
    """A fake document: white background with noisy 'text lines' and blank gaps."""
    rng = np.random.default_rng(seed)
    page = np.full((height, width, 3), 255, np.uint8)
    y = 0
    while y < height:
        kind = rng.random()
        if kind < 0.7:  # text line
            lh = min(int(rng.integers(12, 24)), height - y)
            line = rng.integers(0, 255, size=(lh, width - 80, 3), dtype=np.uint8)
            page[y:y + lh, 40:width - 40] = line
            y += lh + int(rng.integers(4, 12))
        elif kind < 0.9:  # image block
            bh = min(int(rng.integers(40, 160)), height - y)
            page[y:y + bh, 60:width - 200] = rng.integers(0, 255, 3, dtype=np.uint8)
            page[y:y + bh, 60:70] = 0
            y += bh + 10
        else:  # blank gap
            y += int(rng.integers(30, 200))
    return page


def viewport_frames(page, view_h, step, header=0, footer=0, scrollbar=0):
    total = page.shape[0]
    offsets = list(range(0, total - view_h, step)) + [total - view_h]
    frames = []
    for o in offsets:
        f = page[o:o + view_h].copy()
        if header:
            f[:header] = (30, 60, 200)
            f[header // 2, ::7] = 255
        if footer:
            f[view_h - footer:] = (220, 220, 220)
            f[view_h - footer // 2, ::5] = 0
        if scrollbar:
            w = f.shape[1]
            f[:, w - scrollbar:] = (240, 240, 240)
            thumb = int(o / total * view_h)
            f[thumb:thumb + 60, w - scrollbar + 2:w - 2] = (120, 120, 120)
        frames.append(f)
    return frames, offsets


@pytest.mark.parametrize("step", [150, 400, 520])
def test_plain_stitch_is_pixel_exact(step):
    page = make_page()
    frames, _ = viewport_frames(page, 700, step)
    res = stitcher.stitch(frames)
    assert res.gaps == 0
    assert res.image.shape == page.shape
    assert np.array_equal(res.image, page)


def test_sticky_header_footer_kept_once():
    page = make_page(seed=2)
    H, F, vh = 60, 40, 700
    frames, offsets = viewport_frames(page, vh, 420, header=H, footer=F)
    res = stitcher.stitch(frames)
    assert res.header == H and res.footer == F
    last = offsets[-1]
    expected = np.vstack([frames[0][:H], page[H:last + vh - F], frames[-1][vh - F:]])
    assert res.image.shape == expected.shape
    assert np.array_equal(res.image, expected)


def test_scrollbar_is_trimmed():
    page = make_page(seed=3)
    sb = 14
    frames, _ = viewport_frames(page, 700, 380, scrollbar=sb)
    res = stitcher.stitch(frames)
    assert res.gaps == 0
    # the 2px track border next to the thumb never changes, so it may remain
    assert sb - 2 <= res.trim <= sb
    w = page.shape[1]
    assert res.image.shape[0] == page.shape[0]
    assert np.array_equal(res.image[:, : w - sb], page[:, : w - sb])


def test_duplicate_frames_are_dropped():
    page = make_page(seed=4)
    frames, _ = viewport_frames(page, 700, 500)
    frames = frames + [frames[-1].copy(), frames[-1].copy()]
    res = stitcher.stitch(frames)
    assert np.array_equal(res.image, page)


def test_tolerant_fallback_handles_noise():
    page = make_page(seed=5)
    frames, _ = viewport_frames(page, 700, 400)
    rng = np.random.default_rng(9)
    noisy = []
    for f in frames:
        n = f.astype(np.int16) + rng.integers(-1, 2, size=f.shape, dtype=np.int16)
        noisy.append(np.clip(n, 0, 255).astype(np.uint8))
    res = stitcher.stitch(noisy)
    assert res.gaps == 0
    assert res.image.shape[0] == page.shape[0]


def test_single_frame():
    page = make_page(height=500, seed=6)
    res = stitcher.stitch([page])
    assert np.array_equal(res.image, page)


def test_nearly_identical_ignores_caret():
    page = make_page(height=700, seed=7)
    b = page.copy()
    b[100:120, 50:52] = 0
    assert stitcher.nearly_identical(page, b)
    assert not stitcher.nearly_identical(page, make_page(height=700, seed=8))


def test_floating_button_appears_once():
    page = make_page(seed=11)
    vh, w = 700, page.shape[1]
    frames, offsets = viewport_frames(page, vh, 350)
    for f in frames:  # a fixed "chat" button near the bottom-right
        f[vh - 90:vh - 40, w - 160:w - 60] = (230, 60, 60)
    res = stitcher.stitch(frames)
    assert res.image.shape[0] == page.shape[0]
    btn = np.all(res.image[:, w - 160:w - 60] == (230, 60, 60), axis=2).all(axis=1)
    # the button must only be present in the last screen's position
    assert btn[: page.shape[0] - vh].sum() == 0
    body = res.image[: page.shape[0] - 90]
    assert np.array_equal(body, page[: page.shape[0] - 90])
