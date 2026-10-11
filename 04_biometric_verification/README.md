# 🎯 Project 4: Biometric Verification Engine

A unified biometric verification module combining **face recognition** (InsightFace) and **fingerprint verification** (Mock SDK) — with SQLite persistence for identities, references, and verification history.

---

## 📋 Requirement Coverage

| Requirement | Description | Status |
|---|---|---|
| **FR-02** | Test Identity Registration (database-backed) | ✅ |
| **FR-04** | Face Recognition | ✅ |
| **FR-07** | Fingerprint Verification | ✅ |
| **FR-13** | Verification Records (partial — full audit in Project 8) | ✅ Partial |

---

## 🎯 What This Project Demonstrates

This is the **integration layer** — it takes face recognition (Project 1) and fingerprint verification (Project 2), and combines them into a **single unified verification engine** with proper database persistence.

**Key additions over Projects 1 & 2:**
- SQLite database with 3 tables (identities, biometric_references, verification_records)
- Unified verification engine that handles both modalities
- Verification history with filters and CSV export
- Live stats dashboard
- Multi-modal enrollment per identity

---

## 🗄️ Database Schema

Aligned with the SRS Database Design section:

### `identities`
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment |
| display_name | String unique | Name |
| consent_status | Boolean | Consent flag |
| enrollment_status | String | active / inactive |
| created_at | DateTime | Timestamp |

### `biometric_references`
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment |
| identity_id | FK | Reference to identities |
| modality | String | face / fingerprint |
| protected_reference | Binary | Pickled embedding/template |
| model_or_sdk_version | String | Version tag |
| created_at | DateTime | Timestamp |

### `verification_records`
| Column | Type | Description |
|---|---|---|
| id | Integer PK | Auto-increment |
| identity_id | FK nullable | Null for 1:N matching |
| modality | String | face / fingerprint |
| verification_type | String | 1:N or 1:1 |
| result | String | Match / No Match / Unable to Verify |
| score | Float | Similarity score |
| source | String | face_engine / mock_sdk |
| created_at | DateTime | Timestamp |

---

## 🏗️ Architecture
![alt text](image.png)

---

## ⚙️ Setup

```bash
cd 04_biometric_verification

# Reuse Project 1's venv
..\01_face_capture_recognition\venv\Scripts\Activate.ps1

# Add SQLAlchemy
pip install sqlalchemy==2.0.29