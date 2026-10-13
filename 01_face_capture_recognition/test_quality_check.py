"""Tests for quality_check.py — pure numpy + OpenCV logic."""
import numpy as np

from quality_check import (
    check_brightness, check_blur, check_face_size,
    run_all_quality_checks, all_passed,
)


def test_brightness_too_dark():
    dark = np.full((480, 640, 3), 20, dtype=np.uint8)
    ok, msg = check_brightness(dark)
    assert not ok
    assert "dark" in msg.lower()


def test_brightness_too_bright():
    bright = np.full((480, 640, 3), 240, dtype=np.uint8)
    ok, msg = check_brightness(bright)
    assert not ok
    assert "bright" in msg.lower()


def test_brightness_ok():
    ok_img = np.full((480, 640, 3), 128, dtype=np.uint8)
    ok, _ = check_brightness(ok_img)
    assert ok


def test_blur_detection_flat_image():
    """A flat image has near-zero variance → too blurry."""
    flat = np.full((480, 640, 3), 128, dtype=np.uint8)
    ok, msg = check_blur(flat)
    assert not ok
    assert "blurry" in msg.lower()


def test_blur_detection_sharp_noise():
    """Random noise has high Laplacian variance → sharp enough."""
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    ok, _ = check_blur(noise)
    assert ok


def test_face_size_too_small():
    ok, _ = check_face_size((100, 100, 150, 150), (480, 640, 3))
    assert not ok


def test_face_size_ok():
    ok, _ = check_face_size((100, 100, 400, 400), (480, 640, 3))
    assert ok


def test_run_all_without_face():
    img = np.full((480, 640, 3), 128, dtype=np.uint8)
    results = run_all_quality_checks(img, face_box=None)
    names = [r["name"] for r in results]
    assert "Face Detected" in names
    assert not all_passed(results)


def test_run_all_with_face():
    rng = np.random.default_rng(42)
    img = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    results = run_all_quality_checks(img, face_box=(150, 100, 450, 400))
    assert any(r["name"] == "Face Size" for r in results)