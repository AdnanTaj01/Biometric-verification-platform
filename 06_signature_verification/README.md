# 🔍 Project 6: PDF Signature Verification

A fully self-contained Streamlit module for verifying cryptographic signatures in PDF documents — using pyHanko.

**SRS Coverage:** FR-12

---

## 📋 Requirement Coverage

| FR-12 Category | Detected by | Demo fixture |
|---|---|---|
| Signature cryptographically valid | `intact=True, valid=True, trusted=True` | `signed.pdf` + trust |
| Signature invalid | `valid=False` | — |
| Document modified after signing | `intact=False` | `tampered.pdf` |
| Certificate expired or untrusted | `trusted=False` | `signed.pdf` (no trust) |
| Verification inconclusive | Parse error | Malformed input |

---

## 🎯 What This Project Demonstrates

Unlike Project 5 (which signs PDFs), Project 6 **only verifies**.

- Generates its own test certificate (`certs.py`)
- Generates 3 test PDFs (`test_fixtures.py`): unsigned / signed / tampered
- Verifies any uploaded PDF with embedded signatures
- Reports per-signature: **intact**, **valid**, **trusted**
- Maps results to the 5 FR-12 categories

**100% independent** — no imports from Project 5.

---


---

## ⚙️ Setup

```bash
cd 06_signature_verification
..\01_face_capture_recognition\venv\Scripts\Activate.ps1
pip install -r requirements.txt
