"""
Face detection and recognition using InsightFace.
Handles embedding generation and matching via sklearn cosine_similarity.

Covers SRS requirement FR-04:
- Generate numerical embedding from captured face
- Compare against registered test identity's reference embedding
- Possible results: Match / No Match / Unable to Verify / Processing Error
"""
import cv2
import numpy as np
import pickle
from pathlib import Path
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity


# Initialize InsightFace once (it's heavy)
_app = None


def get_face_app():
    """Lazy load InsightFace model. Downloads ~300MB on first run."""
    global _app
    if _app is None:
        print("[face_engine] Loading InsightFace model (buffalo_l)...")
        _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(640, 640))
        print("[face_engine] Model loaded.")
    return _app


def detect_faces(image: np.ndarray):
    """
    Detect faces in an image.
    Returns list of face objects with bbox, kps, embedding, etc.
    """
    app = get_face_app()
    faces = app.get(image)
    return faces


def get_largest_face(faces):
    """Return the largest face (by bbox area) from a list."""
    if not faces:
        return None
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def match_face(query_embedding: np.ndarray, registered: dict, threshold: float = 0.4):
    """
    Match query embedding against all registered identities
    using sklearn's cosine_similarity (industry standard, batch-optimized).

    Args:
        query_embedding: np.ndarray (512,) from live capture
        registered: dict {identity_name: embedding (512,)}
        threshold: cosine similarity threshold for Match

    Returns:
        dict with result, best_match, best_score, all_scores, threshold
    """
    if not registered:
        return {
            "result": "Unable to Verify",
            "reason": "No registered identities found",
            "best_match": None,
            "best_score": 0.0,
            "all_scores": {},
            "threshold": threshold,
        }

    names = list(registered.keys())
    # Stack registered embeddings into matrix (N, 512)
    matrix = np.stack([registered[n] for n in names])
    query = query_embedding.reshape(1, -1)

    # Single sklearn call — returns (1, N) array
    scores = cosine_similarity(query, matrix)[0]

    # Map back to names
    score_dict = {name: float(score) for name, score in zip(names, scores)}

    best_match = max(score_dict, key=score_dict.get)
    best_score = score_dict[best_match]

    if best_score >= threshold:
        result = "Match"
    else:
        result = "No Match"

    return {
        "result": result,
        "best_match": best_match,
        "best_score": best_score,
        "all_scores": score_dict,
        "threshold": threshold,
    }


def save_embeddings(registered: dict, path: str = "data/embeddings.pkl"):
    """Save registered embeddings to disk."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(registered, f)


def load_embeddings(path: str = "data/embeddings.pkl") -> dict:
    """
    Load registered embeddings from disk.
    Returns empty dict if file doesn't exist, is empty, or is corrupt.
    """
    if not Path(path).exists():
        return {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except (EOFError, pickle.UnpicklingError, AttributeError):
        # Empty or corrupt file — treat as no registered identities
        print(f"[face_engine] Warning: could not read {path}, starting fresh.")
        return {}


def bbox_to_xyxy(bbox):
    """Convert InsightFace bbox to (x1, y1, x2, y2) ints."""
    return tuple(int(v) for v in bbox)


# Quick test — run this file directly to verify model loads and detects nothing on random noise
if __name__ == "__main__":
    print("face_engine.py loaded successfully")
    print("Loading model (this may take a moment on first run)...")
    app = get_face_app()
    print("Model loaded. Testing on random noise image...")
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    faces = detect_faces(dummy)
    print(f"Detected {len(faces)} faces in noise (expected 0)")
    print("✅ face_engine.py works")