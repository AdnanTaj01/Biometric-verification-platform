# 📜 Project 8: Audit Logs & Admin Dashboard

A centralized audit logging system and dashboard that consolidates events from all 7 previous modules.

**SRS Coverage:** FR-13, FR-14

---

## 📋 Requirement Coverage

| Requirement | Description | Status |
|---|---|---|
| **FR-13** | Audit logs — record important events across the platform | ✅ |
| **FR-14** | Admin dashboard — metrics and recent events | ✅ |

---

## 🎯 What This Project Demonstrates

Projects 1–7 each generate events (logins, verifications, signings, admin changes). Project 8 provides:

- A **single schema** for all audit events (SQLAlchemy model)
- A **write API** (`audit.log()`) any module can call
- A **read API** (`audit.query()`) with filters
- A **stats API** (`audit.stats()`) for the dashboard
- A **Streamlit dashboard** with metrics, filterable log, and CSV export
- **Automatic redaction** of sensitive metadata (passwords, keys, biometrics)

---

## 🔒 Privacy & Safety

FR-13 explicitly requires:
> *"Audit logs mein passwords, private keys aur unnecessary raw biometric data store nahi kiya jayega."*

This project enforces it at the API level:

```python
_BLOCKED_KEYS = {
    "password", "password_hash", "passwd", "pwd",
    "private_key", "secret", "token", "api_key",
    "raw_image", "raw_biometric", "embedding",
    "fingerprint_image", "fingerprint_template", "face_embedding",
}