"""Tests for authentication, hashing, and RBAC."""
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


def test_password_hashing_roundtrip():
    from auth import hash_password, verify_password
    h = hash_password("TestPass123")
    assert h != "TestPass123"
    assert verify_password("TestPass123", h)
    assert not verify_password("WrongPass1", h)


def test_password_policy():
    from auth import validate_password_strength
    ok, _ = validate_password_strength("short")
    assert not ok

    ok, _ = validate_password_strength("NoNumbersHere")
    assert not ok

    ok, _ = validate_password_strength("ValidPass123")
    assert ok


def test_email_validation():
    from auth import validate_email
    assert not validate_email("notanemail")[0]
    assert not validate_email("a@b")[0]
    assert validate_email("user@example.com")[0]


def test_permission_matrix():
    from auth import has_permission
    assert has_permission("admin", "manage_users")
    assert not has_permission("verification_operator", "manage_users")
    assert has_permission("document_signer", "sign_documents")
    assert not has_permission("document_verifier", "sign_documents")
    assert has_permission("admin", "view_audit_logs")


def test_create_and_authenticate_user():
    from auth import create_user, authenticate
    ok, err, _ = create_user("ci@test.local", "CITestPass123", "admin")
    assert ok, err

    ok, user, _ = authenticate("ci@test.local", "CITestPass123")
    assert ok
    assert user["role"] == "admin"
    assert user["email"] == "ci@test.local"


def test_duplicate_user_rejected():
    from auth import create_user
    create_user("dup@test.local", "TestPass123", "admin")
    ok, err, _ = create_user("dup@test.local", "TestPass123", "admin")
    assert not ok
    assert "already exists" in err.lower()


def test_inactive_user_cannot_login():
    from database import get_session, User
    from auth import create_user, authenticate
    create_user("inactive@test.local", "TestPass123", "admin")
    s = get_session()
    u = s.query(User).filter_by(email="inactive@test.local").first()
    u.is_active = False
    s.commit()
    s.close()

    ok, _, _ = authenticate("inactive@test.local", "TestPass123")
    assert not ok