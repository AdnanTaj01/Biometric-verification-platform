"""
Mock Fingerprint Scanner SDK.

This module simulates the interface of real fingerprint scanner SDKs
(DigitalPersona, Futronic, Mantra, etc.). The public API mirrors the
typical vendor SDK shape.

Real vendor SDKs would swap this module for their own (e.g., ctypes bindings
to a .dll). Application code should not change — only the import.
"""
import time
import hashlib
import numpy as np
from dataclasses import dataclass
from typing import Optional


# ---------- Constants matching typical vendor SDK error codes ----------
class SDKError:
    OK = 0
    DEVICE_NOT_FOUND = -1
    DEVICE_BUSY = -2
    CAPTURE_TIMEOUT = -3
    POOR_QUALITY = -4
    NO_FINGER = -5


# ---------- Result object ----------
@dataclass
class CaptureResult:
    """Result of a fingerprint capture — mirrors vendor SDK return objects."""
    success: bool
    error_code: int
    error_message: str
    quality_score: int
    template: Optional[np.ndarray]
    image: Optional[np.ndarray]
    capture_time_ms: int


# ---------- Mock Scanner ----------
class FingerprintScanner:
    """
    Mock fingerprint scanner. Simulates:
    - Device connection / disconnection
    - Capture with timeout
    - Quality scoring
    - Template generation

    For real hardware, replace this class with vendor SDK calls.
    """

    def __init__(self, device_name: str = "MockScan FX-2000"):
        self.device_name = device_name
        self.connected = False
        self._finger_present = False

    # ---------- Device lifecycle ----------
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

    # ---------- Simulation helpers (mock only) ----------
    def simulate_finger_placed(self):
        self._finger_present = True

    def simulate_finger_lifted(self):
        self._finger_present = False

    # ---------- Capture ----------
    def capture(self, timeout: int = 5,
                seed: Optional[int] = None,
                force_quality: Optional[int] = None) -> CaptureResult:
        """
        Simulate a fingerprint capture.

        Args:
            timeout: capture timeout (seconds)
            seed: RNG seed — same seed = same template (deterministic)
            force_quality: if set (0-100), bypasses random quality.
                           Useful for testing.

        Returns:
            CaptureResult object.
        """
        start = time.time()

        if not self.connected:
            return CaptureResult(
                success=False,
                error_code=SDKError.DEVICE_NOT_FOUND,
                error_message="Scanner not connected",
                quality_score=0,
                template=None,
                image=None,
                capture_time_ms=0,
            )

        if not self._finger_present:
            return CaptureResult(
                success=False,
                error_code=SDKError.NO_FINGER,
                error_message="No finger detected on sensor",
                quality_score=0,
                template=None,
                image=None,
                capture_time_ms=int((time.time() - start) * 1000),
            )

        # Simulate capture time
        time.sleep(0.5)

        rng = np.random.default_rng(seed)

        # Quality: use forced value if provided, else random 40-95
        if force_quality is not None:
            quality = int(force_quality)
        else:
            quality = int(rng.integers(40, 96))

        # Mock 512-byte template
        template = rng.integers(0, 256, size=512, dtype=np.uint8)

        # Mock fingerprint image (256x256 uint8)
        img_h, img_w = 256, 256
        y, x = np.mgrid[0:img_h, 0:img_w]
        r = np.sqrt((x - img_w / 2) ** 2 + (y - img_h / 2) ** 2)
        pattern = (np.sin(r * 0.5) * 127 + 128).astype(np.uint8)
        noise = rng.integers(-20, 20, size=(img_h, img_w))
        image = np.clip(pattern.astype(int) + noise, 0, 255).astype(np.uint8)

        # Poor quality simulation
        if quality < 55:
            return CaptureResult(
                success=False,
                error_code=SDKError.POOR_QUALITY,
                error_message=f"Poor quality ({quality}/100). Please retry.",
                quality_score=quality,
                template=None,
                image=image,
                capture_time_ms=int((time.time() - start) * 1000),
            )

        return CaptureResult(
            success=True,
            error_code=SDKError.OK,
            error_message="Capture successful",
            quality_score=quality,
            template=template,
            image=image,
            capture_time_ms=int((time.time() - start) * 1000),
        )


# ---------- Template matching (mock) ----------
def compare_templates(t1: np.ndarray, t2: np.ndarray) -> float:
    """
    Compare two fingerprint templates. Returns similarity 0.0 - 1.0.
    In real SDKs this is a proprietary matcher function.
    """
    if t1 is None or t2 is None:
        return 0.0
    matches = np.sum(t1 == t2)
    total = len(t1)
    return float(matches / total)


# ---------- Self-test ----------
if __name__ == "__main__":
    print("=" * 60)
    print("Mock Fingerprint SDK — self test")
    print("=" * 60)

    scanner = FingerprintScanner()
    print(f"\n[1] Status before connect: {scanner.get_device_status()}")

    scanner.connect()
    print(f"[2] Status after connect: {scanner.get_device_status()}")

    r = scanner.capture()
    print(f"\n[3] Capture without finger:")
    print(f"    success={r.success}, error={r.error_message}")

    scanner.simulate_finger_placed()
    r = scanner.capture(seed=42, force_quality=85)
    print(f"\n[4] Capture with finger (forced quality):")
    print(f"    success={r.success}, quality={r.quality_score}")
    print(f"    template shape: {r.template.shape if r.template is not None else None}")
    print(f"    capture_time: {r.capture_time_ms} ms")

    r2 = scanner.capture(seed=42, force_quality=85)
    sim = compare_templates(r.template, r2.template)
    print(f"\n[5] Same seed twice → similarity: {sim:.2%}")

    r3 = scanner.capture(seed=99, force_quality=85)
    sim2 = compare_templates(r.template, r3.template)
    print(f"[6] Different seed → similarity: {sim2:.2%}")

    print("\n✅ Mock SDK works.")