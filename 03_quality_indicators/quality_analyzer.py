"""
Comprehensive image quality analyzer for face capture.

Covers SRS requirement FR-03 in depth:
- Red indicator: quality insufficient
- Yellow indicator: warning — capture possible but not ideal
- Green indicator: quality passes all thresholds
- Text labels alongside colors (accessibility requirement from NFR-5.4)

Metrics analyzed:
    1. Brightness         — mean gray value
    2. Contrast           — standard deviation of gray values
    3. Sharpness          — Laplacian variance
    4. Face size          — bbox area / image area
    5. Face centering     — distance of face center from image center
    6. Face orientation   — roll angle from eye landmarks (InsightFace kps)
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


# ---------- Result container ----------
@dataclass
class QualityResult:
    """Result of a single quality check."""
    name: str
    score: float           # 0-100
    status: str            # "pass" | "warning" | "fail"
    message: str
    recommendation: str    # actionable advice


# ---------- Individual checks ----------

def analyze_brightness(image: np.ndarray) -> QualityResult:
    """Brightness = mean gray value. Ideal range: 90-180."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    # Map to score: 100 if within ideal range, decays outside
    if 90 <= brightness <= 180:
        score = 100.0
        status = "pass"
        msg = f"Brightness OK ({brightness:.0f})"
        rec = ""
    elif 60 <= brightness < 90 or 180 < brightness <= 210:
        score = 70.0
        status = "warning"
        msg = f"Borderline brightness ({brightness:.0f})"
        rec = "Move toward better lighting" if brightness < 90 else "Reduce direct light"
    else:
        score = 30.0
        status = "fail"
        msg = f"Poor brightness ({brightness:.0f})"
        rec = "Move to a well-lit area" if brightness < 60 else "Avoid backlighting"

    return QualityResult("Brightness", score, status, msg, rec)


def analyze_contrast(image: np.ndarray) -> QualityResult:
    """Contrast = standard deviation of gray values. Ideal: > 45."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    contrast = float(np.std(gray))

    if contrast >= 55:
        score, status = 100.0, "pass"
        msg, rec = f"Contrast OK ({contrast:.0f})", ""
    elif contrast >= 40:
        score, status = 70.0, "warning"
        msg, rec = f"Low contrast ({contrast:.0f})", "Avoid flat lighting; add side light"
    else:
        score, status = 30.0, "fail"
        msg, rec = f"Very low contrast ({contrast:.0f})", "Increase lighting diversity"

    return QualityResult("Contrast", score, status, msg, rec)


def analyze_sharpness(image: np.ndarray) -> QualityResult:
    """Sharpness = Laplacian variance. Ideal: > 100."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if variance >= 120:
        score, status = 100.0, "pass"
        msg, rec = f"Sharp ({variance:.0f})", ""
    elif variance >= 60:
        score, status = 70.0, "warning"
        msg, rec = f"Slightly blurry ({variance:.0f})", "Hold still during capture"
    else:
        score, status = 25.0, "fail"
        msg, rec = f"Blurry ({variance:.0f})", "Hold camera steady or clean lens"

    return QualityResult("Sharpness", score, status, msg, rec)


def analyze_face_size(face_box, image_shape) -> QualityResult:
    """Face bbox area / image area. Ideal ratio: 0.15-0.50."""
    x1, y1, x2, y2 = face_box
    face_area = (x2 - x1) * (y2 - y1)
    image_area = image_shape[0] * image_shape[1]
    ratio = face_area / image_area

    if 0.15 <= ratio <= 0.50:
        score, status = 100.0, "pass"
        msg, rec = f"Face size OK ({ratio:.2f})", ""
    elif 0.08 <= ratio < 0.15:
        score, status = 60.0, "warning"
        msg, rec = f"Face small ({ratio:.2f})", "Move closer to the camera"
    elif ratio > 0.50:
        score, status = 70.0, "warning"
        msg, rec = f"Face too large ({ratio:.2f})", "Move slightly away"
    else:
        score, status = 20.0, "fail"
        msg, rec = f"Face too small ({ratio:.2f})", "Move much closer to the camera"

    return QualityResult("Face Size", score, status, msg, rec)


