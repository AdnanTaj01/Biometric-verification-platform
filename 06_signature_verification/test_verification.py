"""End-to-end signature verification tests using generated fixtures."""
import shutil
from pathlib import Path


def setup_module(module):
    for d in ["data/certs", "data/fixtures"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)


def teardown_module(module):
    for d in ["data/certs", "data/fixtures"]:
        p = Path(d)
        if p.exists():
            shutil.rmtree(p)


def test_cert_generation():
    from certs import ensure_cert, cert_exists
    ensure_cert()
    assert cert_exists()


def test_fixtures_generated():
    from test_fixtures import (
        generate_all_fixtures, UNSIGNED_PATH, SIGNED_PATH, TAMPERED_PATH,
    )
    generate_all_fixtures(force=True)
    assert UNSIGNED_PATH.exists()
    assert SIGNED_PATH.exists()
    assert TAMPERED_PATH.exists()


def test_unsigned_pdf_returns_no_signature():
    from test_fixtures import UNSIGNED_PATH
    from verify import verify_pdf
    r = verify_pdf(UNSIGNED_PATH.read_bytes())
    assert r["overall"] == "NO_SIGNATURE"


def test_signed_pdf_without_trust_is_untrusted():
    from test_fixtures import SIGNED_PATH
    from verify import verify_pdf
    r = verify_pdf(SIGNED_PATH.read_bytes())
    assert r["overall"] == "UNTRUSTED"
    sig = r["signatures"][0]
    assert sig["intact"] is True
    assert sig["valid"] is True
    assert sig["trusted"] is False


def test_signed_pdf_with_trust_is_valid():
    from certs import CERT_PATH
    from test_fixtures import SIGNED_PATH
    from verify import verify_pdf
    r = verify_pdf(SIGNED_PATH.read_bytes(), trust_cert_path=str(CERT_PATH))
    assert r["overall"] == "VALID"


def test_tampered_pdf_detected_as_modified():
    from certs import CERT_PATH
    from test_fixtures import TAMPERED_PATH
    from verify import verify_pdf
    r = verify_pdf(TAMPERED_PATH.read_bytes(), trust_cert_path=str(CERT_PATH))
    assert r["overall"] == "MODIFIED"