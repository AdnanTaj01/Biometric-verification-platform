"""Tests for the biometric verification database (SQLAlchemy models).

Note: We test database.py directly — not verification.py — because
verification.py imports face_engine.py which requires insightface
(a 300MB+ package not installed in the CI environment).
"""
import pytest


@pytest.fixture(autouse=True)
def clean_db():
    """Truncate all tables before each test (Windows-friendly)."""
    from database import init_db, get_session, Base
    init_db()
    session = get_session()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            session.execute(table.delete())
        session.commit()
    finally:
        session.close()
    yield


def test_create_identity_direct():
    from database import get_session, Identity
    session = get_session()
    try:
        identity = Identity(display_name="Test User A", consent_status=True)
        session.add(identity)
        session.commit()
        assert identity.id is not None
        assert identity.display_name == "Test User A"
    finally:
        session.close()


def test_identity_uniqueness_on_display_name():
    from database import get_session, Identity
    from sqlalchemy.exc import IntegrityError

    session = get_session()
    try:
        session.add(Identity(display_name="Duplicate Name"))
        session.commit()

        session.add(Identity(display_name="Duplicate Name"))
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_biometric_reference_link():
    from database import get_session, Identity, BiometricReference
    import pickle
    import numpy as np

    session = get_session()
    try:
        identity = Identity(display_name="Ref Test")
        session.add(identity)
        session.commit()

        ref = BiometricReference(
            identity_id=identity.id,
            modality="face",
            protected_reference=pickle.dumps(np.zeros(512, dtype=np.float32)),
            model_or_sdk_version="buffalo_l",
        )
        session.add(ref)
        session.commit()

        assert ref.id is not None
        assert ref.identity_id == identity.id
    finally:
        session.close()


def test_verification_record_creation():
    from database import get_session, Identity, VerificationRecord

    session = get_session()
    try:
        identity = Identity(display_name="VR Test")
        session.add(identity)
        session.commit()

        record = VerificationRecord(
            identity_id=identity.id,
            modality="face",
            verification_type="1:N",
            result="Match",
            score=0.85,
            source="face_engine",
        )
        session.add(record)
        session.commit()

        assert record.id is not None
        assert record.result == "Match"
        assert record.score == 0.85
    finally:
        session.close()


def test_delete_identity_cascades():
    from database import get_session, Identity, BiometricReference
    import pickle
    import numpy as np

    session = get_session()
    try:
        identity = Identity(display_name="Cascade Test")
        session.add(identity)
        session.commit()

        session.add(BiometricReference(
            identity_id=identity.id,
            modality="face",
            protected_reference=pickle.dumps(np.zeros(512, dtype=np.float32)),
        ))
        session.commit()

        count = session.query(BiometricReference).filter_by(
            identity_id=identity.id
        ).count()
        assert count == 1

        session.delete(identity)
        session.commit()

        count = session.query(BiometricReference).filter_by(
            identity_id=identity.id
        ).count()
        assert count == 0
    finally:
        session.close()