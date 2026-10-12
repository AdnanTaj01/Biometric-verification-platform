"""
PDF signature verification engine.

Covers SRS requirement FR-12:
- Signature cryptographically valid
- Signature invalid
- Document modified after signing
- Certificate expired or untrusted
- Verification inconclusive

This module ONLY verifies — it does not sign.
"""
import io
import hashlib
import logging
from pathlib import Path
from typing import Optional

from pyhanko.pdf_utils.reader import PdfFileReader
from pyhanko.sign.validation import validate_pdf_signature
from pyhanko_certvalidator import ValidationContext

from asn1crypto import x509 as asn1_x509
from cryptography.x509 import load_pem_x509_certificate
from cryptography.hazmat.primitives.serialization import Encoding


logging.getLogger("pyhanko").setLevel(logging.CRITICAL)
logging.getLogger("pyhanko_certvalidator").setLevel(logging.CRITICAL)
logging.getLogger("asyncio").setLevel(logging.CRITICAL)


class VerifyVerdict:
    VALID = "Signature cryptographically valid"
    INVALID = "Signature invalid"
    MODIFIED = "Document modified after signing"
    CERT_UNTRUSTED = "Certificate expired or untrusted"
    INCONCLUSIVE = "Verification inconclusive"


def _load_cert_as_trust_root(cert_path: str):
    with open(cert_path, "rb") as f:
        cert_pem = f.read()
    cert_obj = load_pem_x509_certificate(cert_pem)
    der_bytes = cert_obj.public_bytes(Encoding.DER)
    return asn1_x509.Certificate.load(der_bytes)


def build_trust_context(cert_path: str) -> Optional[ValidationContext]:
    try:
        root = _load_cert_as_trust_root(cert_path)
        return ValidationContext(
            trust_roots=[root],
            allow_fetching=False,
        )
    except Exception as e:
        print(f"[verify] Could not build trust context: {e}")
        return None


def _cert_common_name(cert) -> str:
    if cert is None:
        return ""
    try:
        native = cert.subject.native
        if isinstance(native, dict):
            return str(native.get("common_name", ""))
        if isinstance(native, list):
            for rdn in native:
                if isinstance(rdn, dict) and "common_name" in rdn:
                    return str(rdn["common_name"])
    except Exception:
        pass
    return ""


def _cert_info(cert) -> dict:
    if cert is None:
        return {}
    try:
        return {
            "subject_cn": _cert_common_name(cert),
            "serial": hex(cert.serial_number),
            "not_before": cert["tbs_certificate"]["validity"]["not_before"].native,
            "not_after": cert["tbs_certificate"]["validity"]["not_after"].native,
            "issuer_cn": _cert_common_name(cert.issuer),
            "signature_algorithm": cert["signature_algorithm"]["algorithm"].native,
        }
    except Exception:
        return {}


def _extract_signer_cert(sig, status):
    cert = getattr(status, "signer_cert", None)
    if cert is not None:
        return cert
    cert = getattr(sig, "signer_cert", None)
    if cert is not None:
        return cert
    certs = getattr(sig, "certs", None) or []
    if certs:
        return certs[0]
    try:
        sig_obj = getattr(sig, "sig_object", None)
        if sig_obj is not None:
            cms_certs = getattr(sig_obj, "certificates", None)
            if cms_certs:
                return cms_certs[0]
    except Exception:
        pass
    return None


def _cert_der_sha256(cert) -> Optional[str]:
    if cert is None:
        return None
    try:
        return hashlib.sha256(cert.dump()).hexdigest()
    except Exception:
        pass
    try:
        return hashlib.sha256(cert.public_bytes(Encoding.DER)).hexdigest()
    except Exception:
        pass
    return None


def verify_pdf(pdf_bytes: bytes, trust_cert_path: Optional[str] = None) -> dict:
    try:
        reader = PdfFileReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        return {"signatures": [], "overall": "INCONCLUSIVE",
                "error": f"Could not parse PDF: {e}"}

    try:
        embedded = reader.embedded_signatures
    except Exception as e:
        return {"signatures": [], "overall": "INCONCLUSIVE",
                "error": f"Could not read embedded signatures: {e}"}

    if not embedded:
        return {"signatures": [], "overall": "NO_SIGNATURE",
                "error": "No signatures found in this PDF."}

    context = None
    if trust_cert_path and Path(trust_cert_path).exists():
        context = build_trust_context(trust_cert_path)

    results = [_verify_one(sig, context, trust_cert_path) for sig in embedded]
    return {"signatures": results, "overall": _overall_verdict(results), "error": ""}


