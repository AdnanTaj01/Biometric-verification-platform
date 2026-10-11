"""
Quality checks for face capture.
Returns pass/fail for each check so we can show red/green indicators.

Covers SRS requirement FR-03:
- Red indicator: face not detected or quality insufficient
- Green indicator: configured quality checks passed
"""
import cv2
import numpy as np


def check_brightness(image: np.ndarray, min_brightness: int = 60, max_brightness: int = 200):
    """Check if image brightness is in acceptable range."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    brightness = float(np.mean(gray))

    if brightness < min_brightness:
        return False, f"Too dark (brightness: {brightness:.1f})"
    if brightness > max_brightness:
        return False, f"Too bright (brightness: {brightness:.1f})"
    return True, f"Brightness OK ({brightness:.1f})"


def check_blur(image: np.ndarray, min_variance: float = 50.0):
    """Check if image is sharp enough using Laplacian variance."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    variance = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if variance < min_variance:
        return False, f"Too blurry (sharpness: {variance:.1f})"
    return True, f"Sharpness OK ({variance:.1f})"


def check_face_size(face_box, image_shape, min_ratio: float = 0.08):
    """Check if detected face is large enough in the frame."""
    x1, y1, x2, y2 = face_box
    face_area = (x2 - x1) * (y2 - y1)
    image_area = image_shape[0] * image_shape[1]
    ratio = face_area / image_area

    if ratio < min_ratio:
        return False, f"Face too small (ratio: {ratio:.2f})"
    return True, f"Face size OK (ratio: {ratio:.2f})"


def run_all_quality_checks(image: np.ndarray, face_box=None):
    """
    Run all quality checks and return a list of results.
    Each result: {"name": str, "passed": bool, "message": str}
    """
    results = []

    # Brightness
    passed, msg = check_brightness(image)
    results.append({"name": "Brightness", "passed": passed, "message": msg})

    # Blur
    passed, msg = check_blur(image)
    results.append({"name": "Sharpness", "passed": passed, "message": msg})

    # Face size (only if face detected)
    if face_box is not None:
        passed, msg = check_face_size(face_box, image.shape)
        results.append({"name": "Face Size", "passed": passed, "message": msg})
    else:
        results.append({
            "name": "Face Detected",
            "passed": False,
            "message": "No face detected in frame"
        })

    return results


def all_passed(results):
    """Return True if every check passed."""
    return all(r["passed"] for r in results)


# Quick test — run this file directly to verify it works
if __name__ == "__main__":
    print("quality_check.py loaded successfully")
    # Dummy test with a random image
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    results = run_all_quality_checks(dummy, face_box=(200, 100, 440, 340))
    for r in results:
        status = "✅" if r["passed"] else "❌"
        print(f"{status} {r['name']}: {r['message']}")
    print(f"All passed: {all_passed(results)}")