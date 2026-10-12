"""
Streamlit app: PDF Signature Verification.

Covers FR-12: verify signed PDFs — integrity, validity, trust.
Fully self-contained — generates its own test fixtures and cert.
"""
from pathlib import Path

import streamlit as st

from certs import (
    cert_exists, ensure_cert, load_cert_info,
    delete_cert, CERT_PATH,
)
from test_fixtures import (
    generate_all_fixtures, cleanup_fixtures,
    UNSIGNED_PATH, SIGNED_PATH, TAMPERED_PATH,
)
from verify import verify_pdf, count_signatures


st.set_page_config(
    page_title="PDF Signature Verification",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 PDF Signature Verification")
st.caption("Project 6 — Verify cryptographic validity, integrity, and trust (FR-12)")


def _render_flag(label: str, value, tooltip: str = ""):
    if value is True:
        bg, border, icon = "#d4edda", "#28a745", "✅"
    elif value is False:
        bg, border, icon = "#f8d7da", "#dc3545", "❌"
    else:
        bg, border, icon = "#e2e3e5", "#6c757d", "❓"
    st.markdown(
        f"<div style='padding:10px;border-radius:6px;background:{bg};"
        f"border-left:5px solid {border};'>"
        f"<b>{icon} {label}</b><br>"
        f"<span style='font-size:11px;color:#666;'>{tooltip}</span></div>",
        unsafe_allow_html=True,
    )


# ---------- Ensure fixtures ----------
Path("data/fixtures").mkdir(parents=True, exist_ok=True)
Path("data/certs").mkdir(parents=True, exist_ok=True)
ensure_cert()
if not SIGNED_PATH.exists():
    generate_all_fixtures()


# ---------- Sidebar ----------
st.sidebar.header("⚙️ Settings")

use_trust = st.sidebar.checkbox(
    "Use trust context (local test cert)",
    value=True,
    help="If checked, the locally generated test certificate is treated as a trusted root.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("📋 Local Test Certificate")
info = load_cert_info()
if info:
    st.sidebar.markdown(
        f"""
        **CN:** `{info.get('subject_cn', '')}`  
        **Org:** `{info.get('subject_org', '')}`  
        **Serial:** `{info.get('serial', '')[:20]}...`  
        **Valid to:** `{info.get('not_after').strftime('%Y-%m-%d')}`  
        **Self-signed:** `{info.get('is_self_signed')}`
        """
    )

if st.sidebar.button("♻️ Regenerate cert & fixtures", use_container_width=True):
    delete_cert()
    cleanup_fixtures()
    ensure_cert()
    generate_all_fixtures(force=True)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 📖 SRS FR-12 Categories

    - ✅ Cryptographically valid
    - ❌ Signature invalid
    - ⚠️ Document modified
    - 🔒 Certificate untrusted
    - ❓ Inconclusive
    """
)


# ---------- Render function ----------
def render_verification(pdf_bytes: bytes, filename: str):
    size_kb = len(pdf_bytes) / 1024
    st.markdown(f"### 📄 `{filename}` — `{size_kb:.1f} KB`")

    n_sigs = count_signatures(pdf_bytes)
    if n_sigs == 0:
        st.warning("⚠️ No signatures found in this PDF.")
        st.info("Upload a signed PDF or use the **Test with Fixtures** tab.")
        return

    st.success(f"Found **{n_sigs}** embedded signature(s).")

    trust_path = str(CERT_PATH) if use_trust else None

    with st.spinner("Verifying..."):
        result = verify_pdf(pdf_bytes, trust_cert_path=trust_path)

    if result.get("error"):
        st.error(f"❌ {result['error']}")
        return

    overall = result["overall"]
    meta = {
        "VALID":        ("🟢", "CRYPTOGRAPHICALLY VALID", "#d4edda", "#28a745"),
        "UNTRUSTED":    ("🟡", "VALID BUT UNTRUSTED", "#fff3cd", "#856404"),
        "MODIFIED":     ("🔴", "DOCUMENT MODIFIED AFTER SIGNING", "#f8d7da", "#dc3545"),
        "INVALID":      ("🔴", "SIGNATURE INVALID", "#f8d7da", "#dc3545"),
        "INCONCLUSIVE": ("⚪", "VERIFICATION INCONCLUSIVE", "#e2e3e5", "#383d41"),
        "NO_SIGNATURE": ("⚪", "NO SIGNATURES", "#e2e3e5", "#383d41"),
    }
    icon, label, bg, border = meta.get(overall, meta["INCONCLUSIVE"])

    st.markdown(
        f"""
        <div style='padding:20px;border-radius:10px;background:{bg};
                    border:2px solid {border};text-align:center;margin-bottom:20px;'>
            <div style='font-size:48px;line-height:1;'>{icon}</div>
            <div style='font-size:22px;font-weight:bold;color:{border};margin-top:8px;'>
                {label}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    for i, sig in enumerate(result["signatures"], 1):
        st.markdown(f"### 📝 Signature #{i} — `{sig.get('field_name', '?')}`")

        col_a, col_b, col_c = st.columns(3)
        with col_a:
            _render_flag("Intact", sig.get("intact"), "Content unchanged")
        with col_b:
            _render_flag("Cryptographically valid", sig.get("valid"), "Hash matches")
        with col_c:
            _render_flag("Trusted", sig.get("trusted"), "CA chain")

        st.info(f"**Verdict:** {sig.get('verdict', 'Unknown')}")

        with st.expander("👤 Signer certificate details"):
            st.write(f"**Common Name:** `{sig.get('signer_cn', '-')}`")
            st.write(f"**Issuer CN:** `{sig.get('signer_issuer', '-')}`")
            st.write(f"**Serial:** `{sig.get('signer_serial', '-')}`")
            st.write(f"**Valid from:** `{sig.get('signer_not_before', '-')}`")
            st.write(f"**Valid to:** `{sig.get('signer_not_after', '-')}`")
            st.write(f"**Signing time:** `{sig.get('signing_time', '-')}`")
            st.write(f"**Digest:** `{sig.get('md_algorithm', '-')}`")
            st.write(f"**Mechanism:** `{sig.get('signature_mechanism', '-')}`")


# ---------- Tabs ----------
tab1, tab2 = st.tabs(["📤 Upload PDF", "🧪 Test with Fixtures"])


with tab1:
    st.subheader("Upload a signed PDF")
    st.caption("Verify any PDF with embedded signatures.")

    pdf_file = st.file_uploader("Choose a PDF", type=["pdf"])

    if pdf_file is not None:
        render_verification(pdf_file.getvalue(), pdf_file.name)
    else:
        st.info("👈 Upload a PDF to begin. Or use the **Test with Fixtures** tab.")


with tab2:
    st.subheader("Test with pre-generated fixtures")
    st.caption(
        "Project 6 generates three test PDFs locally — no external signed PDFs needed."
    )

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("#### 📄 Unsigned")
        st.caption("Expected: **NO_SIGNATURE**")
        if UNSIGNED_PATH.exists():
            if st.button("Verify unsigned", use_container_width=True, key="btn_unsigned"):
                render_verification(UNSIGNED_PATH.read_bytes(), UNSIGNED_PATH.name)
            with open(UNSIGNED_PATH, "rb") as f:
                st.download_button(
                    "Download", f.read(),
                    file_name="unsigned.pdf", mime="application/pdf",
                    key="dl_unsigned", use_container_width=True,
                )

    with col2:
        st.markdown("#### ✅ Valid signed")
        st.caption("Expected: **VALID** (with trust) / **UNTRUSTED** (without)")
        if SIGNED_PATH.exists():
            if st.button("Verify signed", use_container_width=True, key="btn_signed"):
                render_verification(SIGNED_PATH.read_bytes(), SIGNED_PATH.name)
            with open(SIGNED_PATH, "rb") as f:
                st.download_button(
                    "Download", f.read(),
                    file_name="signed.pdf", mime="application/pdf",
                    key="dl_signed", use_container_width=True,
                )

    with col3:
        st.markdown("#### ⚠️ Tampered")
        st.caption("Expected: **MODIFIED**")
        if TAMPERED_PATH.exists():
            if st.button("Verify tampered", use_container_width=True, key="btn_tampered"):
                render_verification(TAMPERED_PATH.read_bytes(), TAMPERED_PATH.name)
            with open(TAMPERED_PATH, "rb") as f:
                st.download_button(
                    "Download", f.read(),
                    file_name="tampered.pdf", mime="application/pdf",
                    key="dl_tampered", use_container_width=True,
                )

    st.markdown("---")
    if st.button("🔁 Regenerate fixtures"):
        generate_all_fixtures(force=True)
        st.success("Fixtures regenerated.")
        st.rerun()


with st.expander("📖 Cryptographic validity vs Trust vs Legal enforceability"):
    st.markdown(
        """
        | Concept | Question | Determined by |
        |---|---|---|
        | **Cryptographic validity** | Does the signature match content? | Hash comparison |
        | **Trust** | Is cert chained to a trusted root? | Cert path validation |
        | **Legal enforceability** | Would a court accept it? | Jurisdiction + CA + TSA |

        Our self-signed cert is:
        - ✅ Cryptographically valid
        - ❌ Not trusted by default
        - ⚠️ Not legally binding without a CA + TSA

        Toggle **"Use trust context"** to simulate trust.
        """
    )


st.markdown("---")
st.caption("🔒 Private key never leaves the server. Verification is read-only.")