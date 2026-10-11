"""
Streamlit app: Fingerprint Scanner Integration.

Covers SRS requirements:
- FR-06: Fingerprint Capture with connection status, progress, quality indicators
- FR-07: Fingerprint Verification against enrolled templates
"""
import streamlit as st
import numpy as np

from mock_sdk import FingerprintScanner, SDKError
from fingerprint_engine import (
    enroll_template,
    verify_template,
    load_templates,
)


# ---------- Page config ----------
st.set_page_config(
    page_title="Fingerprint Scanner Integration",
    page_icon="🖐️",
    layout="wide",
)

st.title("🖐️ Fingerprint Scanner Integration")
st.caption("Project 2 — Biometric Identity Verification Portfolio")

# ---------- Session state ----------
if "scanner" not in st.session_state:
    st.session_state.scanner = FingerprintScanner()
if "last_capture" not in st.session_state:
    st.session_state.last_capture = None


scanner = st.session_state.scanner


# ---------- Sidebar ----------
st.sidebar.header("⚙️ Settings")

threshold = st.sidebar.slider(
    "Match Threshold",
    min_value=0.5, max_value=1.0, value=0.85, step=0.01,
    help="Similarity threshold for fingerprint match"
)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Enrolled Identities")
enrolled = load_templates()
if enrolled:
    for name in enrolled.keys():
        st.sidebar.write(f"• {name}")
else:
    st.sidebar.warning("No fingerprints enrolled yet.")

st.sidebar.markdown("---")
st.sidebar.caption(
    "ℹ️ **Mock SDK Notice**\n\n"
    "This demo uses a mock fingerprint SDK that mimics the interface of real vendor SDKs "
    "(DigitalPersona, Futronic, Mantra). The application code is ready to swap in a real "
    "SDK with only the import changing."
)


# ---------- Helper: render indicator ----------
def render_check(name: str, passed: bool, message: str):
    """Render a red/green indicator with text label."""
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


# ---------- Layout ----------
col_left, col_right = st.columns([1, 1])

# ============ LEFT: Device status + controls ============
with col_left:
    st.subheader("🔌 Device Status")

    status = scanner.get_device_status()

    if status["connected"]:
        st.success(
            f"🟢 **Connected** — {status['device_name']}  \n"
            f"Firmware: `{status['firmware']}`  \n"
            f"SDK: `{status['sdk_version']}`"
        )
    else:
        st.error("🔴 **Scanner not connected**")

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔗 Connect", disabled=status["connected"], use_container_width=True):
            with st.spinner("Connecting to scanner..."):
                scanner.connect()
            st.rerun()
    with col_b:
        if st.button("⏏️ Disconnect", disabled=not status["connected"], use_container_width=True):
            scanner.disconnect()
            st.rerun()

    st.markdown("---")

    # ---------- Simulation controls (would be real hardware in production) ----------
    st.subheader("🎛️ Simulation Controls")
    st.caption(
        "In production, these are handled by the hardware. "
        "For this demo, use these to simulate finger placement."
    )

    col_c, col_d = st.columns(2)
    with col_c:
        if st.button("👆 Place Finger", use_container_width=True,
                     disabled=not status["connected"]):
            scanner.simulate_finger_placed()
            st.toast("Finger placed on sensor", icon="👆")
    with col_d:
        if st.button("✋ Lift Finger", use_container_width=True,
                     disabled=not status["connected"]):
            scanner.simulate_finger_lifted()
            st.toast("Finger lifted", icon="✋")


