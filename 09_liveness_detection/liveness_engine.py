"""
Liveness detection engine.

Covers SRS FR-05: detect printed-photo or replayed-video spoofing.

Approach: multi-photo challenge-response
    1. User captures photo with eyes OPEN      → validated at capture time
    2. User captures photo with eyes CLOSED    → validated at capture time
    3. User captures photo with head TURNED    → validated at capture time

Then the engine runs an overall analysis:
    - Blink detection via Eye Aspect Ratio (EAR) drop
    - Head movement via nose tip displacement
    - Texture analysis via Laplacian variance + FFT peak ratio

Thresholds are calibrated for typical laptop webcams (720p, moderate lighting).
"""
import numpy as np
import cv2
from dataclasses import dataclass
from typing import Optional

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


# MediaPipe Face Mesh indices (standard 468-landmark model)
LEFT_EYE_IDX = [362, 385, 387, 263, 373, 380]
RIGHT_EYE_IDX = [33, 160, 158, 133, 153, 144]
NOSE_TIP_IDX = 1

# ---- Thresholds tuned for laptop webcams ----
EAR_OPEN_THRESHOLD = 0.18       # below this → eyes considered closed
EAR_DROP_MIN = 0.025            # minimum drop for a clear blink
HEAD_SHIFT_MIN_PX = 12.0        # minimum nose-tip shift (overall analysis)
LAPLACIAN_MIN = 20.0            # minimum high-frequency energy
FFT_PEAK_MAX = 200.0            # maximum FFT peak ratio (screens/prints)

# ---- Per-step validation thresholds ----
STEP1_EAR_MIN = 0.20            # Step 1: eyes must be OPEN → EAR > 0.20
STEP2_EAR_MAX = 0.18            # Step 2: eyes must be CLOSED → EAR < 0.18
STEP3_OFFSET_RATIO_MIN = 0.15   # Step 3: nose offset > 15% of face width


@dataclass
class LivenessResult:
    is_live: bool
    confidence: float
    blink_detected: bool
    head_movement_detected: bool
    texture_looks_real: bool
    details: dict
    reason: str


_face_mesh = None


def _get_face_mesh():
    global _face_mesh
    if _face_mesh is None and MEDIAPIPE_AVAILABLE:
        _face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.4,
        )
    return _face_mesh


