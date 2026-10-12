"""
Central audit logging API.

Any module (Projects 1-7) can import this to write events to the
central audit database. Provides:
    - log() — write an event
    - query() — filtered read
    - stats() — aggregate metrics for dashboard
    - export_csv() — download as CSV

Safe metadata policy: NEVER log passwords, private keys, or raw biometric data.
"""
import json
from datetime import datetime, timedelta

from sqlalchemy import func, desc

from database import get_session, AuditLog, EventType, Outcome


# ---------- Sensitive keys blocked from metadata ----------
_BLOCKED_KEYS = {
    "password", "password_hash", "passwd", "pwd",
    "private_key", "secret", "token", "api_key",
    "raw_image", "raw_biometric", "embedding", "fingerprint_image",
    "fingerprint_template", "face_embedding",
}


def _sanitize_metadata(metadata: dict) -> str:
    """
    Strip blocked keys from metadata before storing.
    Returns JSON string (or empty string if metadata is empty).
    """
    if not metadata:
        return ""
    safe = {}
    for k, v in metadata.items():
        if k.lower() in _BLOCKED_KEYS:
            safe[k] = "[REDACTED]"
        else:
            # Only allow JSON-serializable primitives
            if isinstance(v, (str, int, float, bool, type(None))):
                safe[k] = v
            else:
                safe[k] = str(v)[:200]
    return json.dumps(safe)


# ---------- Write ----------
def log(
    event_type: str,
    outcome: str,
    source_module: str,
    actor: str = "system",
    target: str = None,
    metadata: dict = None,
) -> int:
    """
    Write an audit log entry. Returns the new row ID.

    Args:
        event_type: one of EventType.* constants
        outcome: one of Outcome.* constants
        source_module: one of SourceModule.* constants
        actor: user email (or "system")
        target: identity/document/user being acted on
        metadata: dict of safe metadata (passwords etc. auto-redacted)
    """
    session = get_session()
    try:
        entry = AuditLog(
            timestamp=datetime.utcnow(),
            actor=actor or "system",
            event_type=event_type,
            outcome=outcome,
            target=target,
            source_module=source_module,
            safe_metadata=_sanitize_metadata(metadata or {}),
        )
        session.add(entry)
        session.commit()
        return entry.id
    finally:
        session.close()


# ---------- Read ----------
def query(
    limit: int = 500,
    event_type: str = None,
    outcome: str = None,
    source_module: str = None,
    actor: str = None,
    since: datetime = None,
) -> list:
    """Query audit log entries with optional filters."""
    session = get_session()
    try:
        q = session.query(AuditLog)

        if event_type:
            q = q.filter(AuditLog.event_type == event_type)
        if outcome:
            q = q.filter(AuditLog.outcome == outcome)
        if source_module:
            q = q.filter(AuditLog.source_module == source_module)
        if actor:
            q = q.filter(AuditLog.actor == actor)
        if since:
            q = q.filter(AuditLog.timestamp >= since)

        rows = q.order_by(desc(AuditLog.timestamp)).limit(limit).all()

        return [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "actor": r.actor,
                "event_type": r.event_type,
                "outcome": r.outcome,
                "target": r.target,
                "source_module": r.source_module,
                "metadata": r.safe_metadata,
            }
            for r in rows
        ]
    finally:
        session.close()


# ---------- Stats (FR-14) ----------
def stats() -> dict:
    """Aggregate metrics for the admin dashboard (FR-14)."""
    session = get_session()
    try:
        total = session.query(AuditLog).count()

        # By event type
        by_type = dict(
            session.query(AuditLog.event_type, func.count(AuditLog.id))
            .group_by(AuditLog.event_type)
            .all()
        )

        # By outcome
        by_outcome = dict(
            session.query(AuditLog.outcome, func.count(AuditLog.id))
            .group_by(AuditLog.outcome)
            .all()
        )

        # By source module
        by_module = dict(
            session.query(AuditLog.source_module, func.count(AuditLog.id))
            .group_by(AuditLog.source_module)
            .all()
        )

        # Last 24 hours
        day_ago = datetime.utcnow() - timedelta(hours=24)
        last_24h = session.query(AuditLog).filter(AuditLog.timestamp >= day_ago).count()

        # Distinct actors
        actors = [row[0] for row in session.query(AuditLog.actor).distinct().all() if row[0]]

        return {
            "total": total,
            "last_24h": last_24h,
            "by_type": by_type,
            "by_outcome": by_outcome,
            "by_module": by_module,
            "actors_count": len(actors),
            "actors": actors,
        }
    finally:
        session.close()


def clear_all():
    """Delete all audit log entries. Returns count deleted."""
    session = get_session()
    try:
        n = session.query(AuditLog).delete()
        session.commit()
        return n
    finally:
        session.close()


# ---------- Self-test ----------
if __name__ == "__main__":
    from database import init_db, SourceModule

    init_db()
    clear_all()

    print("=" * 60)
    print("audit.py — self test")
    print("=" * 60)

    # Write a few events
    print("\n[1] Writing sample events...")
    log(EventType.LOGIN, Outcome.SUCCESS, SourceModule.PROJECT_7_AUTH,
        actor="admin@portfolio.local")
    log(EventType.BIOMETRIC_VERIFICATION, Outcome.MATCH, SourceModule.PROJECT_4_VERIFICATION,
        actor="operator@portfolio.local", target="Ali Khan",
        metadata={"score": 0.93, "modality": "face"})
    log(EventType.DOCUMENT_SIGNED, Outcome.SUCCESS, SourceModule.PROJECT_5_SIGNING,
        actor="signer@portfolio.local", target="contract.pdf")
    log(EventType.LOGIN, Outcome.FAILURE, SourceModule.PROJECT_7_AUTH,
        actor="attacker@evil.com", metadata={"reason": "bad_password"})

    # Test redaction
    log(EventType.ADMIN_CHANGE, Outcome.SUCCESS, SourceModule.PROJECT_8_AUDIT,
        actor="admin@portfolio.local",
        metadata={"password": "super_secret", "changed_field": "role"})

    print("[2] Reading back...")
    for e in query(limit=5):
        print(f"    [{e['event_type']:22s}] {e['actor']:25s} → {e['outcome']}")

    print("\n[3] Redaction test:")
    for e in query(event_type=EventType.ADMIN_CHANGE):
        print(f"    metadata: {e['metadata']}")
        assert "super_secret" not in e["metadata"], "Redaction failed!"
        print("    ✓ password was redacted")

    print("\n[4] Stats:")
    s = stats()
    print(f"    total events: {s['total']}")
    print(f"    by outcome: {s['by_outcome']}")
    print(f"    actors: {s['actors']}")

    print("\n✅ audit.py works.")