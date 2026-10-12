"""
Test fixture generator for Project 6.

Creates three PDFs under data/fixtures/:
    1. unsigned.pdf    — plain PDF, no signature
    2. signed.pdf      — cryptographically signed with local test cert
    3. tampered.pdf    — signed PDF with one byte modified INSIDE
                         the signed range (breaks integrity)
"""
import io
from pathlib import Path

from pyhanko.sign import signers
from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4

from certs import KEY_PATH, CERT_PATH, ensure_cert


FIXTURES_DIR = Path("data/fixtures")
UNSIGNED_PATH = FIXTURES_DIR / "unsigned.pdf"
SIGNED_PATH = FIXTURES_DIR / "signed.pdf"
TAMPERED_PATH = FIXTURES_DIR / "tampered.pdf"


def _make_plain_pdf(title: str = "Portfolio Contract") -> bytes:
    """Generate a simple one-page PDF."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    c.setFont("Helvetica-Bold", 22)
    c.drawString(80, 780, title)

    c.setFont("Helvetica", 12)
    body = [
        "Project 6 — Signature Verification test fixture.",
        "",
        "This PDF is used to exercise the verification engine with:",
        "  - unsigned content (no signature)",
        "  - cryptographically signed content (valid signature)",
        "  - tampered content (signature becomes invalid)",
        "",
        "Signer: ______________________     Date: ____________",
    ]
    y = 730
    for line in body:
        c.drawString(80, y, line)
        y -= 18

    c.showPage()
    c.save()
    return buf.getvalue()


def _sign_pdf_bytes(pdf_bytes: bytes, signer_name: str = "Test Signer") -> bytes:
    """Sign PDF bytes using the local test cert."""
    ensure_cert()

    signer = signers.SimpleSigner.load(
        key_file=str(KEY_PATH),
        cert_file=str(CERT_PATH),
        key_passphrase=None,
    )

    reader = IncrementalPdfFileWriter(io.BytesIO(pdf_bytes))

    meta = signers.PdfSignatureMetadata(
        field_name="Signature1",
        reason="Test signature",
        location="Pakistan",
        name=signer_name,
    )

    out = io.BytesIO()
    signers.sign_pdf(reader, meta, signer=signer, output=out)
    return out.getvalue()


def _tamper_pdf_bytes(signed_bytes: bytes) -> bytes:
    """
    Simulate tampering by modifying an EXISTING byte inside the
    cryptographically-signed region.

    Why not append at the end?
    --------------------------
    PDF signatures use /ByteRange with exact offsets. Appending bytes
    after %%EOF does NOT change the covered content, so integrity
    checks still pass. Real tampering modifies content INSIDE the
    signed range.

    Strategy:
    ---------
    Modify a byte in the PDF header area (the binary comment
    that typically follows "%PDF-1.x\\n"). This byte is:
      - inside the first ByteRange segment
      - safe to change (no impact on PDF structure)
      - the file length stays identical, so ByteRange offsets
        remain valid — pyHanko can still parse the PDF.
    """
    if len(signed_bytes) < 40:
        return signed_bytes

    tampered = bytearray(signed_bytes)

    # The PDF header is "%PDF-1.x\n" followed by a binary comment
    # like "%âãÏÓ\n" (5 bytes of high-bit data). Those high-bit bytes
    # are safe to modify — they carry no structural meaning but ARE
    # inside the first ByteRange segment.
    for i in range(8, min(40, len(tampered))):
        if tampered[i] > 127:  # non-ASCII byte in the binary comment
            tampered[i] = (tampered[i] + 1) % 256
            return bytes(tampered)

    # Fallback: modify a byte at a fixed safe position inside the
    # first 100 bytes (avoids the "%PDF-" magic itself).
    for i in range(10, min(100, len(tampered))):
        if tampered[i] not in (0x0A, 0x0D, 0x25):  # not newline, not '%'
            tampered[i] = (tampered[i] + 1) % 256
            return bytes(tampered)

    # Last-resort fallback
    tampered[-1] = (tampered[-1] + 1) % 256
    return bytes(tampered)


def generate_all_fixtures(force: bool = False) -> dict:
    """Generate the three test fixtures."""
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    if force or not UNSIGNED_PATH.exists():
        unsigned_bytes = _make_plain_pdf("Portfolio Contract — Unsigned")
        UNSIGNED_PATH.write_bytes(unsigned_bytes)

    if force or not SIGNED_PATH.exists():
        plain = _make_plain_pdf("Portfolio Contract — Signed")
        signed = _sign_pdf_bytes(plain, signer_name="Test Signer (Project 6)")
        SIGNED_PATH.write_bytes(signed)

    if force or not TAMPERED_PATH.exists():
        signed = SIGNED_PATH.read_bytes()
        tampered = _tamper_pdf_bytes(signed)
        TAMPERED_PATH.write_bytes(tampered)

    return {
        "unsigned": UNSIGNED_PATH,
        "signed": SIGNED_PATH,
        "tampered": TAMPERED_PATH,
    }


def cleanup_fixtures():
    """Remove all generated fixtures."""
    for p in [UNSIGNED_PATH, SIGNED_PATH, TAMPERED_PATH]:
        if p.exists():
            p.unlink()


if __name__ == "__main__":
    print("=" * 60)
    print("test_fixtures.py — self test")
    print("=" * 60)

    if ensure_cert():
        print("\n[1] Generated fresh test certificate.")
    else:
        print("\n[1] Test certificate already valid.")

    print("[2] Generating test fixtures...")
    paths = generate_all_fixtures(force=True)
    for name, path in paths.items():
        size = path.stat().st_size
        print(f"    {name:10s} → {path}  ({size} bytes)")

    print("\n✅ test_fixtures.py works.")