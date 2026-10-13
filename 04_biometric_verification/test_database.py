"""Tests for the biometric verification database."""
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


def test_create_identity():
    from verification import create_identity, list_identities
    iid = create_identity("Test User A")
    assert iid > 0
    identities = list_identities()
    assert any(name == "Test User A" for _, name in identities)


def test_duplicate_identity_returns_existing_id():
    from verification import create_identity
    id1 = create_identity("Test User B")
    id2 = create_identity("Test User B")
    assert id1 == id2


def test_get_stats():
    from verification import get_stats, create_identity
    create_identity("Test User C")
    s = get_stats()
    assert "total_identities" in s
    assert s["total_identities"] >= 1