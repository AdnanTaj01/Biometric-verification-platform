# 🎭 Project 09: Liveness Detection

A Streamlit module demonstrating anti-spoofing liveness detection via **challenge-response** — blink, head movement, and texture analysis.

**SRS Coverage:** FR-05

---

## 📋 Requirement Coverage

| Requirement | Description | Status |
|---|---|---|
| **FR-05** | Liveness detection to detect printed-photo / replayed-video spoofing | ✅ |

**FR-05 note:** *"Liveness result aur face matching result separate show kiye jayenge."* — This module reports liveness independently. Identity verification is handled in Project 01.

---

## 🎯 How It Works

Three-signal challenge-response:

1. **Blink detection** — Eye Aspect Ratio (EAR) drops when eyes close
2. **Head movement** — nose tip displacement between photos
3. **Texture analysis** — Laplacian variance + FFT peak ratio

### Challenge-response flow
