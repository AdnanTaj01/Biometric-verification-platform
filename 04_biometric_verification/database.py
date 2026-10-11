"""
Database models for the biometric verification engine.

Covers SRS Database Design section:
- Users (in Project 7)
- TestIdentities
- BiometricReferences
- VerificationRecords
"""
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime,
    ForeignKey, LargeBinary, Boolean,
)
from sqlalchemy.orm import declarative_base, sessionmaker, relationship


DB_PATH = "data/biometric.db"
DB_URL = f"sqlite:///{DB_PATH}"

Base = declarative_base()


class Identity(Base):
    """Registered test identity (SRS: TestIdentities table)."""
    __tablename__ = "identities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    display_name = Column(String, nullable=False, unique=True)
    consent_status = Column(Boolean, default=True)
    enrollment_status = Column(String, default="active")  # active | inactive
    created_at = Column(DateTime, default=datetime.utcnow)

    references = relationship(
        "BiometricReference",
        back_populates="identity",
        cascade="all, delete-orphan",
    )
    verifications = relationship(
        "VerificationRecord",
        back_populates="identity",
    )


class BiometricReference(Base):
    """Stored biometric reference (SRS: BiometricReferences table)."""
    __tablename__ = "biometric_references"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identity_id = Column(Integer, ForeignKey("identities.id"), nullable=False)
    modality = Column(String, nullable=False)  # "face" | "fingerprint"
    protected_reference = Column(LargeBinary, nullable=False)  # pickled embedding
    model_or_sdk_version = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    identity = relationship("Identity", back_populates="references")


class VerificationRecord(Base):
    """Verification attempt record (SRS: VerificationRecords table)."""
    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    identity_id = Column(Integer, ForeignKey("identities.id"), nullable=True)
    modality = Column(String, nullable=False)  # "face" | "fingerprint"
    verification_type = Column(String)         # "1:N" | "1:1"
    result = Column(String, nullable=False)    # "Match" | "No Match" | "Unable to Verify"
    score = Column(Float)
    source = Column(String)                    # "face_engine" | "mock_sdk"
    created_at = Column(DateTime, default=datetime.utcnow)

    identity = relationship("Identity", back_populates="verifications")


# ---------- Engine setup ----------
def get_engine():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    return create_engine(DB_URL, echo=False)


def init_db():
    """Create all tables. Safe to call multiple times."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine


def get_session():
    """Get a new SQLAlchemy session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


# ---------- Self-test ----------
if __name__ == "__main__":
    init_db()
    session = get_session()

    # Test insert
    test_identity = Identity(display_name="__test_identity__", consent_status=True)
    session.add(test_identity)
    session.commit()

    print(f"Created test identity: id={test_identity.id}, name={test_identity.display_name}")

    # Cleanup
    session.delete(test_identity)
    session.commit()
    session.close()

    print("✅ database.py works. Tables created.")