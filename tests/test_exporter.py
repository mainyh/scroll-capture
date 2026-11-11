from datetime import datetime

import numpy as np
import pytest
from PIL import Image

from scrollcapture.core import exporter


def test_build_filename_sanitizes_title():
    when = datetime(2026, 11, 11, 9, 5, 7)
    name = exporter.build_filename("ScrollCapture_{title}_{datetime}", 'Inbox: a/b <c>?', "png", when)
    assert name == "ScrollCapture_Inbox_ a_b _c_20261111_090507.png"


def test_build_filename_bad_pattern_falls_back():
    name = exporter.build_filename("{nope}", "t", "jpg", datetime(2026, 1, 2, 3, 4, 5))
    assert name == "ScrollCapture_t_20260102_030405.jpg"


def test_unique_path(tmp_path):
    (tmp_path / "a.png").write_bytes(b"x")
    assert exporter.unique_path(tmp_path, "a.png").name == "a_1.png"


def test_format_from_path():
    assert exporter.format_from_path("x.JPEG") == "jpg"
    assert exporter.format_from_path("x.png") == "png"
    assert exporter.format_from_path("x.bmp", "jpg") == "jpg"


def test_save_png_with_metadata(tmp_path):
    img = np.random.default_rng(0).integers(0, 255, (50, 40, 3), dtype=np.uint8)
    p = exporter.save_image(img, tmp_path / "x.png", "png", metadata={"Title": "제목"})[0]
    with Image.open(p) as im:
        assert im.size == (40, 50)
        assert im.text["Title"] == "제목"
        assert np.array_equal(np.asarray(im), img)


def test_save_jpg(tmp_path):
    img = np.full((30, 20, 3), 128, np.uint8)
    p = exporter.save_image(img, tmp_path / "x.jpg", "jpg", jpg_quality=90)[0]
    with Image.open(p) as im:
        assert im.format == "JPEG" and im.size == (20, 30)


def test_jpeg_too_tall_raises_or_splits(tmp_path):
    img = np.zeros((exporter.JPEG_MAX + 10, 2, 3), np.uint8)
    with pytest.raises(exporter.JpegTooLarge):
        exporter.save_image(img, tmp_path / "t.jpg", "jpg")
    parts = exporter.save_image(img, tmp_path / "t.jpg", "jpg", split_jpeg=True)
    assert len(parts) == 2
    heights = [Image.open(p).size[1] for p in parts]
    assert sum(heights) == img.shape[0]
