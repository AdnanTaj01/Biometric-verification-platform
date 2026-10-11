# 🔐 Biometric Verification & Secure E-Signature Platform

> A modular portfolio demonstrating **AI/ML**, **computer vision**, **biometric hardware integration**, and **cryptographic document signing** — built as a cohesive engineering project.

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.32+-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![InsightFace](https://img.shields.io/badge/InsightFace-0.7.3-blue)](https://github.com/deepinsight/insightface)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.4+-F7931E?logo=scikitlearn&logoColor=white)](https://scikit-learn.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 📖 Overview

This repository is a **portfolio implementation** of a Software Requirements Specification (SRS) for a **Biometric Identity Verification & Secure E-Signature Platform**.

Instead of building one monolithic application, the SRS requirements are split into **8 standalone modules** — each focused, testable, and independently demonstrable. This structure makes the codebase easier to review, and each module can be understood in isolation.

**Why this structure?**
- ✅ Each module maps to specific SRS requirements (FR-01 to FR-14)
- ✅ Reviewers can inspect a single feature without loading the whole platform
- ✅ Modules are reusable — each is a self-contained Streamlit app
- ✅ Demonstrates clean separation of concerns

---

## 📋 Project Modules

| # | Module | SRS Coverage | Core Tech | Status |
|---|---|---|---|---|
| **01** | [**Face Capture & Recognition**](./01_face_capture_recognition) | FR-02, FR-03, FR-04, FR-05 | Streamlit, InsightFace, OpenCV, sklearn | ✅ Complete |
| **02** | [**Fingerprint Scanner Integration**](./02_fingerprint_scanner) | FR-06, FR-07 | Streamlit, Mock SDK | 🚧 In Progress |
| **03** | [**Quality Indicators Deep-Dive**](./03_quality_indicators) | FR-03 | Streamlit, OpenCV | 🚧 Planned |
| **04** | [**Biometric Verification Engine**](./04_biometric_verification) | FR-04, FR-07 | Streamlit, InsightFace, SQLAlchemy | 🚧 Planned |
| **05** | [**PDF Digital Signature**](./05_pdf_signing) | FR-09, FR-10, FR-11 | Streamlit, pyHanko, cryptography | 🚧 Planned |
| **06** | [**Signature Verification**](./06_signature_verification) | FR-12 | Streamlit, pyHanko | 🚧 Planned |
| **07** | [**Authentication & RBAC**](./07_auth_rbac) | FR-01, FR-14 | Streamlit, bcrypt, JWT | 🚧 Planned |
| **08** | [**Audit Logs & Verification History**](./08_audit_logs) | FR-13 | Streamlit, SQLAlchemy | 🚧 Planned |

**Status legend:** ✅ Complete · 🚧 In Progress · 📝 Planned

---

## 🎯 Skills Demonstrated

This project is designed to showcase a broad range of engineering skills across AI/ML, security, and full-stack development.

### 🧠 AI / Machine Learning
- **Face detection & recognition** using InsightFace `buffalo_l` (RetinaFace + ArcFace)
- **512-dimensional embedding generation** and vector similarity search
- **Cosine similarity matching** with `sklearn.metrics.pairwise` — batch-optimized
- **Quality assurance** for biometric capture (brightness, sharpness, face size)

### 📷 Computer Vision
- **Live webcam streaming** via Streamlit `camera_input()`
- **Face bounding box detection** and visualization
- **Laplacian variance** for blur detection
- **Real-time quality feedback** with red/green indicators

### 🔐 Security & Cryptography
- **Password hashing** with bcrypt
- **JWT-based session management**
- **Role-Based Access Control (RBAC)** with 4 distinct roles
- **Cryptographic PDF signing** using pyHanko
- **X.509 certificate handling** and signature verification
- **Audit logging** with safe metadata (no raw biometrics stored)

### 🖥️ Full-Stack Engineering
- **Streamlit** for rapid, production-quality UIs
- **SQLAlchemy** ORM with SQLite/PostgreSQL
- **Modular architecture** — UI separated from business logic
- **Automated testing** with pytest
- **Docker** for reproducible environments

### 🎨 UX & Accessibility
- **Red/green indicators** paired with text labels (not color-dependent)
- **Clear, honest disclaimers** (e.g., "green = readiness, not verification")
- **Configurable thresholds** for different environments

---

## 🏗️ System Architecture
<img width="530" height="466" alt="image" src="https://github.com/user-attachments/assets/c8880953-05f3-4c40-88e5-5ce7b7ca5b5d" />


Each module is a **Streamlit app** that runs independently. The platform is designed so that modules can be composed into a larger application if needed.

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


