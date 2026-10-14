"""
Streamlit app: Liveness Detection (FR-05).

Challenge-response flow with PER-STEP VALIDATION:
    Step 1/3 — eyes OPEN      → validate EAR > 0.20
    Step 2/3 — eyes CLOSED    → validate EAR < 0.18
    Step 3/3 — head TURNED    → validate nose offset > 15% of face width

Each capture is validated immediately. Invalid photos are rejected with
a specific reason, and the user must retake.

Note: Uses Streamlit 1.32 API (use_column_width for st.image).
"""
import io
import numpy as np
import cv2
import streamlit as st
from PIL import Image

from liveness_engine import (
    evaluate_liveness,
    validate_eyes_open,
    validate_eyes_closed,
    validate_head_turned,
    MEDIAPIPE_AVAILABLE,
)


st.set_page_config(
    page_title="Liveness Detection",
    page_icon="🎭",
    layout="wide",
)

st.title("🎭 Liveness Detection")
st.caption("Project 9 — FR-05: anti-spoofing via challenge-response with live validation")


if not MEDIAPIPE_AVAILABLE:
    st.error("`mediapipe` is not installed. Run: `pip install mediapipe==0.10.14`")
    st.stop()


def render_check(label, passed, message=""):
    bg = "#d4edda" if passed else "#f8d7da"
    border = "#28a745" if passed else "#dc3545"
    icon = "✅" if passed else "❌"
    st.markdown(
        f"<div style='padding:10px;border-radius:6px;background:{bg};"
        f"border-left:5px solid {border};margin-bottom:6px;'>"
        f"<b>{icon} {label}</b>"
        + (f"<br><span style='font-size:12px;color:#666;'>{message}</span>" if message else "")
        + "</div>",
        unsafe_allow_html=True,
    )


def to_bgr(camera_image):
    pil = Image.open(io.BytesIO(camera_image.getvalue())).convert("RGB")
    return cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)


# ---------- Session state ----------
for key in ("photo_open", "photo_closed", "photo_turned"):
    if key not in st.session_state:
        st.session_state[key] = None

if "last_validation" not in st.session_state:
    st.session_state.last_validation = {}


# ---------- Sidebar ----------
st.sidebar.header("ℹ️ How it works")

st.sidebar.markdown(
    """
    **Challenge-response liveness** asks you to perform 3 actions:

    1. **Eyes OPEN** — must be detected before proceeding
    2. **Eyes CLOSED** — the app checks that your eyes really closed
    3. **Head TURNED** — the app checks that your head really moved

    Each step is **validated at capture time**. If the action wasn't
    performed, the photo is rejected and you must retake.
    """
)

if st.sidebar.button("🔄 Reset all photos", use_container_width=True):
    for key in ("photo_open", "photo_closed", "photo_turned"):
        st.session_state[key] = None
    st.session_state.last_validation = {}
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "⚠️ Liveness result is reported **separately** from identity verification (FR-05)."
)


# ---------- Tabs ----------
tab1, tab2 = st.tabs(["🎬 Guided capture", "📊 Result"])