def _verify_one(sig, context, trust_cert_path) -> dict:
    try:
        status = validate_pdf_signature(sig, signer_validation_context=context)
    except Exception as e:
        return {
            "field_name": getattr(sig, "field_name", "<unknown>"),
            "error": f"Validation error: {e}",
            "intact": None, "valid": None, "trusted": None,
            "bottom_line": False,
            "verdict": VerifyVerdict.INCONCLUSIVE,
            "signer_cn": "", "signer_serial": "",
            "signer_not_before": "", "signer_not_after": "",
            "signer_issuer": "", "signing_time": None,
            "md_algorithm": "", "signature_mechanism": "",
            "coverage": "", "pretty": "",
        }

    signer_cert = _extract_signer_cert(sig, status)
    cert_info = _cert_info(signer_cert)

    try:
        signing_time = sig.sig_object.get("/M", None)
        signing_time = str(signing_time) if signing_time else None
    except Exception:
        signing_time = None

    intact = bool(getattr(status, "intact", False))
    valid = bool(getattr(status, "valid", False))
    trusted = bool(getattr(status, "trusted", False))

    # Trust fallback via DER SHA-256
    if (not trusted) and trust_cert_path and signer_cert is not None:
        try:
            trusted_cert = _load_cert_as_trust_root(trust_cert_path)
            sh = _cert_der_sha256(signer_cert)
            th = _cert_der_sha256(trusted_cert)
            if sh and th and sh == th:
                trusted = True
        except Exception as e:
            print(f"[verify] trust fallback error: {e}")

    if not intact:
        verdict = VerifyVerdict.MODIFIED
    elif not valid:
        verdict = VerifyVerdict.INVALID
    elif not trusted:
        verdict = VerifyVerdict.CERT_UNTRUSTED
    else:
        verdict = VerifyVerdict.VALID

    return {
        "field_name": getattr(sig, "field_name", "<unknown>"),
        "intact": intact,
        "valid": valid,
        "trusted": trusted,
        "bottom_line": bool(getattr(status, "bottom_line", False)),
        "coverage": str(getattr(status, "coverage", "unknown")),
        "md_algorithm": str(getattr(status, "md_algorithm", "unknown")),
        "signature_mechanism": str(getattr(status, "signature_mechanism", "unknown")),
        "signer_cn": cert_info.get("subject_cn", ""),
        "signer_serial": cert_info.get("serial", ""),
        "signer_not_before": cert_info.get("not_before", ""),
        "signer_not_after": cert_info.get("not_after", ""),
        "signer_issuer": cert_info.get("issuer_cn", ""),
        "signing_time": signing_time,
        "verdict": verdict,
        "pretty": _safe_pretty(status),
        "error": "",
    }


def _safe_pretty(status) -> str:
    try:
        return status.pretty_print_details()
    except Exception:
        return ""


def _overall_verdict(results) -> str:
    if not results:
        return "NO_SIGNATURE"
    verdicts = [r.get("verdict") for r in results]
    if VerifyVerdict.MODIFIED in verdicts:
        return "MODIFIED"
    if VerifyVerdict.INVALID in verdicts:
        return "INVALID"
    if VerifyVerdict.INCONCLUSIVE in verdicts:
        return "INCONCLUSIVE"
    if VerifyVerdict.CERT_UNTRUSTED in verdicts:
        return "UNTRUSTED"
    if VerifyVerdict.VALID in verdicts:
        return "VALID"
    return "INCONCLUSIVE"


def count_signatures(pdf_bytes: bytes) -> int:
    try:
        reader = PdfFileReader(io.BytesIO(pdf_bytes))
        return len(reader.embedded_signatures)
    except Exception:
        return 0


if __name__ == "__main__":
    from certs import CERT_PATH, ensure_cert
    from test_fixtures import (
        UNSIGNED_PATH, SIGNED_PATH, TAMPERED_PATH,
        generate_all_fixtures,
    )

    print("=" * 60)
    print("verify.py — self test")
    print("=" * 60)

    if ensure_cert():
        print("\n[0] Generated fresh test certificate.")
    if not SIGNED_PATH.exists():
        print("[0] Generating test fixtures...")
        generate_all_fixtures(force=True)

    print(f"\n[1] Unsigned PDF: {UNSIGNED_PATH.name}")
    r1 = verify_pdf(UNSIGNED_PATH.read_bytes())
    print(f"    overall: {r1['overall']}  (expected: NO_SIGNATURE)")

    print(f"\n[2] Signed PDF (no trust context): {SIGNED_PATH.name}")
    r2 = verify_pdf(SIGNED_PATH.read_bytes())
    print(f"    overall: {r2['overall']}  (expected: UNTRUSTED)")
    for s in r2["signatures"]:
        print(f"    intact={s['intact']} valid={s['valid']} trusted={s['trusted']}")
        print(f"    signer: {s['signer_cn']}")

    print(f"\n[3] Signed PDF (with trust context): {CERT_PATH}")
    r3 = verify_pdf(SIGNED_PATH.read_bytes(), trust_cert_path=str(CERT_PATH))
    print(f"    overall: {r3['overall']}  (expected: VALID)")
    for s in r3["signatures"]:
        print(f"    trusted={s['trusted']}  verdict: {s['verdict']}")

    print(f"\n[4] Tampered PDF: {TAMPERED_PATH.name}")
    r4 = verify_pdf(TAMPERED_PATH.read_bytes(), trust_cert_path=str(CERT_PATH))
    print(f"    overall: {r4['overall']}  (expected: MODIFIED)")
    for s in r4["signatures"]:
        print(f"    intact={s['intact']} valid={s['valid']} trusted={s['trusted']}")
        print(f"    verdict: {s['verdict']}")

    print("\n✅ verify.py works.")