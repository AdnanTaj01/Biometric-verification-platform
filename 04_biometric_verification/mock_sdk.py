"""
Mock fingerprint scanner SDK.
Covers FR-06, FR-07. (See Project 2 for full documentation.)
"""
import time
import numpy as np
from dataclasses import dataclass
from typing import Optional


class SDKError:
    OK = 0
    DEVICE_NOT_FOUND = -1
    DEVICE_BUSY = -2
    CAPTURE_TIMEOUT = -3
    POOR_QUALITY = -4
    NO_FINGER = -5


@dataclass
class CaptureResult:
    success: bool
    error_code: int
    error_message: str
    quality_score: int
    template: Optional[np.ndarray]
    image: Optional[np.ndarray]
    capture_time_ms: int


class FingerprintScanner:
    def __init__(self, device_name: str = "MockScan FX-2000"):
        self.device_name = device_name
        self.connected = False
        self._finger_present = False

    def connect(self) -> bool:
        time.sleep(0.3)
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False

    def get_device_status(self) -> dict:
        return {
            "connected": self.connected,
            "device_name": self.device_name if self.connected else None,
            "firmware": "v2.1.4" if self.connected else None,
            "sdk_version": "Mock SDK 1.0.0",
        }

    def simulate_finger_placed(self):
        self._finger_present = True

    def simulate_finger_lifted(self):
        self._finger_present = False

    def capture(self, timeout: int = 5, seed: Optional[int] = None) -> CaptureResult:
        start = time.time()
        if not self.connected:
            return CaptureResult(False, SDKError.DEVICE_NOT_FOUND,
                                 "Scanner not connected", 0, None, None, 0)

        if not self._finger_present:
            return CaptureResult(False, SDKError.NO_FINGER,
                                 "No finger detected", 0, None, None,
                                 int((time.time() - start) * 1000))

        time.sleep(0.5)
        rng = np.random.default_rng(seed)
        quality = int(rng.integers(40, 96))
        template = rng.integers(0, 256, size=512, dtype=np.uint8)

        img_h, img_w = 256, 256
        y, x = np.mgrid[0:img_h, 0:img_w]
        r = np.sqrt((x - img_w/2)**2 + (y - img_h/2)**2)
        pattern = (np.sin(r * 0.5) * 127 + 128).astype(np.uint8)
        noise = rng.integers(-20, 20, size=(img_h, img_w))
        image = np.clip(pattern.astype(int) + noise, 0, 255).astype(np.uint8)

        if quality < 55:
            return CaptureResult(False, SDKError.POOR_QUALITY,
                                 f"Poor quality ({quality}/100)", quality, None, image,
                                 int((time.time() - start) * 1000))

        return CaptureResult(True, SDKError.OK, "Capture successful",
                             quality, template, image,
                             int((time.time() - start) * 1000))


def compare_templates(t1: np.ndarray, t2: np.ndarray) -> float:
    if t1 is None or t2 is None:
        return 0.0
    return float(np.sum(t1 == t2) / len(t1))