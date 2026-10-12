"""
Streamlit app: PDF Digital Signature.

Covers FR-09 (upload), FR-10 (electronic signature), FR-11 (cryptographic signing).

SECURITY: Private key is stored server-side (certs/signing_key.pem).
It is NEVER sent to the browser.
"""
import io
from pathlib import Path
from datetime import datetime

import streamlit as st
from PIL import Image

from certs import (
    generate_self_signed_cert, cert_exists,
    load_cert_info, delete_cert,
    KEY_PATH, CERT_PATH,
)
from pdf_signer import (
    validate_pdf, validate_signature_image,
    sign_pdf, get_signature_count, list_signature_fields,
    make_demo_pdf,
)


# ---------- Page ----------
st.set_page_config(
    page_title="PDF Digital Signature",
    page_icon="🔐",
    layout="wide",
)

st.title("🔐 PDF Digital Signature")
st.caption("Project 5 — Cryptographic signing with X.509 certificates (pyHanko)")


# ---------- Ensure dirs ----------
Path("uploads").mkdir(exist_ok=True)
Path("signed").mkdir(exist_ok=True)
Path("certs").mkdir(exist_ok=True)


# ---------- Sidebar: Certificate management ----------
st.sidebar.header("🔑 Signing Certificate")

if cert_exists():
    info = load_cert_info()
    st.sidebar.success("Certificate loaded")
    st.sidebar.markdown(
        f"""
        **Subject CN:** `{info.get('subject_cn', '')}`  
        **Org:** `{info.get('subject_org', '')}`  
        **Country:** `{info.get('subject_country', '')}`  
        **Serial:** `{info.get('serial', '')[:20]}...`  
        **Valid from:** `{info.get('not_before').strftime('%Y-%m-%d')}`  
        **Valid to:** `{info.get('not_after').strftime('%Y-%m-%d')}`  
        **Self-signed:** `{info.get('is_self_signed')}`
        """
    )

    if st.sidebar.button("🗑️ Delete & Regenerate Certificate", use_container_width=True):
        delete_cert()
        st.rerun()
else:
    st.sidebar.warning("No certificate found")

    with st.sidebar.form("gen_cert_form"):
        st.markdown("**Generate self-signed certificate**")
        cn = st.text_input("Common Name (your name)", value="M Adnan Taj")
        org = st.text_input("Organization", value="Biometric Verification Portfolio")
        country = st.text_input("Country code (2 letters)", value="PK", max_chars=2)
        days = st.number_input("Valid for (days)", min_value=30, max_value=3650, value=365)
        submit = st.form_submit_button("Generate", type="primary", use_container_width=True)

        if submit:
            generate_self_signed_cert(common_name=cn, org=org, country=country, valid_days=int(days))
            st.success("Certificate generated.")
            st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown(
    """
    ### 🔒 Security Note

    The **private key never leaves the server**.  
    It is stored at `certs/signing_key.pem` and loaded only
    during signing, in the backend process. The browser sees
    only the signed PDF.
    """
)


# ---------- Tabs ----------
tab1, tab2 = st.tabs(["📄 Upload & Sign", "🧪 Demo PDF"])


