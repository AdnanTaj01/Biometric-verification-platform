"""Tests for the audit logging system."""
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


def test_log_and_query():
    from audit import log, query
    from database import EventType, Outcome, SourceModule
    log(EventType.LOGIN, Outcome.SUCCESS, SourceModule.PROJECT_7_AUTH,
        actor="test@example.com")
    logs = query()
    assert len(logs) == 1
    assert logs[0]["actor"] == "test@example.com"
    assert logs[0]["event_type"] == EventType.LOGIN


def test_sensitive_metadata_redacted():
    from audit import log, query
    from database import EventType, Outcome, SourceModule
    log(
        EventType.ADMIN_CHANGE, Outcome.SUCCESS, SourceModule.PROJECT_8_AUDIT,
        actor="admin@example.com",
        metadata={
            "password": "super_secret_value",
            "private_key": "-----BEGIN PRIVATE KEY-----",
            "changed_field": "role",
        },
    )
    logs = query()
    md = logs[0]["metadata"]
    assert "super_secret_value" not in md
    assert "-----BEGIN PRIVATE KEY-----" not in md
    assert "[REDACTED]" in md
    assert "role" in md


def test_filters_work():
    from audit import log, query
    from database import EventType, Outcome, SourceModule
    log(EventType.LOGIN, Outcome.SUCCESS, SourceModule.PROJECT_7_AUTH)
    log(EventType.DOCUMENT_SIGNED, Outcome.SUCCESS, SourceModule.PROJECT_5_SIGNING)
    log(EventType.LOGIN, Outcome.FAILURE, SourceModule.PROJECT_7_AUTH)

    assert len(query()) == 3
    assert len(query(event_type=EventType.LOGIN)) == 2
    assert len(query(outcome=Outcome.SUCCESS)) == 2
    assert len(query(source_module=SourceModule.PROJECT_7_AUTH)) == 2


def test_stats_aggregation():
    from audit import log, stats
    from database import EventType, Outcome, SourceModule
    log(EventType.LOGIN, Outcome.SUCCESS, SourceModule.PROJECT_7_AUTH)
    log(EventType.LOGIN, Outcome.FAILURE, SourceModule.PROJECT_7_AUTH)
    log(EventType.DOCUMENT_SIGNED, Outcome.SUCCESS, SourceModule.PROJECT_5_SIGNING)

    s = stats()
    assert s["total"] == 3
    assert s["by_outcome"]["success"] == 2
    assert s["by_outcome"]["failure"] == 1


def test_clear_all():
    from audit import log, query, clear_all
    from database import EventType, Outcome, SourceModule
    log(EventType.LOGIN, Outcome.SUCCESS, SourceModule.PROJECT_7_AUTH)
    assert len(query()) == 1
    n = clear_all()
    assert n == 1
    assert len(query()) == 0