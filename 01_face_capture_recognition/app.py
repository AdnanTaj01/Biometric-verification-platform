"""
Streamlit app: Live Face Capture + Recognition

Covers SRS requirements:
- FR-03: Live face capture with red/green quality indicators
- FR-04: Face recognition against registered identities
- FR-05: (Optional) Liveness detection — not implemented in this version
"""
import streamlit as st
import cv2
import numpy as np
from PIL import Image
import io

from face_engine import (
    detect_faces,
    get_largest_face,
    match_face,
    load_embeddings,
    bbox_to_xyxy,
)
from quality_check import run_all_quality_checks, all_passed


# ---------- Page config ----------
st.set_page_config(
    page_title="Face Capture & Recognition",
    page_icon="🧑",
    layout="wide",
)

st.title("🧑 Live Face Capture & Recognition")
st.caption("Project 1 — Biometric Identity Verification Portfolio")


# ---------- Sidebar ----------
st.sidebar.header("⚙️ Settings")
threshold = st.sidebar.slider(
    "Match Threshold (cosine similarity)",
    min_value=0.2,
    max_value=0.8,
    value=0.4,
    step=0.05,
    help="Higher = stricter matching",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Registered Identities")
registered = load_embeddings()
if registered:
    for name in registered.keys():
        st.sidebar.write(f"• {name}")
else:
    st.sidebar.warning("No identities registered.\nRun enroll.py first.")


# ---------- Helper: draw indicator badge ----------
def render_check(name: str, passed: bool, message: str):
    """Render a red/green indicator with text label (not color-only)."""
    if passed:
        st.markdown(
            f"<div style='padding:8px;border-radius:6px;background:#d4edda;"
            f"border-left:5px solid #28a745;margin-bottom:6px;'>"
            f"✅ <b>{name}</b>: {message}</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='padding:8px;border-radius:6px;background:#f8d7da;"
            f"border-left:5px solid #dc3545;margin-bottom:6px;'>"
            f"❌ <b>{name}</b>: {message}</div>",
            unsafe_allow_html=True,
        )


# ---------- Main layout ----------
col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("📷 Live Capture")
    camera_image = st.camera_input("Position your face in the frame")

with col_right:
    st.subheader("📊 Quality & Result")

# ---------- Process captured image ----------
if camera_image is not None:
    # Convert to OpenCV format
    image_bytes = camera_image.getvalue()
    pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    image = cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    # Detect faces
    with st.spinner("Detecting face..."):
        faces = detect_faces(image)
        face = get_largest_face(faces)

    face_box = None
    if face is not None:
        face_box = bbox_to_xyxy(face.bbox)

    # Run quality checks
    with st.spinner("Running quality checks..."):
        checks = run_all_quality_checks(image, face_box)

    # Show quality checks in right column
    with col_right:
        st.markdown("### 🔍 Quality Checks")
        for c in checks:
            render_check(c["name"], c["passed"], c["message"])

        quality_ok = all_passed(checks)

        # Draw face box on image for visual feedback
        if face_box is not None:
            display_image = image.copy()
            x1, y1, x2, y2 = face_box
            color = (0, 255, 0) if quality_ok else (0, 0, 255)
            cv2.rectangle(display_image, (x1, y1), (x2, y2), color, 2)
            st.image(
                cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB),
                caption="Detected face",
                use_container_width=True,
            )

        st.markdown("---")

        # Overall capture readiness
        if quality_ok:
            st.success("🟢 **Ready to Capture** — All quality checks passed")
        else:
            st.error("🔴 **Not Ready** — Fix the issues above")

        st.caption(
            "⚠️ Green indicator means capture readiness only, "
            "NOT identity verification."
        )

        st.markdown("---")

        # ---------- Recognition ----------
        st.markdown("### 🎯 Face Recognition")

        if face is None:
            st.warning("No face detected. Cannot run recognition.")
        elif not quality_ok:
            st.warning("Quality checks failed. Fix them before recognition.")
        elif not registered:
            st.warning("No registered identities. Run enroll.py to register faces.")
        else:
            with st.spinner("Matching against registered identities..."):
                match_result = match_face(
                    face.embedding, registered, threshold=threshold
                )

            result = match_result["result"]

            if result == "Match":
                st.success(
                    f"✅ **Match Found**: {match_result['best_match']}\n\n"
                    f"Confidence: `{match_result['best_score']:.4f}` "
                    f"(threshold: {threshold})"
                )
            elif result == "No Match":
                st.error(
                    f"❌ **No Match**\n\n"
                    f"Best candidate: `{match_result['best_match']}` "
                    f"with score `{match_result['best_score']:.4f}` "
                    f"(below threshold {threshold})"
                )
            else:
                st.warning(f"⚠️ {result}: {match_result.get('reason', '')}")

            # Show all scores
            with st.expander("📊 All similarity scores"):
                for name, score in sorted(
                    match_result["all_scores"].items(), key=lambda x: -x[1]
                ):
                    st.write(f"• **{name}**: `{score:.4f}`")

else:
    with col_right:
        st.info("👈 Capture a photo from the camera to begin.")