"""Tests for cert generation and demo PDF generation (no actual signing)."""
from pathlib import Path


def setup_module(module):
    for f in ["certs/signing_key.pem", "certs/signing_cert.pem"]:
        p = Path(f)
        if p.exists():
            p.unlink()


def teardown_module(module):
    for f in ["certs/signing_key.pem", "certs/signing_cert.pem"]:
        p = Path(f)
        if p.exists():
            p.unlink()


def test_cert_generation():
    from certs import generate_self_signed_cert, cert_exists, load_cert_info
    assert not cert_exists()
    key, cert = generate_self_signed_cert(common_name="CI Test User")
    assert key.exists()
    assert cert.exists()
    assert cert_exists()

    info = load_cert_info()
    assert info["subject_cn"] == "CI Test User"
    assert info["is_self_signed"] is True


def test_demo_pdf_generation():
    from pdf_signer import make_demo_pdf, validate_pdf
    pdf = make_demo_pdf("CI Test Document")
    assert pdf.startswith(b"%PDF")
    ok, err = validate_pdf(pdf, "test.pdf")
    assert ok, err


def test_invalid_pdf_rejected():
    from pdf_signer import validate_pdf
    ok, err = validate_pdf(b"not a pdf", "fake.pdf")
    assert not ok