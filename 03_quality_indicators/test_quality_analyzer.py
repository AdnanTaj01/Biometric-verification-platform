"""Tests for quality_analyzer.py — 6-metric quality analysis."""
import numpy as np

from quality_analyzer import (
    analyze_brightness, analyze_contrast, analyze_sharpness,
    analyze_face_size, analyze_face_centering, analyze_face_orientation,
)


def test_brightness_dark_fails():
    img = np.full((480, 640, 3), 20, dtype=np.uint8)
    assert analyze_brightness(img).status == "fail"


def test_brightness_ideal_passes():
    img = np.full((480, 640, 3), 128, dtype=np.uint8)
    assert analyze_brightness(img).status == "pass"


def test_contrast_flat_image_fails():
    img = np.full((480, 640, 3), 128, dtype=np.uint8)
    assert analyze_contrast(img).status == "fail"


def test_contrast_high_passes():
    """Half black, half white → maximum contrast."""
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    img[:, 320:] = 255
    assert analyze_contrast(img).status == "pass"


def test_sharpness_blurry_fails():
    img = np.full((480, 640, 3), 128, dtype=np.uint8)
    assert analyze_sharpness(img).status == "fail"


def test_face_size_ideal():
    r = analyze_face_size((150, 100, 450, 400), (480, 640, 3))
    assert r.status == "pass"


def test_face_size_too_small():
    r = analyze_face_size((100, 100, 150, 150), (480, 640, 3))
    assert r.status == "fail"


def test_orientation_straight():
    kps = np.array([
        [100, 100], [200, 100], [150, 150], [120, 200], [180, 200],
    ], dtype=np.float32)
    r = analyze_face_orientation(kps)
    assert r.status == "pass"


def test_orientation_tilted():
    kps = np.array([
        [100, 100], [200, 200], [150, 250], [120, 300], [180, 300],
    ], dtype=np.float32)
    r = analyze_face_orientation(kps)
    assert r.status in ("warning", "fail")


def test_orientation_missing_landmarks():
    r = analyze_face_orientation(None)
    assert r.status == "fail"