"""
Fingerprint verification engine.

Covers SRS requirement FR-07:
- Use supported fingerprint matcher to verify captured template
- Results: successful verification, failed verification, poor-quality sample, scanner error
"""
import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from mock_sdk import compare_templates


# ---------- Template storage ----------
DEFAULT_STORE = "data/fingerprints.pkl"


def load_templates(path: str = DEFAULT_STORE) -> dict:
    """Load enrolled fingerprint templates from disk."""
    if not Path(path).exists():
        return {}
    try:
        with open(path, "rb") as f:
            data = pickle.load(f)
            if not isinstance(data, dict):
                return {}
            return data
    except (EOFError, pickle.UnpicklingError, AttributeError):
        print(f"[fingerprint_engine] Warning: could not read {path}, starting fresh.")
        return {}


def save_templates(templates: dict, path: str = DEFAULT_STORE):
    """Save enrolled templates to disk."""
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(templates, f)


def enroll_template(identity_name: str, template: np.ndarray,
                     path: str = DEFAULT_STORE) -> int:
    """Enroll a template for an identity. Returns total count after enrollment."""
    templates = load_templates(path)
    templates[identity_name] = template
    save_templates(templates, path)
    return len(templates)


def verify_template(query_template: np.ndarray,
                     threshold: float = 0.85,
                     path: str = DEFAULT_STORE) -> dict:
    """
    Compare query template against all enrolled templates.

    Args:
        query_template: 512-byte array from a fresh capture
        threshold: similarity threshold (0.0 - 1.0) for Match
        path: storage location of enrolled templates

    Returns:
        dict with result and details
    """
    enrolled = load_templates(path)

    if not enrolled:
        return {
            "result": "Unable to Verify",
            "reason": "No enrolled fingerprints",
            "best_match": None,
            "best_score": 0.0,
            "all_scores": {},
            "threshold": threshold,
        }

    scores = {}
    for name, ref in enrolled.items():
        scores[name] = compare_templates(query_template, ref)

    best_match = max(scores, key=scores.get)
    best_score = scores[best_match]

    result = "Match" if best_score >= threshold else "No Match"

    return {
        "result": result,
        "best_match": best_match,
        "best_score": best_score,
        "all_scores": scores,
        "threshold": threshold,
    }