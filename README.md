# 🔐 Biometric Verification & Secure E-Signature Platform

> A modular portfolio demonstrating **AI/ML**, **computer vision**, **biometric hardware integration**, **liveness detection**, and **cryptographic document signing** — built as a cohesive engineering project.

[![Tests](https://github.com/AdnanTaj01/Biometric-verification-platform/actions/workflows/tests.yml/badge.svg)](https://github.com/AdnanTaj01/Biometric-verification-platform/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![InsightFace](https://img.shields.io/badge/InsightFace-0.7.3-blue)](https://github.com/deepinsight/insightface)
[![MediaPipe](https://img.shields.io/badge/MediaPipe-0.10.14-0097A7?logo=google&logoColor=white)](https://mediapipe.dev/)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![pyHanko](https://img.shields.io/badge/pyHanko-0.25.3-005571)](https://github.com/MatthiasValvekens/pyHanko)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 📖 Overview

This repository is a **portfolio implementation** of a Software Requirements Specification (SRS) for a **Biometric Identity Verification & Secure E-Signature Platform**.

Instead of building one monolithic application, the SRS requirements are split into **9 standalone modules** — each focused, testable, and independently demonstrable. This structure makes the codebase easier to review, and each module can be understood in isolation.

**Why this structure?**
- ✅ Each module maps to specific SRS requirements (FR-01 to FR-14)
- ✅ Reviewers can inspect a single feature without loading the whole platform
- ✅ Modules are reusable — each is a self-contained Streamlit app
- ✅ Demonstrates clean separation of concerns
- ✅ Each module can be replaced or upgraded independently

---

## 📋 Project Modules

| # | Module | SRS Coverage | Core Tech | Status |
|---|---|---|---|---|
| **01** | [**Face Capture & Recognition**](./01_face_capture_recognition) | FR-02, FR-03, FR-04 | Streamlit, InsightFace, OpenCV, sklearn | ✅ Complete |
| **02** | [**Fingerprint Scanner Integration**](./02_fingerprint_scanner) | FR-06, FR-07 | Streamlit, Mock SDK (vendor-ready adapter) | ✅ Complete |
| **03** | [**Quality Indicators Deep-Dive**](./03_quality_indicators) | FR-03 | Streamlit, OpenCV, InsightFace | ✅ Complete |
| **04** | [**Biometric Verification Engine**](./04_biometric_verification) | FR-04, FR-07 | Streamlit, SQLAlchemy, InsightFace | ✅ Complete |
| **05** | [**PDF Digital Signature**](./05_pdf_signing) | FR-09, FR-10, FR-11 | Streamlit, pyHanko, cryptography | ✅ Complete |
| **06** | [**Signature Verification**](./06_signature_verification) | FR-12 | Streamlit, pyHanko, cryptography | ✅ Complete |
| **07** | [**Authentication & RBAC**](./07_auth_rbac) | FR-01, FR-14 | Streamlit, bcrypt, SQLAlchemy | ✅ Complete |
| **08** | [**Audit Logs & Admin Dashboard**](./08_audit_logs) | FR-13, FR-14 | Streamlit, SQLAlchemy, pandas | ✅ Complete |
| **09** | [**Liveness Detection**](./09_liveness_detection) | FR-05 | Streamlit, MediaPipe, OpenCV | ✅ Complete |

**Status legend:** ✅ Complete · 🚧 In Progress · 📝 Planned

---

## 🎯 Skills Demonstrated

This project showcases a broad range of engineering skills across AI/ML, security, and full-stack development.

### 🧠 AI / Machine Learning
- **Face detection & recognition** using InsightFace `buffalo_l` (RetinaFace + ArcFace)
- **512-dimensional embedding generation** and vector similarity search
- **Cosine similarity matching** with `sklearn.metrics.pairwise` — batch-optimized
- **Quality assurance** for biometric capture (brightness, contrast, sharpness, face size, centering, orientation)
- **Liveness detection** via challenge-response (blink + head movement + texture analysis)

### 📷 Computer Vision
- **Live webcam streaming** via Streamlit `camera_input()`
- **Face bounding box detection** and visualization
- **468-point face mesh** via MediaPipe
- **Eye Aspect Ratio (EAR)** and head pose estimation
- **Laplacian variance + FFT peak analysis** for print/screen detection
- **Real-time quality feedback** with red/yellow/green indicators

### 🔐 Security & Cryptography
- **Password hashing** with bcrypt (cost factor 12)
- **Role-Based Access Control (RBAC)** with 4 distinct roles and server-side enforcement
- **Cryptographic PDF signing** using pyHanko with X.509 certificates
- **PDF signature verification** — integrity, cryptographic validity, and trust chain
- **Automatic sensitive-metadata redaction** in audit logs
- **Private key isolation** — signing keys never leave the backend
- **Anti-spoofing** for biometric verification

### 🖥️ Full-Stack Engineering
- **Streamlit** for rapid, production-quality UIs
- **SQLAlchemy 2.0** ORM with SQLite
- **Modular architecture** — UI separated from business logic across 9 projects
- **Adapter pattern** for hardware abstraction (fingerprint SDK)
- **Automated testing** with pytest (63 tests across all modules)
- **CI/CD with GitHub Actions** — per-module parallel test jobs
- **Environment isolation** — resolving real-world dependency conflicts

### 🎨 UX & Accessibility
- **Red/yellow/green indicators** paired with text labels, icons, and numeric scores (satisfies NFR-5.4)
- **Clear, honest disclaimers** (e.g., "green = capture readiness, not identity verification")
- **Actionable recommendations** on failed quality checks
- **Per-step validation** with helpful error messages

---

## 🏗️ System Architecture

<img width="530" height="466" alt="System architecture diagram" src="https://github.com/user-attachments/assets/c8880953-05f3-4c40-88e5-5ce7b7ca5b5d" />

Each module is a **Streamlit app** that runs independently. The platform is designed so modules can be composed into a larger application if needed.

---

## 🚀 Quick Start

Each module is **self-contained**. To run any module:

### General Workflow

```bash
# 1. Navigate to a module
cd 01_face_capture_recognition

# 2. Create virtual environment
python -m venv venv

# 3. Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the Streamlit app
streamlit run app.py