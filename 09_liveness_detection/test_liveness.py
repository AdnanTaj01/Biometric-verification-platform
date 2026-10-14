"""Tests for liveness_engine.py — pure logic, no camera needed."""
import numpy as np

from liveness_engine import (
    compute_ear, detect_blink, detect_head_movement,
    analyze_texture, evaluate_liveness, MEDIAPIPE_AVAILABLE,
)


def _fake_eye_landmarks(ear_open: bool):
    """Construct 468 fake landmarks with eye region matching target EAR."""
    lm = np.zeros((468, 2), dtype=np.float32)
    # LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]  (p1..p6)
    # Open eye: vertical gaps large; Closed: vertical gaps tiny
    v_gap = 8.0 if ear_open else 1.0
    h_gap = 20.0
    pts = np.array([
        [100, 200],           # p1 — outer corner
        [110, 200 - v_gap],   # p2 — top mid
        [130, 200 - v_gap],   # p3 — top mid2
        [140, 200],           # p4 — inner corner
        [130, 200 + v_gap],   # p5 — bottom mid2
        [110, 200 + v_gap],   # p6 — bottom mid
    ], dtype=np.float32)
    lm[362] = pts[0]
    lm[385] = pts[1]
    lm[387] = pts[2]
    lm[263] = pts[3]
    lm[373] = pts[4]
    lm[380] = pts[5]
    # Copy same to right eye so it isn't zero (compute uses both)
    for idx, p in zip([33, 160, 158, 133, 153, 144], pts):
        lm[idx] = p
    # Nose tip at center
    lm[1] = [200, 220]
    return lm


def test_compute_ear_open_is_higher_than_closed():
    ear_open = compute_ear(_fake_eye_landmarks(True), [362, 385, 387, 263, 373, 380])
    ear_closed = compute_ear(_fake_eye_landmarks(False), [362, 385, 387, 263, 373, 380])
    assert ear_open > ear_closed
    assert ear_open > 0.20
    assert ear_closed < 0.15


def test_detect_blink_true():
    lm_open = _fake_eye_landmarks(True)
    lm_closed = _fake_eye_landmarks(False)
    blink, info = detect_blink(lm_open, lm_closed)
    assert blink is True
    assert info["drop"] > 0.05


def test_detect_blink_false_when_both_open():
    lm = _fake_eye_landmarks(True)
    blink, _ = detect_blink(lm, lm)
    assert blink is False


def test_detect_blink_missing_landmarks():
    blink, info = detect_blink(None, _fake_eye_landmarks(False))
    assert blink is False
    assert "reason" in info


def test_detect_head_movement_shift():
    lm_front = _fake_eye_landmarks(True)
    lm_turned = lm_front.copy()
    lm_turned[1] = [250, 220]  # shift nose by 50px
    moved, info = detect_head_movement(lm_front, lm_turned)
    assert moved is True
    assert info["dist_px"] >= 15


def test_detect_head_movement_static():
    lm = _fake_eye_landmarks(True)
    moved, _ = detect_head_movement(lm, lm)
    assert moved is False


def test_texture_flat_image_is_spoofish():
    flat = np.full((200, 200, 3), 128, dtype=np.uint8)
    real, info = analyze_texture(flat)
    assert real is False
    assert info["laplacian_variance"] < 50


def test_texture_noise_image_passes():
    rng = np.random.default_rng(0)
    noise = rng.integers(0, 256, (200, 200, 3), dtype=np.uint8)
    real, info = analyze_texture(noise)
    # Noise has very high variance — should pass the laplacian gate
    assert info["laplacian_variance"] > 50


def test_evaluate_liveness_blank_images():
    blank = np.full((480, 640, 3), 128, dtype=np.uint8)
    result = evaluate_liveness(blank, blank, blank)
    assert result.is_live is False
    assert result.confidence == 0.0


def test_evaluate_liveness_no_mediapipe_path():
    """If mediapipe is present, this just exercises the code path."""
    if not MEDIAPIPE_AVAILABLE:
        blank = np.full((480, 640, 3), 128, dtype=np.uint8)
        result = evaluate_liveness(blank, blank, blank)
        assert result.is_live is False