"""
Generate realistic demo audit events for a portfolio demo.

Simulates what the audit log would look like after a few days of
usage across all 7 modules.
"""
import random
from datetime import datetime, timedelta

from audit import log, clear_all
from database import (
    init_db, EventType, Outcome, SourceModule,
)


DEMO_ACTORS = [
    "admin@portfolio.local",
    "operator@portfolio.local",
    "signer@portfolio.local",
    "verifier@portfolio.local",
]

DEMO_IDENTITIES = ["Ali Khan", "Sara Ahmed", "Bilal Raza"]
DEMO_DOCS = ["contract_2026.pdf", "nda_signed.pdf", "invoice_042.pdf"]


def generate_demo(n: int = 40):
    """Generate n random audit events spread over the last 3 days."""
    init_db()

    events = []

    # Every event: (event_type, source_module, outcomes)
    templates = [
        (EventType.LOGIN, SourceModule.PROJECT_7_AUTH, [Outcome.SUCCESS, Outcome.FAILURE]),
        (EventType.LOGOUT, SourceModule.PROJECT_7_AUTH, [Outcome.SUCCESS]),
        (EventType.BIOMETRIC_VERIFICATION, SourceModule.PROJECT_4_VERIFICATION,
         [Outcome.MATCH, Outcome.NO_MATCH, Outcome.UNABLE]),
        (EventType.FINGERPRINT_VERIFICATION, SourceModule.PROJECT_4_VERIFICATION,
         [Outcome.MATCH, Outcome.NO_MATCH]),
        (EventType.PDF_UPLOADED, SourceModule.PROJECT_5_SIGNING, [Outcome.SUCCESS]),
        (EventType.DOCUMENT_SIGNED, SourceModule.PROJECT_5_SIGNING, [Outcome.SUCCESS]),
        (EventType.SIGNATURE_VERIFIED, SourceModule.PROJECT_6_VERIFY,
         [Outcome.SUCCESS, Outcome.FAILURE]),
        (EventType.IDENTITY_ENROLLED, SourceModule.PROJECT_4_VERIFICATION, [Outcome.SUCCESS]),
        (EventType.ADMIN_CHANGE, SourceModule.PROJECT_8_AUDIT, [Outcome.SUCCESS]),
        (EventType.ACCESS_DENIED, SourceModule.PROJECT_7_AUTH, [Outcome.DENIED]),
    ]

    # Weight the templates so some are more common
    weights = [12, 10, 15, 6, 4, 5, 6, 2, 2, 2]

    now = datetime.utcnow()

    for i in range(n):
        template = random.choices(templates, weights=weights, k=1)[0]
        event_type, source_module, outcomes = template
        outcome = random.choice(outcomes)
        actor = random.choice(DEMO_ACTORS)

        # Random timestamp in last 3 days
        offset = timedelta(
            days=random.randint(0, 2),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        ts = now - offset

        target = None
        metadata = {}

        if "verification" in event_type:
            target = random.choice(DEMO_IDENTITIES)
            metadata = {
                "score": round(random.uniform(0.2, 0.95), 3),
                "modality": "face" if "biometric" in event_type else "fingerprint",
            }
        elif "document" in event_type or "pdf" in event_type or "signature" in event_type:
            target = random.choice(DEMO_DOCS)
        elif event_type == EventType.LOGIN and outcome == Outcome.FAILURE:
            metadata = {"reason": random.choice(["bad_password", "user_not_found"])}

        # Write with custom timestamp by using log() then updating
        row_id = log(event_type, outcome, source_module, actor, target, metadata)

        # Override timestamp (log() uses utcnow)
        from database import get_session, AuditLog
        session = get_session()
        try:
            entry = session.query(AuditLog).get(row_id)
            entry.timestamp = ts
            session.commit()
        finally:
            session.close()

        events.append(row_id)

    return len(events)


if __name__ == "__main__":
    print("Generating demo audit data...")
    clear_all()
    n = generate_demo(40)
    print(f"✅ Generated {n} demo events.")