def _get_landmarks(image_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Return Nx2 array of pixel landmarks, or None if no face detected."""
    mesh = _get_face_mesh()
    if mesh is None:
        return None

    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    result = mesh.process(rgb)
    if not result.multi_face_landmarks:
        return None

    h, w = image_bgr.shape[:2]
    lm = result.multi_face_landmarks[0].landmark
    return np.array([[p.x * w, p.y * h] for p in lm], dtype=np.float32)


def compute_ear(landmarks: np.ndarray, eye_indices: list) -> float:
    """
    Eye Aspect Ratio for a single eye.
    Formula: (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    """
    pts = landmarks[eye_indices]
    v1 = float(np.linalg.norm(pts[1] - pts[5]))
    v2 = float(np.linalg.norm(pts[2] - pts[4]))
    h = float(np.linalg.norm(pts[0] - pts[3]))
    if h < 1e-6:
        return 0.0
    return (v1 + v2) / (2.0 * h)


# ================================================================
# PER-STEP VALIDATION (used at capture time in app.py)
# ================================================================

def validate_eyes_open(image_bgr):
    """
    Step 1 validation: eyes must be OPEN.
    Returns (is_valid, message, info).
    """
    lm = _get_landmarks(image_bgr)
    if lm is None:
        return False, "No face detected. Position your face in the frame.", {}

    ear = (compute_ear(lm, LEFT_EYE_IDX) + compute_ear(lm, RIGHT_EYE_IDX)) / 2
    info = {"ear": round(ear, 4), "threshold": STEP1_EAR_MIN}

    if ear < STEP1_EAR_MIN:
        return False, (
            f"Eyes appear CLOSED (EAR={ear:.3f}). "
            "Please OPEN your eyes and retake."
        ), info
    return True, f"Eyes open confirmed (EAR={ear:.3f})", info


def validate_eyes_closed(image_bgr):
    """
    Step 2 validation: eyes must be CLOSED.
    Returns (is_valid, message, info).
    """
    lm = _get_landmarks(image_bgr)
    if lm is None:
        return False, "No face detected. Position your face in the frame.", {}

    ear = (compute_ear(lm, LEFT_EYE_IDX) + compute_ear(lm, RIGHT_EYE_IDX)) / 2
    info = {"ear": round(ear, 4), "threshold": STEP2_EAR_MAX}

    if ear > STEP2_EAR_MAX:
        return False, (
            f"Eyes are still OPEN (EAR={ear:.3f}). "
            "Please CLOSE your eyes fully and retake."
        ), info
    return True, f"Eyes closed confirmed (EAR={ear:.3f})", info


def validate_head_turned(image_bgr):
    """
    Step 3 validation: head must be TURNED (~15° or more).
    Uses the horizontal offset between the nose tip and the midpoint
    of the two eye outer corners.
    Returns (is_valid, message, info).
    """
    lm = _get_landmarks(image_bgr)
    if lm is None:
        return False, "No face detected. Position your face in the frame.", {}

    left_eye_outer = lm[LEFT_EYE_IDX[0]]
    right_eye_outer = lm[RIGHT_EYE_IDX[3]]
    eye_center_x = (left_eye_outer[0] + right_eye_outer[0]) / 2

    nose_tip_x = lm[NOSE_TIP_IDX][0]
    offset = abs(nose_tip_x - eye_center_x)

    face_width = abs(right_eye_outer[0] - left_eye_outer[0])
    if face_width < 1:
        return False, "Could not measure face width. Retake.", {}

    normalized_offset = offset / face_width
    info = {
        "offset_px": round(offset, 2),
        "face_width_px": round(face_width, 2),
        "normalized_offset": round(normalized_offset, 4),
        "threshold": STEP3_OFFSET_RATIO_MIN,
    }

    if normalized_offset < STEP3_OFFSET_RATIO_MIN:
        return False, (
            f"Head appears STRAIGHT (offset={normalized_offset:.3f}). "
            "Please TURN your head ~15° and retake."
        ), info

    return True, f"Head turned confirmed (offset={normalized_offset:.3f})", info


# ================================================================
# OVERALL ANALYSIS (used in Result tab)
# ================================================================

def detect_blink(landmarks_open, landmarks_closed,
                 ear_open_thr: float = EAR_OPEN_THRESHOLD,
                 drop_min: float = EAR_DROP_MIN):
    """Blink detected if EAR drops notably between the two frames."""
    if landmarks_open is None or landmarks_closed is None:
        return False, {"reason": "no face landmarks in one or both photos"}

    ear_open = (compute_ear(landmarks_open, LEFT_EYE_IDX)
                + compute_ear(landmarks_open, RIGHT_EYE_IDX)) / 2
    ear_closed = (compute_ear(landmarks_closed, LEFT_EYE_IDX)
                  + compute_ear(landmarks_closed, RIGHT_EYE_IDX)) / 2

    drop = ear_open - ear_closed

    blink = (
        (ear_open > ear_open_thr and ear_closed < ear_open_thr)
        or (drop > drop_min)
    )

    return blink, {
        "ear_open": round(ear_open, 4),
        "ear_closed": round(ear_closed, 4),
        "drop": round(drop, 4),
        "threshold_open": ear_open_thr,
        "threshold_drop": drop_min,
    }


def detect_head_movement(landmarks_front, landmarks_turned,
                         min_shift_px: float = HEAD_SHIFT_MIN_PX):
    """Head movement detected if nose tip shifts beyond threshold."""
    if landmarks_front is None or landmarks_turned is None:
        return False, {"reason": "no face landmarks in one or both photos"}

    nose_front = landmarks_front[NOSE_TIP_IDX]
    nose_turned = landmarks_turned[NOSE_TIP_IDX]
    dx = float(nose_turned[0] - nose_front[0])
    dy = float(nose_turned[1] - nose_front[1])
    dist = float(np.hypot(dx, dy))

    return dist >= min_shift_px, {
        "dx_px": round(dx, 2),
        "dy_px": round(dy, 2),
        "dist_px": round(dist, 2),
        "threshold_px": min_shift_px,
    }


def analyze_texture(image_bgr: np.ndarray, face_bbox=None):
    """
    Analyze texture of face region for spoofing indicators.
    Real faces: high Laplacian variance, low FFT peak ratio.
    Prints/screens: low Laplacian variance, high FFT peak ratio.
    """
    if face_bbox is not None:
        x1, y1, x2, y2 = [int(v) for v in face_bbox]
        h, w = image_bgr.shape[:2]
        x1 = max(0, x1); y1 = max(0, y1)
        x2 = min(w, x2); y2 = min(h, y2)
        region = image_bgr[y1:y2, x1:x2]
    else:
        region = image_bgr

    if region.size == 0 or region.shape[0] < 20 or region.shape[1] < 20:
        return False, {"reason": "empty or too-small region"}

    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)

    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    f = np.fft.fft2(gray)
    fshift = np.fft.fftshift(f)
    magnitude = np.abs(fshift)
    h, w = magnitude.shape
    cy, cx = h // 2, w // 2
    mask = np.ones_like(magnitude, dtype=bool)
    r = min(h, w) // 4
    mask[cy - r:cy + r, cx - r:cx + r] = False
    high_freq = magnitude[mask]

    peak_ratio = float(np.max(high_freq) / (np.mean(high_freq) + 1e-6))

    looks_real = (lap_var > LAPLACIAN_MIN) and (peak_ratio < FFT_PEAK_MAX)

    return looks_real, {
        "laplacian_variance": round(lap_var, 1),
        "fft_peak_ratio": round(peak_ratio, 2),
        "threshold_lap": LAPLACIAN_MIN,
        "threshold_fft": FFT_PEAK_MAX,
    }


def _bbox_from_landmarks(landmarks, margin=20):
    """Approximate face bbox from landmarks."""
    if landmarks is None:
        return None
    x_min = int(np.min(landmarks[:, 0])) - margin
    y_min = int(np.min(landmarks[:, 1])) - margin
    x_max = int(np.max(landmarks[:, 0])) + margin
    y_max = int(np.max(landmarks[:, 1])) + margin
    return (x_min, y_min, x_max, y_max)


def evaluate_liveness(photo_open: np.ndarray,
                      photo_closed: np.ndarray,
                      photo_turned: np.ndarray) -> LivenessResult:
    """
    Main entry point. Runs the overall 3-signal analysis.
    Called AFTER the per-step validation has already accepted all photos.
    """
    if not MEDIAPIPE_AVAILABLE:
        return LivenessResult(
            is_live=False, confidence=0.0,
            blink_detected=False, head_movement_detected=False,
            texture_looks_real=False,
            details={},
            reason="mediapipe is not installed — liveness engine unavailable.",
        )

    lm_open = _get_landmarks(photo_open)
    lm_closed = _get_landmarks(photo_closed)
    lm_turned = _get_landmarks(photo_turned)

    if lm_open is None or lm_closed is None or lm_turned is None:
        return LivenessResult(
            is_live=False, confidence=0.0,
            blink_detected=False, head_movement_detected=False,
            texture_looks_real=False,
            details={},
            reason="Face not detected in one or more photos.",
        )

    blink, blink_info = detect_blink(lm_open, lm_closed)
    head, head_info = detect_head_movement(lm_open, lm_turned)

    bbox_open = _bbox_from_landmarks(lm_open)
    bbox_closed = _bbox_from_landmarks(lm_closed)
    bbox_turned = _bbox_from_landmarks(lm_turned)

    tex_open_ok, tex_open = analyze_texture(photo_open, bbox_open)
    tex_closed_ok, tex_closed = analyze_texture(photo_closed, bbox_closed)
    tex_turned_ok, tex_turned = analyze_texture(photo_turned, bbox_turned)

    texture_ok = tex_open_ok and tex_closed_ok and tex_turned_ok

    score = 0.0
    if blink: score += 0.40
    if head: score += 0.30
    if texture_ok: score += 0.30

    is_live = (score >= 0.50) and (blink or head)

    reasons = []
    if not blink: reasons.append("no blink detected")
    if not head: reasons.append("no head movement")
    if not texture_ok: reasons.append("suspicious texture (possible print/screen)")

    if is_live:
        reason = "Liveness confirmed — blink and/or head movement verified."
    else:
        reason = "Possible spoof: " + ", ".join(reasons) + "."

    return LivenessResult(
        is_live=is_live,
        confidence=round(score, 2),
        blink_detected=blink,
        head_movement_detected=head,
        texture_looks_real=texture_ok,
        details={
            "blink": blink_info,
            "head": head_info,
            "texture": {
                "open": tex_open,
                "closed": tex_closed,
                "turned": tex_turned,
            },
        },
        reason=reason,
    )


# ================================================================
# SELF-TEST
# ================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("liveness_engine.py — self test")
    print("=" * 60)

    print(f"mediapipe available: {MEDIAPIPE_AVAILABLE}")

    # Blank images
    dummy = np.full((480, 640, 3), 128, dtype=np.uint8)
    result = evaluate_liveness(dummy, dummy, dummy)
    print(f"\nBlank images → is_live={result.is_live}, reason='{result.reason}'")

    # Texture test on random noise
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, (480, 640, 3), dtype=np.uint8)
    looks_real, info = analyze_texture(noise)
    print(f"\nRandom noise texture → looks_real={looks_real}")
    print(f"  info: {info}")

    # Flat image → low variance → spoof suspicion
    flat = np.full((480, 640, 3), 128, dtype=np.uint8)
    looks_real, info = analyze_texture(flat)
    print(f"\nFlat image texture → looks_real={looks_real}")
    print(f"  info: {info}")

    # Validation function tests (should all return False for blank images)
    print("\nValidation functions on blank image:")
    ok, msg, _ = validate_eyes_open(dummy)
    print(f"  validate_eyes_open    → ok={ok}, msg='{msg}'")
    ok, msg, _ = validate_eyes_closed(dummy)
    print(f"  validate_eyes_closed  → ok={ok}, msg='{msg}'")
    ok, msg, _ = validate_head_turned(dummy)
    print(f"  validate_head_turned  → ok={ok}, msg='{msg}'")

    print("\n✅ liveness_engine.py works.")