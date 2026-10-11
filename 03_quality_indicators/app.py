"""
Streamlit app: Quality Indicators Deep-Dive.

Covers FR-03: comprehensive quality feedback with red/yellow/green indicators
and text labels (NFR-5.4 accessibility).
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io

from insightface.app import FaceAnalysis
from quality_analyzer import run_full_analysis


# ---------- Page config ----------
st.set_page_config(
    page_title="Quality Indicators",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Quality Indicators Deep-Dive")
st.caption("Project 3 — Biometric Identity Verification Portfolio")


# ---------- Load face detector (cached) ----------
@st.cache_resource
def load_detector():
    app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
    app.prepare(ctx_id=0, det_size=(640, 640))
    return app


detector = load_detector()


# ---------- Sidebar ----------
st.sidebar.header("ℹ️ About")
st.sidebar.markdown(
    """
    This module performs **6 quality checks** on captured frames:

    1. **Brightness** — mean gray value
    2. **Contrast** — std deviation
    3. **Sharpness** — Laplacian variance
    4. **Face Size** — bbox/frame ratio
    5. **Centering** — offset from frame center
    6. **Orientation** — head roll angle

    Each check returns a **pass / warning / fail** status with a **text label**
    (not color-only, per accessibility guidelines).
    """
)

st.sidebar.markdown("---")
st.sidebar.subheader("🎨 Status Legend")
st.sidebar.markdown(
    """
    - ✅ **Green** — Pass (quality sufficient)
    - ⚠️ **Yellow** — Warning (usable but not ideal)
    - ❌ **Red** — Fail (fix before capture)

    ⚠️ **Note:** Green means **capture readiness only**, not identity verification.
    """
)


# ---------- Indicator renderer ----------
def render_indicator(result):
    """
    Render a quality check result as a color-coded card with
    icon + status word + message + recommendation.
    """
    colors = {
        "pass":    ("#d4edda", "#28a745", "✅", "PASS"),
        "warning": ("#fff3cd", "#ffc107", "⚠️", "WARN"),
        "fail":    ("#f8d7da", "#dc3545", "❌", "FAIL"),
    }
    bg, border, icon, label = colors[result.status]

    # Score bar
    bar_width = int(result.score)
    bar_color = border

    st.markdown(
        f"""
        <div style='padding:10px 14px;border-radius:8px;background:{bg};
                    border-left:5px solid {border};margin-bottom:8px;'>
            <div style='display:flex;justify-content:space-between;align-items:center;'>
                <div>
                    <span style='font-size:16px;'>{icon}</span>
                    <b style='margin-left:6px;'>{result.name}</b>
                    <span style='color:#666;font-size:12px;margin-left:8px;'>{label}</span>
                </div>
                <div style='font-weight:bold;color:{border};'>{result.score:.0f}/100</div>
            </div>
            <div style='color:#333;font-size:13px;margin-top:4px;'>{result.message}</div>
            {f"<div style='color:#856404;font-size:12px;margin-top:4px;'>💡 {result.recommendation}</div>" if result.recommendation else ""}
            <div style='margin-top:6px;background:#e9ecef;border-radius:4px;height:6px;overflow:hidden;'>
                <div style='width:{bar_width}%;height:100%;background:{bar_color};'></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Layout ----------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📷 Live Capture")
    camera_image = st.camera_input("Position your face in the frame")

with col_right:
    st.subheader("📊 Quality Dashboard")

# ---------- Process captured frame ----------
if camera_image is not None:
    # Convert to OpenCV BGR
    pil_image = Image.open(io.BytesIO(camera_image.getvalue())).convert("RGB")
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # Detect faces
    with st.spinner("Analyzing..."):
        faces = detector.get(image)
        face = None
        if faces:
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

        analysis = run_full_analysis(image, face)

    # ---------- Show preview with face box ----------
    with col_left:
        if analysis["face_box"]:
            x1, y1, x2, y2 = analysis["face_box"]
            preview = image.copy()
            color = (0, 200, 0) if analysis["overall_status"] == "pass" else \
                    (0, 200, 255) if analysis["overall_status"] == "warning" else (0, 0, 255)
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, 3)
            st.image(
                cv2.cvtColor(preview, cv2.COLOR_BGR2RGB),
                caption="Detected face",
                use_container_width=True,
            )
        else:
            st.image(
                cv2.cvtColor(image, cv2.COLOR_BGR2RGB),
                caption="No face detected",
                use_container_width=True,
            )

    # ---------- Overall score ----------
    with col_right:
        overall = analysis["overall_score"]
        status = analysis["overall_status"]

        status_meta = {
            "pass":    ("🟢", "READY", "#28a745", "#d4edda"),
            "warning": ("🟡", "WARNING", "#856404", "#fff3cd"),
            "fail":    ("🔴", "NOT READY", "#dc3545", "#f8d7da"),
        }
        icon, label, txt_color, bg_color = status_meta[status]

        st.markdown(
            f"""
            <div style='padding:20px;border-radius:10px;background:{bg_color};
                        border:2px solid {txt_color};text-align:center;margin-bottom:16px;'>
                <div style='font-size:48px;line-height:1;'>{icon}</div>
                <div style='font-size:26px;font-weight:bold;color:{txt_color};margin-top:6px;'>
                    {overall:.0f} / 100
                </div>
                <div style='font-size:16px;font-weight:bold;color:{txt_color};margin-top:2px;'>
                    {label}
                </div>
                <div style='font-size:12px;color:#666;margin-top:8px;'>
                    Overall quality score (weighted average)
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🔍 Individual Checks")
        for r in analysis["results"]:
            render_indicator(r)

        st.caption(
            "⚠️ Green means **capture readiness only**, not identity verification."
        )

    # ---------- Explanation expander ----------
    with st.expander("📖 How this analysis works"):
        st.markdown(
            """
            ### Metrics & Rationale

            | Check | Metric | Ideal Range | Why It Matters |
            |---|---|---|---|
            | Brightness | Mean gray value | 90–180 | Too dark hides features; too bright blows them out |
            | Contrast | Std deviation | > 55 | Low contrast = flat, feature-poor image |
            | Sharpness | Laplacian variance | > 120 | Blur destroys high-frequency facial detail |
            | Face Size | bbox / frame area | 0.15–0.50 | Face must be prominent for reliable matching |
            | Centering | Offset from center | < 0.10 | Centers the region of interest, avoids edge cropping |
            | Orientation | Roll angle from eyes | < 10° | Tilted face degrades embedding quality |

            ### Overall Score

            Each check produces a **0–100 score**. The overall score is a
            **weighted average** with emphasis on face size and sharpness
            (the two biggest impact factors for downstream recognition).

            ### Status Thresholds

            - **Pass (green):** score ≥ 80
            - **Warning (yellow):** 55 ≤ score < 80
            - **Fail (red):** score < 55

            ### Accessibility Note

            Every indicator includes:
            - A **color** (green/yellow/red)
            - An **icon** (✅/⚠️/❌)
            - A **text label** (PASS/WARN/FAIL)
            - A **numeric score** (0–100)
            - A **text message** and **recommendation**

            This satisfies **NFR-5.4** — the interface does not depend on color alone.
            """
        )

else:
    with col_right:
        st.info("👈 Capture a photo from the camera to see the quality analysis.")