# ==================================================================
# TAB 1: Guided capture
# ==================================================================
with tab1:
    st.subheader("Follow the 3 steps — each is validated")

    # =================== STEP 1 ===================
    st.markdown("### Step 1 / 3 — Eyes OPEN")
    st.caption("Look straight at the camera. Keep your eyes clearly open.")

    if st.session_state.photo_open is not None:
        render_check("Step 1 completed", True, "Eyes open — validated")
    else:
        cam1 = st.camera_input("Photo 1 — eyes open", key="cam_open")
        if cam1 is not None:
            img = to_bgr(cam1)
            with st.spinner("Validating..."):
                ok, msg, info = validate_eyes_open(img)

            if ok:
                st.session_state.photo_open = img
                st.session_state.last_validation["step1"] = info
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                render_check("Validation failed", False, msg)
                st.warning("🔄 Click **Clear photo** and try again.")

    st.markdown("---")

    # =================== STEP 2 ===================
    st.markdown("### Step 2 / 3 — Eyes CLOSED (blink)")
    st.caption("Close your eyes fully and take the photo.")

    if st.session_state.photo_open is None:
        st.info("Complete Step 1 first.")
    elif st.session_state.photo_closed is not None:
        render_check("Step 2 completed", True, "Eyes closed — validated")
    else:
        cam2 = st.camera_input("Photo 2 — eyes closed", key="cam_closed")
        if cam2 is not None:
            img = to_bgr(cam2)
            with st.spinner("Validating..."):
                ok, msg, info = validate_eyes_closed(img)

            if ok:
                st.session_state.photo_closed = img
                st.session_state.last_validation["step2"] = info
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                render_check("Validation failed", False, msg)
                st.warning("🔄 Click **Clear photo** and try again with eyes fully closed.")

    st.markdown("---")

    # =================== STEP 3 ===================
    st.markdown("### Step 3 / 3 — Head turned slightly")
    st.caption("Turn your head ~15° to one side (left or right).")

    if st.session_state.photo_closed is None:
        st.info("Complete Steps 1 and 2 first.")
    elif st.session_state.photo_turned is not None:
        render_check("Step 3 completed", True, "Head turned — validated")
    else:
        cam3 = st.camera_input("Photo 3 — head turned", key="cam_turned")
        if cam3 is not None:
            img = to_bgr(cam3)
            with st.spinner("Validating..."):
                ok, msg, info = validate_head_turned(img)

            if ok:
                st.session_state.photo_turned = img
                st.session_state.last_validation["step3"] = info
                st.success(f"✅ {msg}")
                st.rerun()
            else:
                render_check("Validation failed", False, msg)
                st.warning("🔄 Click **Clear photo** and turn your head more.")

    # =================== Preview ===================
    if any(st.session_state[k] is not None for k in ("photo_open", "photo_closed", "photo_turned")):
        st.markdown("---")
        st.markdown("### Captured photos (validated)")
        cols = st.columns(3)
        for col, key, label in zip(
            cols,
            ("photo_open", "photo_closed", "photo_turned"),
            ("1 — Eyes open", "2 — Eyes closed", "3 — Head turned"),
        ):
            img = st.session_state[key]
            with col:
                if img is not None:
                    st.image(
                        cv2.cvtColor(img, cv2.COLOR_BGR2RGB),
                        caption=label,
                        use_column_width=True,
                    )
                else:
                    st.info(f"{label} — pending")


# ==================================================================
# TAB 2: Result
# ==================================================================
with tab2:
    st.subheader("Liveness result")

    ready = all(st.session_state[k] is not None
                for k in ("photo_open", "photo_closed", "photo_turned"))

    if not ready:
        st.info("Complete all 3 validated photos in the **Guided capture** tab first.")
    else:
        with st.spinner("Running final liveness analysis..."):
            result = evaluate_liveness(
                st.session_state.photo_open,
                st.session_state.photo_closed,
                st.session_state.photo_turned,
            )

        if result.is_live:
            icon, label, bg, border = "🟢", "LIVE", "#d4edda", "#28a745"
        else:
            icon, label, bg, border = "🔴", "SPOOF SUSPECTED", "#f8d7da", "#dc3545"

        st.markdown(
            f"""
            <div style='padding:24px;border-radius:12px;background:{bg};
                        border:2px solid {border};text-align:center;margin-bottom:20px;'>
                <div style='font-size:56px;line-height:1;'>{icon}</div>
                <div style='font-size:26px;font-weight:bold;color:{border};margin-top:8px;'>
                    {label}
                </div>
                <div style='font-size:14px;color:#666;margin-top:6px;'>
                    Confidence: <b>{result.confidence:.2f}</b> / 1.00
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.info(f"**Reason:** {result.reason}")

        st.markdown("### Signals")
        col1, col2, col3 = st.columns(3)
        with col1:
            render_check("Blink detected", result.blink_detected)
        with col2:
            render_check("Head movement detected", result.head_movement_detected)
        with col3:
            render_check("Texture looks real", result.texture_looks_real)

        with st.expander("🔬 Technical details"):
            st.markdown("**Per-step validation (capture time):**")
            st.json(st.session_state.last_validation)

            st.markdown("**Overall signals (post-capture analysis):**")
            st.json(result.details)

        with st.expander("📖 How liveness detection works"):
            st.markdown(
                """
                **Per-step validation** happens at capture time:

                - Step 1: eyes must be OPEN (EAR > 0.20)
                - Step 2: eyes must be CLOSED (EAR < 0.18)
                - Step 3: head must be TURNED (nose offset > 15% of face width)

                **Overall analysis** combines three signals:

                - Blink: EAR drop between step 1 and step 2 (+0.40)
                - Head movement: nose shift between step 1 and step 3 (+0.30)
                - Texture: Laplacian variance + FFT peak ratio (+0.30)

                **LIVE verdict** requires score 0.50 or higher AND (blink OR head movement).
                """
            )

        st.markdown("---")
        if st.button("🔄 Try again with new photos", use_container_width=True):
            for key in ("photo_open", "photo_closed", "photo_turned"):
                st.session_state[key] = None
            st.session_state.last_validation = {}
            st.rerun()