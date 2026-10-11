"""
Unified biometric verification engine.
Coordinates face + fingerprint verification, persists results to database.
Covers FR-04, FR-07, FR-13 (partial).
"""
import pickle
from datetime import datetime

import numpy as np

from database import get_session, Identity, BiometricReference, VerificationRecord
from face_engine import match_face
from mock_sdk import compare_templates


# ---------- Identity management ----------

def list_identities() -> list:
    """Return list of (id, display_name) tuples."""
    session = get_session()
    try:
        rows = session.query(Identity).order_by(Identity.display_name).all()
        return [(r.id, r.display_name) for r in rows]
    finally:
        session.close()


def get_identity(identity_id: int) -> Identity:
    session = get_session()
    try:
        return session.query(Identity).get(identity_id)
    finally:
        session.close()


def create_identity(display_name: str, consent: bool = True) -> int:
    """Create a new identity. Returns new ID."""
    session = get_session()
    try:
        existing = session.query(Identity).filter_by(display_name=display_name).first()
        if existing:
            return existing.id
        identity = Identity(display_name=display_name, consent_status=consent)
        session.add(identity)
        session.commit()
        return identity.id
    finally:
        session.close()


def delete_identity(identity_id: int):
    session = get_session()
    try:
        identity = session.query(Identity).get(identity_id)
        if identity:
            session.delete(identity)
            session.commit()
    finally:
        session.close()


# ---------- Biometric reference enrollment ----------

def enroll_face(identity_id: int, embedding: np.ndarray, model_version: str = "buffalo_l"):
    """Store face embedding for identity."""
    session = get_session()
    try:
        # Remove existing face reference (re-enroll)
        session.query(BiometricReference).filter_by(
            identity_id=identity_id, modality="face"
        ).delete()

        ref = BiometricReference(
            identity_id=identity_id,
            modality="face",
            protected_reference=pickle.dumps(embedding),
            model_or_sdk_version=model_version,
        )
        session.add(ref)
        session.commit()
    finally:
        session.close()


def enroll_fingerprint(identity_id: int, template: np.ndarray, sdk_version: str = "Mock SDK 1.0.0"):
    """Store fingerprint template for identity."""
    session = get_session()
    try:
        session.query(BiometricReference).filter_by(
            identity_id=identity_id, modality="fingerprint"
        ).delete()

        ref = BiometricReference(
            identity_id=identity_id,
            modality="fingerprint",
            protected_reference=pickle.dumps(template),
            model_or_sdk_version=sdk_version,
        )
        session.add(ref)
        session.commit()
    finally:
        session.close()


def get_references_by_modality(modality: str) -> dict:
    """Return {identity_name: reference_array} for a modality."""
    session = get_session()
    try:
        refs = session.query(BiometricReference).filter_by(modality=modality).all()
        result = {}
        for ref in refs:
            identity = session.query(Identity).get(ref.identity_id)
            if identity and identity.enrollment_status == "active":
                result[identity.display_name] = pickle.loads(ref.protected_reference)
        return result
    finally:
        session.close()


# ---------- Verification ----------

def verify_face(query_embedding: np.ndarray, threshold: float = 0.4) -> dict:
    """Verify a face query against all enrolled face references."""
    references = get_references_by_modality("face")

    if not references:
        result = {
            "result": "Unable to Verify",
            "reason": "No face references enrolled",
            "best_match": None, "best_score": 0.0, "all_scores": {},
        }
    else:
        result = match_face(query_embedding, references, threshold=threshold)

    # Persist verification record
    _save_verification(
        identity_id=None,
        modality="face",
        verification_type="1:N",
        result=result["result"],
        score=result.get("best_score", 0.0),
        source="face_engine",
    )
    return result


def verify_fingerprint(query_template: np.ndarray, threshold: float = 0.85) -> dict:
    """Verify a fingerprint query against all enrolled templates."""
    references = get_references_by_modality("fingerprint")

    if not references:
        result = {
            "result": "Unable to Verify",
            "reason": "No fingerprint references enrolled",
            "best_match": None, "best_score": 0.0, "all_scores": {},
        }
    else:
        scores = {name: compare_templates(query_template, ref)
                  for name, ref in references.items()}
        best_match = max(scores, key=scores.get)
        best_score = scores[best_match]
        result = {
            "result": "Match" if best_score >= threshold else "No Match",
            "best_match": best_match,
            "best_score": best_score,
            "all_scores": scores,
            "threshold": threshold,
        }

    _save_verification(
        identity_id=None,
        modality="fingerprint",
        verification_type="1:N",
        result=result["result"],
        score=result.get("best_score", 0.0),
        source="mock_sdk",
    )
    return result


def _save_verification(identity_id, modality, verification_type, result, score, source):
    """Persist a VerificationRecord."""
    session = get_session()
    try:
        record = VerificationRecord(
            identity_id=identity_id,
            modality=modality,
            verification_type=verification_type,
            result=result,
            score=score,
            source=source,
        )
        session.add(record)
        session.commit()
    finally:
        session.close()


# ---------- History ----------

def get_verification_history(limit: int = 100) -> list:
    """Return most recent verification records."""
    session = get_session()
    try:
        rows = (
            session.query(VerificationRecord)
            .order_by(VerificationRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [
            {
                "id": r.id,
                "identity_id": r.identity_id,
                "modality": r.modality,
                "type": r.verification_type,
                "result": r.result,
                "score": r.score,
                "source": r.source,
                "created_at": r.created_at,
            }
            for r in rows
        ]
    finally:
        session.close()


def get_stats() -> dict:
    """Return aggregate stats for dashboard."""
    session = get_session()
    try:
        total_identities = session.query(Identity).count()
        total_verifications = session.query(VerificationRecord).count()
        matches = session.query(VerificationRecord).filter_by(result="Match").count()
        no_matches = session.query(VerificationRecord).filter_by(result="No Match").count()
        unable = session.query(VerificationRecord).filter_by(result="Unable to Verify").count()
        return {
            "total_identities": total_identities,
            "total_verifications": total_verifications,
            "matches": matches,
            "no_matches": no_matches,
            "unable": unable,
        }
    finally:
        session.close()