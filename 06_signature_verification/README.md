# 🔍 Project 6: PDF Signature Verification Results

## Landing_gage
<img width="1326" height="589" alt="Landing_gage" src="https://github.com/user-attachments/assets/76fd2dcb-4023-4cb7-aee8-fef30036220a" />

## Test_with_pre_generated_fixtures_signed
<img width="1968" height="927" alt="Test_with_pre_generated_fixtures_signed_page_1" src="https://github.com/user-attachments/assets/40c6c2ca-dde4-4160-a4f0-d4fad1a501b8" />

## Test_with_pre_generated_fixtures_unsigned
<img width="1323" height="606" alt="Test_with_pre_generated_fixtures_unsigned" src="https://github.com/user-attachments/assets/b5e8a863-7170-4361-a1d9-9b1149d4d93a" />


## Test_with_pre_generated_fixtures_tampered
<img width="1353" height="598" alt="Test_with_pre_generated_fixtures_tampered" src="https://github.com/user-attachments/assets/133c5c50-5f9c-4e73-9d81-9ab6916dc1ea" />

## Upload_pdf_to_verify_signature
<img width="1299" height="542" alt="Upload_pdf_to_verify_signature" src="https://github.com/user-attachments/assets/f4b3824d-6fd1-4ac3-a3c3-8beeeed3719a" />

## Upload_signed-pdf
<img width="1309" height="607" alt="Upload_signed-pdf" src="https://github.com/user-attachments/assets/3cfb3e90-2a23-4f5f-b68b-d6c47560ce2f" />

## Upload_unsigned-pdf
<img width="1231" height="512" alt="Upload_unsigned-pdf" src="https://github.com/user-attachments/assets/42176b24-953e-419d-94f0-2342cf9bec80" />

## Upload_tampered-pdf
<img width="1285" height="574" alt="Upload_tampered-pdf" src="https://github.com/user-attachments/assets/79662e6e-b9f5-4dc6-866e-4ec506dc53a4" />

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


## ⚙️ Setup

```bash
cd 06_signature_verification
..\01_face_capture_recognition\venv\Scripts\Activate.ps1
pip install -r requirements.txt

## ⚠️ Known Limitations

- **No timestamp authority (TSA) verification.** Signatures carry local time only.
- **No revocation checking (CRL/OCSP).** `allow_fetching=False` blocks network access.
- **Trust root is user-provided.** Production uses the OS trust store.
- **No long-term validation (LTV).** For long-term validity, use PAdES-LTV.
- **Only checks embedded signatures.** Detached signatures are out of scope.

## 📸 Screenshots

### 06 Upload

![06 Upload](../docs/screenshots/06_signature_verification/06_upload.png)

### 06 Fixtures

![06 Fixtures](../docs/screenshots/06_signature_verification/06_fixtures.png)

### 06 Signed Valid

![06 Signed Valid](../docs/screenshots/06_signature_verification/06_signed_valid.png)

