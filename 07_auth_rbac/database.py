"""
Database models for authentication and RBAC.

Covers SRS:
- Users table (from SRS Database Design section)
- AuditLogs table (partial — full audit in Project 8)

Roles (from SRS Section 3):
- admin:                 Administrator
- verification_operator: Verification Operator
- document_signer:       Document Signer
- document_verifier:     Document Verifier
"""
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean,
    DateTime, Text,
)
from sqlalchemy.orm import declarative_base, sessionmaker


DB_PATH = "data/auth.db"
DB_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()


# ---------- Constants ----------
ROLES = {
    "admin": "Administrator",
    "verification_operator": "Verification Operator",
    "document_signer": "Document Signer",
    "document_verifier": "Document Verifier",
}

# Permission matrix
PERMISSIONS = {
    "admin": [
        "manage_users",
        "view_audit_logs",
        "enroll_identities",
        "verify_biometric",
        "sign_documents",
        "verify_signatures",
    ],
    "verification_operator": [
        "verify_biometric",
    ],
    "document_signer": [
        "sign_documents",
    ],
    "document_verifier": [
        "verify_signatures",
    ],
}


# ---------- Models ----------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="verification_operator")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_email = Column(String, nullable=True)
    event_type = Column(String, nullable=False)   # login, logout, access_denied, etc.
    outcome = Column(String, nullable=False)      # success, failure
    metadata_json = Column(Text, nullable=True)   # safe metadata only
    timestamp = Column(DateTime, default=datetime.utcnow)


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
    session = get_session()

    # Quick self-test
    from auth import hash_password  # noqa
    test_email = "__test__@example.com"
    existing = session.query(User).filter_by(email=test_email).first()
    if existing:
        session.delete(existing)
        session.commit()

    u = User(email=test_email, password_hash="x", role="admin")
    session.add(u)
    session.commit()
    print(f"Created test user id={u.id}")
    session.delete(u)
    session.commit()
    session.close()
    print("✅ database.py works.")