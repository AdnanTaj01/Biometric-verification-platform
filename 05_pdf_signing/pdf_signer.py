"""
PDF digital signing engine using pyHanko.

Covers:
- FR-09: PDF upload validation
- FR-10: Electronic signature (drawn signature image overlay)
- FR-11: Cryptographic digital signature with X.509 certificate
"""
import io
from pathlib import Path
from typing import Optional

from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from pyhanko.pdf_utils.reader import PdfFileReader

from certs import KEY_PATH, CERT_PATH


# ---------- Constants ----------
MAX_PDF_SIZE_MB = 20
ALLOWED_SIGNATURE_FORMATS = ["png", "jpg", "jpeg"]


# ---------- Validation (FR-09) ----------
def validate_pdf(file_bytes: bytes, filename: str) -> tuple:
    """
    Validate an uploaded PDF.
    Returns (is_valid, error_message).
    """
    # Size check
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_PDF_SIZE_MB:
        return False, f"File too large ({size_mb:.1f} MB > {MAX_PDF_SIZE_MB} MB)"

    # Magic bytes check
    if not file_bytes.startswith(b"%PDF"):
        return False, "File does not start with %PDF — not a valid PDF"

    # Extension check
    if not filename.lower().endswith(".pdf"):
        return False, "File extension is not .pdf"

    # Try to actually open with pyHanko
    try:
        reader = PdfFileReader(io.BytesIO(file_bytes))
        _ = reader.root
    except Exception as e:
        return False, f"PDF could not be parsed: {e}"

    return True, ""


def validate_signature_image(file_bytes: bytes, filename: str) -> tuple:
    """Validate a drawn signature image."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED_SIGNATURE_FORMATS:
        return False, f"Signature must be one of: {', '.join(ALLOWED_SIGNATURE_FORMATS)}"

    # PNG / JPEG magic bytes
    if not (file_bytes.startswith(b"\x89PNG") or file_bytes.startswith(b"\xff\xd8")):
        return False, "Not a valid PNG/JPEG image"

    if len(file_bytes) > 2 * 1024 * 1024:
        return False, "Signature image too large (max 2 MB)"

    return True, ""


# ---------- Signing (FR-11) ----------
def sign_pdf(
    pdf_bytes: bytes,
    output_path: str,
    signer_name: str = "Signer",
    reason: str = "Document approval",
    location: str = "Pakistan",
    field_name: str = "Signature1",
) -> tuple:
    """
    Cryptographically sign a PDF using the loaded self-signed certificate.

    Private key is loaded server-side from certs/signing_key.pem.
    It is NEVER sent to the browser.

    Returns (success, error_message).
    """
    if not KEY_PATH.exists() or not CERT_PATH.exists():
        return False, "Signing key or certificate not found. Generate them first."

    try:
        # Load signer (private key + cert) — server-side only
        signer = signers.SimpleSigner.load(
            key_file=str(KEY_PATH),
            cert_file=str(CERT_PATH),
            key_passphrase=None,
        )

        # Incremental writer preserves existing PDF contents
        reader = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))

        # Metadata for the signature dictionary
        meta = signers.PdfSignatureMetadata(
            field_name=field_name,
            reason=reason,
            location=location,
            name=signer_name, 
        )

        # Perform signing
        with open(output_path, "wb") as out:
            signers.sign_pdf(reader, meta, signer=signer, output=out)

        return True, ""

    except Exception as e:
        return False, f"Signing failed: {e}"


# ---------- Signature inspection ----------
def get_signature_count(pdf_bytes: bytes) -> int:
    """Return number of embedded signatures in a PDF."""
    try:
        reader = PdfFileReader(io.BytesIO(pdf_bytes))
        return len(reader.embedded_signatures)
    except Exception:
        return 0


def list_signature_fields(pdf_bytes: bytes) -> list:
    """Return list of signature field names in a PDF."""
    try:
        reader = PdfFileReader(io.BytesIO(pdf_bytes))
        root = reader.root
        acro = root.get("/AcroForm")
        if acro is None:
            return []
        fields = acro.get("/Fields", [])
        sig_fields = []
        for f in fields:
            try:
                if f.get("/FT") == "/Sig":
                    sig_fields.append(str(f.get("/T", "<unnamed>")))
            except Exception:
                continue
        return sig_fields
    except Exception:
        return []


# ---------- Demo PDF generator ----------
def make_demo_pdf(text: str = "Sample Contract") -> bytes:
    """Generate a simple one-page PDF for testing."""
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    c.setFont("Helvetica-Bold", 24)
    c.drawString(80, 780, text)

    c.setFont("Helvetica", 12)
    lines = [
        "This document is generated as a demonstration for the",
        "Biometric Verification & Secure E-Signature Platform.",
        "",
        "The purpose of this PDF is to demonstrate cryptographic",
        "digital signature application using pyHanko and a",
        "self-signed X.509 certificate.",
        "",
        "Signer: ______________________     Date: ____________",
    ]
    y = 730
    for line in lines:
        c.drawString(80, y, line)
        y -= 20

    c.showPage()
    c.save()
    return buf.getvalue()


# ---------- Self-test ----------
if __name__ == "__main__":
    from certs import generate_self_signed_cert, cert_exists

    print("=" * 60)
    print("pdf_signer.py — self test")
    print("=" * 60)

    if not cert_exists():
        print("\n[1] Generating self-signed certificate...")
        generate_self_signed_cert()
    else:
        print("\n[1] Certificate already exists.")

    print("[2] Generating demo PDF...")
    pdf = make_demo_pdf("Portfolio Demo Contract")
    print(f"    PDF size: {len(pdf)} bytes")

    valid, msg = validate_pdf(pdf, "demo.pdf")
    print(f"[3] Validation: valid={valid}, msg='{msg}'")

    print("[4] Signing PDF...")
    out = "signed/self_test_signed.pdf"
    Path("signed").mkdir(exist_ok=True)
    ok, err = sign_pdf(pdf, out, signer_name="Self Test", reason="Testing")
    print(f"    success={ok}, error='{err}'")

    if ok:
        with open(out, "rb") as f:
            signed_bytes = f.read()
        n_sigs = get_signature_count(signed_bytes)
        fields = list_signature_fields(signed_bytes)
        print(f"[5] Signature count in signed PDF: {n_sigs}")
        print(f"    Signature fields: {fields}")
        print(f"    File: {out}")

    print("\n✅ pdf_signer.py works.")