# ============ RIGHT: Capture + Verify ============
with col_right:
    st.subheader("📸 Capture & Verify")

    if not status["connected"]:
        st.info("👈 Connect the scanner first.")
    else:
        mode = st.radio(
            "Mode",
            ["🔍 Verify (match against enrolled)", "➕ Enroll (register new)"],
            horizontal=True,
        )

        if mode.startswith("➕"):
            identity_name = st.text_input("Identity name", placeholder="e.g., Ali Khan")

        capture_seed = st.number_input(
            "Finger ID (seed) — for demo purposes",
            min_value=0, max_value=9999, value=1, step=1,
            help="Same seed = same fingerprint. Different seed = different fingerprint. "
                 "This simulates putting different fingers on the scanner.",
        )

        if st.button("🖐️ Capture Fingerprint", type="primary", use_container_width=True):
            with st.spinner("Capturing..."):
                result = scanner.capture(timeout=5, seed=int(capture_seed))
            st.session_state.last_capture = result

        # ---------- Show last capture result ----------
        result = st.session_state.last_capture
        if result is not None:
            st.markdown("---")
            st.markdown("### 📊 Capture Result")

            # Connection check
            render_check("Scanner Connected", True, "Device is online")

            # Finger detection
            if result.error_code == SDKError.NO_FINGER:
                render_check("Finger Detected", False, "No finger on sensor")
                st.warning("👆 Place your finger on the scanner and try again.")
            else:
                render_check("Finger Detected", True, "Finger detected")

            # Quality
            if result.quality_score > 0:
                quality_ok = result.quality_score >= 55
                render_check(
                    "Quality",
                    quality_ok,
                    f"Score: {result.quality_score}/100",
                )
            else:
                render_check("Quality", False, "No sample to score")

            # Capture outcome
            if result.success:
                st.success(
                    f"🟢 **Capture Successful** — "
                    f"took {result.capture_time_ms} ms"
                )

                # Show simulated fingerprint image
                if result.image is not None:
                    st.image(
                        result.image,
                        caption="Simulated fingerprint image",
                        width=200,
                        clamp=True,
                    )

                # ---------- Verify or Enroll ----------
                st.markdown("---")

                if mode.startswith("🔍"):
                    st.markdown("### 🎯 Verification")
                    verify = verify_template(
                        result.template, threshold=threshold
                    )
                    res = verify["result"]

                    if res == "Match":
                        st.success(
                            f"✅ **Match Found**: {verify['best_match']}  \n"
                            f"Score: `{verify['best_score']:.4f}` (threshold: {threshold})"
                        )
                    elif res == "No Match":
                        st.error(
                            f"❌ **No Match**  \n"
                            f"Best candidate: `{verify['best_match']}` "
                            f"with score `{verify['best_score']:.4f}`  \n"
                            f"(below threshold {threshold})"
                        )
                    else:
                        st.warning(f"⚠️ {res}: {verify.get('reason', '')}")

                    with st.expander("📊 All similarity scores"):
                        for name, score in sorted(
                            verify["all_scores"].items(), key=lambda x: -x[1]
                        ):
                            st.write(f"• **{name}**: `{score:.4f}`")

                else:  # Enroll
                    st.markdown("### ➕ Enrollment")
                    if not identity_name.strip():
                        st.warning("Please enter an identity name above.")
                    elif not result.success:
                        st.warning("Capture must succeed before enrolling.")
                    else:
                        if st.button(f"✅ Enroll '{identity_name}'",
                                     type="primary", use_container_width=True):
                            total = enroll_template(identity_name.strip(), result.template)
                            st.success(
                                f"Enrolled **{identity_name}**. "
                                f"Total enrolled: {total}"
                            )
                            st.rerun()

            else:
                # Failure path
                st.error(
                    f"🔴 **Capture Failed**  \n"
                    f"Error: `{result.error_message}` (code {result.error_code})"
                )

                if result.error_code == SDKError.POOR_QUALITY:
                    st.info(
                        "💡 **Tips to improve quality:**\n"
                        "- Clean the sensor\n"
                        "- Place finger flat and firmly\n"
                        "- Don't move during capture\n"
                        "- Ensure finger is not wet or too dry"
                    )
                elif result.error_code == SDKError.NO_FINGER:
                    st.info("👆 Place finger on sensor and capture again.")


# ---------- Footer ----------
st.markdown("---")
st.caption(
    "⚠️ **Disclaimer:** This demo uses a mock SDK. "
    "Real integration requires vendor SDK + physical hardware. "
    "The application interface is designed for drop-in replacement."
)