"""
Face detection + embedding using InsightFace.
Covers FR-04.
"""
import numpy as np
from insightface.app import FaceAnalysis
from sklearn.metrics.pairwise import cosine_similarity


_app = None


def get_face_app():
    global _app
    if _app is None:
        print("[face_engine] Loading InsightFace...")
        _app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _app.prepare(ctx_id=0, det_size=(640, 640))
        print("[face_engine] Model loaded.")
    return _app


def detect_faces(image: np.ndarray):
    return get_face_app().get(image)


def get_largest_face(faces):
    if not faces:
        return None
    return max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))


def match_face(query_embedding: np.ndarray, registered: dict, threshold: float = 0.4) -> dict:
    """Match query against {name: embedding} using sklearn cosine."""
    if not registered:
        return {
            "result": "Unable to Verify",
            "reason": "No registered faces",
            "best_match": None, "best_score": 0.0,
            "all_scores": {}, "threshold": threshold,
        }

    names = list(registered.keys())
    matrix = np.stack([registered[n] for n in names])
    query = query_embedding.reshape(1, -1)
    scores = cosine_similarity(query, matrix)[0]
    score_dict = {n: float(s) for n, s in zip(names, scores)}

    best_match = max(score_dict, key=score_dict.get)
    best_score = score_dict[best_match]
    result = "Match" if best_score >= threshold else "No Match"

    return {
        "result": result,
        "best_match": best_match,
        "best_score": best_score,
        "all_scores": score_dict,
        "threshold": threshold,
    }


def bbox_to_xyxy(bbox):
    return tuple(int(v) for v in bbox)