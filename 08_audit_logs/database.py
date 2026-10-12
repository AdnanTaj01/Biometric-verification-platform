"""
Audit log database model.

Covers FR-13: record important events across all modules.
Designed to be imported by ANY project (1-7) as the central audit sink.

NEVER store here:
- passwords or password hashes
- private keys
- raw biometric samples (images, fingerprint images)
- full embeddings

Only store SAFE metadata: IDs, event types, outcomes, timestamps.
"""
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Text, Index,
)
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = "data/audit.db"
DB_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()


# ---------- Event types (aligned with SRS FR-13) ----------
class EventType:
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    ACCESS_DENIED = "access_denied"

    IDENTITY_ENROLLED = "identity_enrolled"
    IDENTITY_DELETED = "identity_deleted"

    BIOMETRIC_VERIFICATION = "biometric_verification"
    FINGERPRINT_VERIFICATION = "fingerprint_verification"

    PDF_UPLOADED = "pdf_uploaded"
    DOCUMENT_SIGNED = "document_signed"
    SIGNATURE_VERIFIED = "signature_verified"

    ADMIN_CHANGE = "admin_change"
    USER_CREATED = "user_created"
    USER_DEACTIVATED = "user_deactivated"
    ROLE_CHANGED = "role_changed"


# ---------- Outcomes ----------
class Outcome:
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"
    MATCH = "match"
    NO_MATCH = "no_match"
    UNABLE = "unable_to_verify"


# ---------- Source modules ----------
class SourceModule:
    PROJECT_1_FACE = "01_face_capture_recognition"
    PROJECT_2_FINGERPRINT = "02_fingerprint_scanner"
    PROJECT_3_QUALITY = "03_quality_indicators"
    PROJECT_4_VERIFICATION = "04_biometric_verification"
    PROJECT_5_SIGNING = "05_pdf_signing"
    PROJECT_6_VERIFY = "06_signature_verification"
    PROJECT_7_AUTH = "07_auth_rbac"
    PROJECT_8_AUDIT = "08_audit_logs"


# ---------- Model ----------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor = Column(String, nullable=True, index=True)       # user email, or "system"
    event_type = Column(String, nullable=False, index=True)
    outcome = Column(String, nullable=False, index=True)
    target = Column(String, nullable=True)                  # identity/document/user affected
    source_module = Column(String, nullable=False, index=True)
    safe_metadata = Column(Text, nullable=True)             # JSON string, sanitized

    __table_args__ = (
        Index("ix_time_type", "timestamp", "event_type"),
    )


# ---------- Engine ----------
def get_engine():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(DB_URL, echo=False)


def init_db():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


if __name__ == "__main__":
    init_db()
    print("✅ database.py works. Tables created.")