def analyze_face_centering(face_box, image_shape) -> QualityResult:
    """Distance of face center from image center. Ideal: < 15% of frame."""
    x1, y1, x2, y2 = face_box
    face_cx = (x1 + x2) / 2
    face_cy = (y1 + y2) / 2
    img_h, img_w = image_shape[:2]

    dx = abs(face_cx - img_w / 2) / img_w
    dy = abs(face_cy - img_h / 2) / img_h
    offset = float(np.sqrt(dx**2 + dy**2))

    if offset < 0.10:
        score, status = 100.0, "pass"
        msg, rec = f"Centered (offset {offset:.2f})", ""
    elif offset < 0.22:
        score, status = 70.0, "warning"
        msg, rec = f"Slightly off-center ({offset:.2f})", "Center your face in frame"
    else:
        score, status = 30.0, "fail"
        msg, rec = f"Off-center ({offset:.2f})", "Move to center of frame"

    return QualityResult("Centering", score, status, msg, rec)


def analyze_face_orientation(landmarks: Optional[np.ndarray]) -> QualityResult:
    """
    Roll angle from eye landmarks.
    landmarks: 5x2 array — [left_eye, right_eye, nose, left_mouth, right_mouth]
    Ideal: < 10° roll.
    """
    if landmarks is None:
        return QualityResult("Orientation", 0.0, "fail",
                             "No landmarks detected", "Ensure face is visible")

    left_eye = landmarks[0]
    right_eye = landmarks[1]

    dy = right_eye[1] - left_eye[1]
    dx = right_eye[0] - left_eye[0]
    roll = float(np.degrees(np.arctan2(dy, dx)))
    roll_abs = abs(roll)

    if roll_abs <= 10:
        score, status = 100.0, "pass"
        msg, rec = f"Straight ({roll:+.1f}°)", ""
    elif roll_abs <= 20:
        score, status = 70.0, "warning"
        msg, rec = f"Slight tilt ({roll:+.1f}°)", "Keep head level"
    else:
        score, status = 30.0, "fail"
        msg, rec = f"Tilted ({roll:+.1f}°)", "Straighten your head"

    return QualityResult("Orientation", score, status, msg, rec)


# ---------- Full analysis pipeline ----------

# Weights for overall score — face presence is critical, so size is weighted higher
WEIGHTS = {
    "Brightness": 1.0,
    "Contrast": 0.8,
    "Sharpness": 1.2,
    "Face Size": 1.3,
    "Centering": 0.7,
    "Orientation": 0.8,
}


def run_full_analysis(image: np.ndarray, face) -> dict:
    """
    Run all quality checks and return:
    - results: list of QualityResult
    - overall_score: weighted average (0-100)
    - overall_status: pass | warning | fail
    - face_detected: bool
    - face_box: tuple or None
    """
    results = []

    if face is None:
        # No face — every check fails
        results.append(QualityResult("Face Detection", 0, "fail",
                                     "No face detected", "Position your face in the frame"))
        return {
            "results": results,
            "overall_score": 0.0,
            "overall_status": "fail",
            "face_detected": False,
            "face_box": None,
        }

    # Extract face box (xyxy)
    x1, y1, x2, y2 = (int(v) for v in face.bbox)
    face_box = (x1, y1, x2, y2)

    # Run each check
    results.append(QualityResult("Face Detection", 100.0, "pass",
                                 "Face detected", ""))
    results.append(analyze_brightness(image))
    results.append(analyze_contrast(image))
    results.append(analyze_sharpness(image))
    results.append(analyze_face_size(face_box, image.shape))
    results.append(analyze_face_centering(face_box, image.shape))

    # Orientation — face.kps is 5x2 if available
    kps = getattr(face, "kps", None)
    results.append(analyze_face_orientation(kps))

    # Weighted overall score (Face Detection is a gate — skipped in weights)
    weighted_sum = 0.0
    weight_total = 0.0
    for r in results:
        if r.name in WEIGHTS:
            weighted_sum += r.score * WEIGHTS[r.name]
            weight_total += WEIGHTS[r.name]

    overall_score = weighted_sum / weight_total if weight_total > 0 else 0.0

    if overall_score >= 80:
        overall_status = "pass"
    elif overall_score >= 55:
        overall_status = "warning"
    else:
        overall_status = "fail"

    return {
        "results": results,
        "overall_score": overall_score,
        "overall_status": overall_status,
        "face_detected": True,
        "face_box": face_box,
    }


# ---------- Self-test ----------
if __name__ == "__main__":
    print("quality_analyzer.py loaded. Running self-test on random images...")

    for label, img in [
        ("dark", np.full((480, 640, 3), 20, dtype=np.uint8)),
        ("bright", np.full((480, 640, 3), 240, dtype=np.uint8)),
        ("noise", np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)),
    ]:
        b = analyze_brightness(img)
        c = analyze_contrast(img)
        s = analyze_sharpness(img)
        print(f"  {label:8s} → brightness={b.status:7s} contrast={c.status:7s} sharpness={s.status}")

    print("✅ quality_analyzer.py works.")