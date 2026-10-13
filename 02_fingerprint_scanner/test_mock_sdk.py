"""Tests for the mock fingerprint SDK."""
from mock_sdk import FingerprintScanner, compare_templates, SDKError


def test_scanner_starts_disconnected():
    s = FingerprintScanner()
    status = s.get_device_status()
    assert not status["connected"]


def test_connect():
    s = FingerprintScanner()
    assert s.connect() is True
    assert s.get_device_status()["connected"]


def test_capture_fails_without_connection():
    s = FingerprintScanner()
    r = s.capture()
    assert not r.success
    assert r.error_code == SDKError.DEVICE_NOT_FOUND


def test_capture_fails_without_finger():
    s = FingerprintScanner()
    s.connect()
    r = s.capture()
    assert not r.success
    assert r.error_code == SDKError.NO_FINGER


def test_capture_success():
    s = FingerprintScanner()
    s.connect()
    s.simulate_finger_placed()
    r = s.capture(seed=42, force_quality=80)
    assert r.success
    assert r.template is not None
    assert r.template.shape == (512,)
    assert r.quality_score == 80


def test_capture_poor_quality_forced():
    s = FingerprintScanner()
    s.connect()
    s.simulate_finger_placed()
    r = s.capture(seed=42, force_quality=30)
    assert not r.success
    assert r.error_code == SDKError.POOR_QUALITY


def test_same_seed_produces_identical_templates():
    s = FingerprintScanner()
    s.connect()
    s.simulate_finger_placed()
    r1 = s.capture(seed=42, force_quality=80)
    r2 = s.capture(seed=42, force_quality=80)
    assert compare_templates(r1.template, r2.template) == 1.0


def test_different_seeds_produce_different_templates():
    s = FingerprintScanner()
    s.connect()
    s.simulate_finger_placed()
    r1 = s.capture(seed=42, force_quality=80)
    r2 = s.capture(seed=99, force_quality=80)
    assert compare_templates(r1.template, r2.template) < 0.5