# ==================================================================
# TAB 1: Upload & Sign
# ==================================================================
with tab1:
    st.subheader("Upload a PDF and apply a digital signature")
    st.caption("FR-09 (upload) + FR-10 (electronic signature) + FR-11 (cryptographic signature)")

    if not cert_exists():
        st.warning("⚠️ No signing certificate. Generate one from the sidebar first.")
        st.stop()

    col_left, col_right = st.columns([1, 1])

    # ---------- LEFT: Upload + metadata ----------
    with col_left:
        st.markdown("### 📤 1. Upload PDF")

        pdf_file = st.file_uploader("Choose a PDF file (max 20 MB)", type=["pdf"])

        pdf_bytes = None
        if pdf_file is not None:
            pdf_bytes = pdf_file.getvalue()

            valid, err = validate_pdf(pdf_bytes, pdf_file.name)
            if not valid:
                st.error(f"❌ Invalid PDF: {err}")
                pdf_bytes = None
            else:
                size_kb = len(pdf_bytes) / 1024
                st.success(f"✅ Valid PDF — {size_kb:.1f} KB")

                n_existing = get_signature_count(pdf_bytes)
                if n_existing > 0:
                    st.warning(f"⚠️ This PDF already has {n_existing} signature(s).")

        st.markdown("---")
        st.markdown("### ✍️ 2. Signature Metadata")

        signer_name = st.text_input("Signer name", value="M Adnan Taj")
        reason = st.text_input("Reason", value="Document approval")
        location = st.text_input("Location", value="Pakistan")

        st.markdown("---")
        st.markdown("### 🎨 3. Drawn Signature (optional)")
        st.caption(
            "Upload a PNG/JPEG of your handwritten signature. "
            "It is validated and previewed but only cryptographic signature is applied."
        )

        sig_file = st.file_uploader(
            "Signature image",
            type=["png", "jpg", "jpeg"],
            key="sig_img",
        )

        sig_img_bytes = None
        if sig_file is not None:
            sig_img_bytes = sig_file.getvalue()
            v, e = validate_signature_image(sig_img_bytes, sig_file.name)
            if not v:
                st.error(f"❌ {e}")
                sig_img_bytes = None
            else:
                try:
                    st.image(Image.open(io.BytesIO(sig_img_bytes)),
                             caption="Your signature", width=200)
                except Exception:
                    st.warning("Could not preview signature image.")

    # ---------- RIGHT: Preview + Sign ----------
    with col_right:
        st.markdown("### 📄 4. Preview & Sign")

        if pdf_bytes is None:
            st.info("👈 Upload a PDF to continue.")
        else:
            st.markdown("**PDF loaded:**")
            st.write(f"- Size: `{len(pdf_bytes) / 1024:.1f} KB`")
            st.write(f"- Existing signatures: `{get_signature_count(pdf_bytes)}`")

            st.markdown("---")

            if st.button("🔐 Sign PDF", type="primary", use_container_width=True):
                with st.spinner("Signing PDF (server-side)..."):
                    out_name = f"signed/signed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                    ok, err = sign_pdf(
                        pdf_bytes,
                        out_name,
                        signer_name=signer_name,
                        reason=reason,
                        location=location,
                    )

                if not ok:
                    st.error(f"❌ {err}")
                else:
                    st.success("✅ PDF signed successfully.")

                    with open(out_name, "rb") as f:
                        signed_bytes = f.read()

                    st.markdown("#### Signature details")
                    n_sigs = get_signature_count(signed_bytes)

                    st.write(f"**Embedded signatures:** {n_sigs}")
                    info = load_cert_info()
                    st.write(f"**Signed by:** `{signer_name}` ({info.get('subject_cn', '')})")
                    st.write(f"**Reason:** `{reason}`")
                    st.write(f"**Location:** `{location}`")
                    st.write(f"**Certificate serial:** `{info.get('serial', '')[:20]}...`")

                    st.download_button(
                        "📥 Download signed PDF",
                        signed_bytes,
                        file_name=Path(out_name).name,
                        mime="application/pdf",
                        use_container_width=True,
                    )

                    st.caption(
                        "⚠️ This is a **self-signed** certificate. "
                        "Adobe Reader will show it as untrusted — this is expected. "
                        "For trust, use a CA-issued certificate."
                    )


# ==================================================================
# TAB 2: Demo PDF
# ==================================================================
with tab2:
    st.subheader("Generate a demo PDF for testing")
    st.caption(
        "You can use this to test signing without needing your own PDF. "
        "Useful when you want a clean, quick demo."
    )

    demo_text = st.text_input("Document title", value="Service Agreement")

    if st.button("📄 Generate Demo PDF", type="primary"):
        pdf = make_demo_pdf(demo_text)
        st.success(f"✅ Generated {len(pdf)} bytes.")
        st.download_button(
            "📥 Download demo PDF",
            pdf,
            file_name="demo_contract.pdf",
            mime="application/pdf",
        )


# ---------- Footer ----------
st.markdown("---")
st.caption(
    "🔒 **Private key safety:** The signing key is loaded server-side only. "
    "It is never transmitted to or stored in the browser. "
    "Signed PDFs can be verified later (Project 6)."
)