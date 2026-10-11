# 🔍 Project 3: Quality Indicators Deep-Dive

A dedicated Streamlit module that performs **comprehensive image quality analysis** on captured frames — with red/yellow/green indicators, numeric scores, and actionable recommendations.

**SRS Coverage:** FR-03 (detailed) + NFR-5.4 (accessibility)

---

## 🎯 What This Project Demonstrates

This is a **deep-dive into the quality indicator system** first introduced in Project 1. Where Project 1 provides basic checks (brightness, sharpness, size), Project 3 adds:

- **6 quality metrics** (vs 3 in Project 1)
- **Three-tier status system** (pass / warning / fail — not just binary)
- **Numeric score per metric** (0–100)
- **Weighted overall score**
- **Actionable recommendations** per failed check
- **Accessibility-first design** — every indicator has icon + text + number + color

---

## 📋 Quality Checks

| # | Check | Metric | Ideal Range | Weight |
|---|---|---|---|---|
| 1 | Brightness | Mean gray value | 90–180 | 1.0 |
| 2 | Contrast | Std deviation | > 55 | 0.8 |
| 3 | Sharpness | Laplacian variance | > 120 | 1.2 |
| 4 | Face Size | bbox / frame ratio | 0.15–0.50 | 1.3 |
| 5 | Centering | Offset from center | < 0.10 | 0.7 |
| 6 | Orientation | Roll angle from eyes | < 10° | 0.8 |

**Overall score:** Weighted average of all six checks.

**Overall status thresholds:**
- ✅ **Pass:** score ≥ 80
- ⚠️ **Warning:** 55 ≤ score < 80
- ❌ **Fail:** score < 55

---

## ♿ Accessibility Design (NFR-5.4)

Every indicator includes **five redundant signals** so the interface is usable regardless of color perception:

1. **Color** — green / yellow / red
2. **Icon** — ✅ / ⚠️ / ❌
3. **Text label** — PASS / WARN / FAIL
4. **Numeric score** — 0–100
5. **Progress bar** — visual magnitude

Plus a **recommendation text** for any warning or fail state.

---

## ⚙️ Setup

```bash
cd 03_quality_indicators

# Reuse Project 1's venv (recommended)
..\01_face_capture_recognition\venv\Scripts\Activate.ps1

# Or create a fresh one
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt