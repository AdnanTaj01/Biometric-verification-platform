"""
Streamlit app: Unified Biometric Verification Engine.
Covers FR-04, FR-07, partial FR-13.

Fix history:
- v3: Prevent infinite rerun loops by hashing camera input and skipping
      reprocessing of the same frame. Removed st.rerun() from camera blocks.
"""
import streamlit as st
import cv2
import numpy as np
import pandas as pd
from PIL import Image
import io
import hashlib

from database import init_db
from face_engine import detect_faces, get_largest_face
from mock_sdk import FingerprintScanner
from verification import (
    list_identities, create_identity, delete_identity,
    enroll_face, enroll_fingerprint,
    verify_face, verify_fingerprint,
    get_verification_history, get_stats,
)


# ---------- Init ----------
init_db()

st.set_page_config(
    page_title="Biometric Verification Engine",
    page_icon="🎯",
    layout="wide",
)

st.title("🎯 Biometric Verification Engine")
st.caption("Project 4 — Unified face + fingerprint verification with database persistence")


# ---------- Session state ----------
if "scanner" not in st.session_state:
    st.session_state.scanner = FingerprintScanner()
    st.session_state.scanner.connect()

if "last_face_result" not in st.session_state:
    st.session_state.last_face_result = None

if "last_fp_result" not in st.session_state:
    st.session_state.last_fp_result = None

if "face_img_hash" not in st.session_state:
    st.session_state.face_img_hash = None

if "cached_stats" not in st.session_state:
    st.session_state.cached_stats = get_stats()

scanner = st.session_state.scanner


def refresh_stats():
    """Recompute stats and cache in session_state."""
    st.session_state.cached_stats = get_stats()


def hash_bytes(data: bytes) -> str:
    """Return a short deterministic hash of bytes (used to detect new captures)."""
    return hashlib.md5(data).hexdigest()


# ---------- Sidebar: Stats ----------
stats = st.session_state.cached_stats

st.sidebar.header("📊 Live Stats")
st.sidebar.metric("Registered Identities", stats["total_identities"])
st.sidebar.metric("Total Verifications", stats["total_verifications"])
st.sidebar.metric("✅ Matches", stats["matches"])
st.sidebar.metric("❌ No Matches", stats["no_matches"])
st.sidebar.metric("⚠️ Unable to Verify", stats["unable"])

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Refresh Stats", use_container_width=True):
    refresh_stats()
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.caption(
    "This app combines Project 1 (face) and Project 2 (fingerprint) into "
    "a unified verification system backed by SQLite."
)


# ---------- Tabs ----------
tab1, tab2, tab3 = st.tabs(["➕ Enroll Identity", "🎯 Verify", "📜 History"])


# ==================================================================
# TAB 1: Enroll
# ==================================================================
with tab1:
    st.subheader("Register a new test identity")
    st.caption(
        "Yeh FR-02 (Test Identity Registration) ka database version hai. "
        "Face ya fingerprint ya dono enroll kar sakte hain."
    )

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("### 👤 Identity Details")
        name_input = st.text_input("Display name", placeholder="e.g., Ali Khan")
        consent = st.checkbox("Consent given", value=True)

        if st.button("Create Identity", type="primary", use_container_width=True):
            if not name_input.strip():
                st.warning("Enter a name first.")
            else:
                new_id = create_identity(name_input.strip(), consent)
                refresh_stats()
                st.success(f"Identity created: **{name_input}** (id={new_id})")
                st.rerun()

    with col_b:
        st.markdown("### 📋 Existing Identities")
        identities = list_identities()
        if identities:
            for iid, name in identities:
                cols = st.columns([4, 1])
                with cols[0]:
                    st.write(f"• **{name}** `(id={iid})`")
                with cols[1]:
                    if st.button("🗑️", key=f"del_{iid}"):
                        delete_identity(iid)
                        refresh_stats()
                        st.rerun()
        else:
            st.info("No identities yet.")

    st.markdown("---")
    st.markdown("### 🔗 Enroll Biometric Data")

    identities = list_identities()
    if not identities:
        st.info("Create an identity first above.")
    else:
        identity_options = {f"{name} (id={iid})": iid for iid, name in identities}

        col_face, col_fp = st.columns(2)

        # ----- Face enrollment -----
        with col_face:
            st.markdown("#### 📷 Face")
            selected_face = st.selectbox(
                "Select identity (face)", list(identity_options.keys()),
                key="face_id_select",
            )
            face_cam = st.camera_input("Reference photo", key="face_cam")

            if face_cam is not None:
                # Detect new capture via hash
                img_hash = hash_bytes(face_cam.getvalue())
                enroll_key = f"enroll_face_hash_{selected_face}"

                if st.session_state.get(enroll_key) != img_hash:
                    # New capture — show enroll button
                    if st.button("Enroll Face", key="enroll_face_btn",
                                 type="primary", use_container_width=True):
                        pil = Image.open(io.BytesIO(face_cam.getvalue())).convert("RGB")
                        img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

                        with st.spinner("Detecting face..."):
                            faces = detect_faces(img)
                            face = get_largest_face(faces)

                        if face is None:
                            st.error("No face detected in photo.")
                        else:
                            iid = identity_options[selected_face]
                            enroll_face(iid, face.embedding)
                            refresh_stats()
                            st.session_state[enroll_key] = img_hash
                            st.success(f"✅ Face enrolled for **{selected_face}**")
                else:
                    st.success(f"✅ Face already enrolled for **{selected_face}**")
                    st.caption("Clear the photo and take a new one to re-enroll.")

        # ----- Fingerprint enrollment -----
        with col_fp:
            st.markdown("#### 🖐️ Fingerprint")
            selected_fp = st.selectbox(
                "Select identity (fingerprint)", list(identity_options.keys()),
                key="fp_id_select",
            )

            seed = st.number_input("Finger ID (seed)", min_value=0, max_value=9999,
                                   value=1, step=1, key="fp_enroll_seed")

            cols_fp = st.columns(2)
            with cols_fp[0]:
                if st.button("👆 Place Finger", key="place_fp"):
                    scanner.simulate_finger_placed()
                    st.toast("Finger placed")
            with cols_fp[1]:
                if st.button("🖐️ Capture & Enroll", key="enroll_fp_btn",
                             type="primary", use_container_width=True):
                    result = scanner.capture(seed=int(seed))
                    if not result.success:
                        st.error(f"Capture failed: {result.error_message}")
                    else:
                        st.write(f"Quality: **{result.quality_score}/100**")
                        iid = identity_options[selected_fp]
                        enroll_fingerprint(iid, result.template)
                        refresh_stats()
                        st.success(f"✅ Fingerprint enrolled for **{selected_fp}**")


# ==================================================================
# TAB 2: Verify
# ==================================================================
with tab2:
    st.subheader("Verify a biometric sample")
    st.caption("FR-04 (face) + FR-07 (fingerprint) — 1:N matching against enrolled identities")

    col_face, col_fp = st.columns(2)

    # ----- Face verification -----
    with col_face:
        st.markdown("### 📷 Face Verification")
        face_verify_cam = st.camera_input("Capture for verification", key="face_verify_cam")

        if face_verify_cam is not None:
            img_bytes = face_verify_cam.getvalue()
            img_hash = hash_bytes(img_bytes)

            # Only process if this is a NEW capture (hash changed)
            if st.session_state.face_img_hash != img_hash:
                pil = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)

                with st.spinner("Matching..."):
                    faces = detect_faces(img)
                    face = get_largest_face(faces)

                if face is None:
                    st.session_state.last_face_result = {
                        "result": "Unable to Verify",
                        "reason": "No face detected in image",
                        "best_match": None,
                        "best_score": 0.0,
                        "all_scores": {},
                    }
                else:
                    result = verify_face(face.embedding, threshold=0.4)
                    st.session_state.last_face_result = result

                # Mark this image as processed — prevents reprocessing on rerun
                st.session_state.face_img_hash = img_hash
                refresh_stats()

            # Display last result
            result = st.session_state.last_face_result
            if result is not None:
                st.markdown("---")
                st.markdown("#### 📊 Result")

                if result["result"] == "Match":
                    st.success(f"✅ **Match**: {result['best_match']}  \n"
                               f"Score: `{result['best_score']:.4f}`")
                elif result["result"] == "No Match":
                    st.error(f"❌ **No Match** — best: `{result['best_match']}` "
                             f"({result['best_score']:.4f})")
                else:
                    st.warning(f"⚠️ {result['result']}: {result.get('reason', '')}")

                with st.expander("All scores"):
                    for n, s in sorted(result.get("all_scores", {}).items(),
                                       key=lambda x: -x[1]):
                        st.write(f"• {n}: `{s:.4f}`")

                if st.button("Clear face result", key="clear_face_result"):
                    st.session_state.last_face_result = None
                    st.session_state.face_img_hash = None
                    st.rerun()

    # ----- Fingerprint verification -----
    with col_fp:
        st.markdown("### 🖐️ Fingerprint Verification")

        seed_v = st.number_input("Finger ID (seed)", min_value=0, max_value=9999,
                                 value=1, step=1, key="fp_verify_seed")
        threshold_fp = st.slider("Fingerprint threshold", 0.5, 1.0, 0.85, 0.01,
                                 key="fp_thr")

        cols_fp = st.columns(2)
        with cols_fp[0]:
            if st.button("👆 Place Finger", key="place_fp_v"):
                scanner.simulate_finger_placed()
                st.toast("Finger placed")
        with cols_fp[1]:
            # NOTE: This button only returns True on the click run.
            # After any rerun, it returns False — so no infinite loop possible here.
            if st.button("🎯 Capture & Verify", key="verify_fp_btn",
                         type="primary", use_container_width=True):
                result = scanner.capture(seed=int(seed_v))
                if not result.success:
                    st.session_state.last_fp_result = {
                        "result": "Unable to Verify",
                        "reason": result.error_message,
                        "best_match": None,
                        "best_score": 0.0,
                        "all_scores": {},
                    }
                else:
                    v = verify_fingerprint(result.template, threshold=threshold_fp)
                    st.session_state.last_fp_result = v

                refresh_stats()
                # No st.rerun() — display result in the same run

        # Display last stored result
        if st.session_state.last_fp_result is not None:
            v = st.session_state.last_fp_result

            st.markdown("---")
            st.markdown("#### 📊 Result")

            if v["result"] == "Match":
                st.success(f"✅ **Match**: {v['best_match']}  \n"
                           f"Score: `{v['best_score']:.4f}`")
            elif v["result"] == "No Match":
                st.error(f"❌ **No Match** — best: `{v['best_match']}` "
                         f"({v['best_score']:.4f})")
            else:
                st.warning(f"⚠️ {v['result']}: {v.get('reason', '')}")

            with st.expander("All scores"):
                for n, s in sorted(v.get("all_scores", {}).items(),
                                   key=lambda x: -x[1]):
                    st.write(f"• {n}: `{s:.4f}`")

            if st.button("Clear fingerprint result", key="clear_fp_result"):
                st.session_state.last_fp_result = None
                st.rerun()


# ==================================================================
# TAB 3: History
# ==================================================================
with tab3:
    st.subheader("Verification History")
    st.caption("FR-13 (partial) — every verification is persisted to database")

    history = get_verification_history(limit=200)

    if not history:
        st.info("No verification records yet.")
    else:
        # Use freshly-read history counts for consistency with the table below
        total = len(history)
        matches = sum(1 for h in history if h["result"] == "Match")
        no_matches = sum(1 for h in history if h["result"] == "No Match")
        unable = sum(1 for h in history if h["result"] == "Unable to Verify")

        cols = st.columns(4)
        cols[0].metric("Total", total)
        cols[1].metric("Matches", matches)
        cols[2].metric("No Match", no_matches)
        cols[3].metric("Unable", unable)

        st.caption(
            "ℹ️ Sidebar stats may lag by 1-2 records. "
            "Click **🔄 Refresh Stats** in the sidebar to sync."
        )

        modality_filter = st.selectbox("Filter by modality", ["All", "face", "fingerprint"])
        result_filter = st.selectbox("Filter by result",
                                     ["All", "Match", "No Match", "Unable to Verify"])

        filtered = history
        if modality_filter != "All":
            filtered = [h for h in filtered if h["modality"] == modality_filter]
        if result_filter != "All":
            filtered = [h for h in filtered if h["result"] == result_filter]

        st.markdown(f"**{len(filtered)} records**")

        df = pd.DataFrame([
            {
                "ID": h["id"],
                "Modality": h["modality"],
                "Type": h["type"],
                "Result": h["result"],
                "Score": f"{h['score']:.4f}" if h["score"] else "-",
                "Source": h["source"],
                "Timestamp": h["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
            }
            for h in filtered
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        csv = df.to_csv(index=False)
        st.download_button("📥 Download CSV", csv, "verification_history.csv", "text/csv")


# ---------- Footer ----------
st.markdown("---")
st.caption(
    "⚠️ **Known limitations:**\n"
    "- Sidebar stats may lag by 1-2 records (Streamlit rerun model). "
    "Click 🔄 Refresh Stats to force re-read.\n"
    "- Face verification processes each new photo only once (hash-based guard)."
)