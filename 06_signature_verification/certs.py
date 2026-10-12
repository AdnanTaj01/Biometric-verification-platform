"""
Local test certificate generator for Project 6.

Creates a self-signed cert used ONLY for generating test fixtures.
Self-heals corrupted files (deletes and regenerates).
"""
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


CERTS_DIR = Path("data/certs")
KEY_PATH = CERTS_DIR / "test_key.pem"
CERT_PATH = CERTS_DIR / "test_cert.pem"


def _is_valid_pem(path: Path, kind: str) -> bool:
    """Check whether a file is a valid PEM of the given kind."""
    if not path.exists():
        return False
    try:
        if path.stat().st_size < 100:
            return False
        data = path.read_bytes()
        if kind == "key":
            serialization.load_pem_private_key(data, password=None)
        else:
            x509.load_pem_x509_certificate(data)
        return True
    except Exception:
        return False


def generate_test_cert(
    common_name: str = "Test Signer (Project 6)",
    org: str = "Verification Portfolio",
    country: str = "PK",
    valid_days: int = 365,
    key_size: int = 2048,
) -> tuple:
    """Generate a self-signed RSA key + X.509 certificate for testing."""
    CERTS_DIR.mkdir(parents=True, exist_ok=True)

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=key_size,
    )

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, country),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, org),
        x509.NameAttribute(NameOID.COMMON_NAME, common_name),
    ])

    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=valid_days))
        .add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .sign(private_key, hashes.SHA256())
    )

    KEY_PATH.write_bytes(
        private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    CERT_PATH.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

    return KEY_PATH, CERT_PATH


def cert_exists() -> bool:
    """
    Check whether a VALID key + cert pair exists.
    Returns False if either file is missing, empty, or corrupted.
    """
    return _is_valid_pem(KEY_PATH, "key") and _is_valid_pem(CERT_PATH, "cert")


def ensure_cert():
    """
    Ensure a valid cert + key pair exists. If files are corrupted,
    delete them and regenerate. Returns True if regeneration happened.
    """
    if cert_exists():
        return False

    # Delete anything left over
    if KEY_PATH.exists():
        KEY_PATH.unlink()
    if CERT_PATH.exists():
        CERT_PATH.unlink()

    generate_test_cert()
    return True


def load_cert_info() -> dict:
    """Load certificate metadata for UI display."""
    if not cert_exists():
        return {}

    cert = x509.load_pem_x509_certificate(CERT_PATH.read_bytes())

    def _name_attr(name, oid):
        try:
            return name.get_attributes_for_oid(oid)[0].value
        except IndexError:
            return ""

    return {
        "subject_cn": _name_attr(cert.subject, NameOID.COMMON_NAME),
        "subject_org": _name_attr(cert.subject, NameOID.ORGANIZATION_NAME),
        "subject_country": _name_attr(cert.subject, NameOID.COUNTRY_NAME),
        "issuer_cn": _name_attr(cert.issuer, NameOID.COMMON_NAME),
        "serial": hex(cert.serial_number),
        "not_before": cert.not_valid_before_utc,
        "not_after": cert.not_valid_after_utc,
        "is_self_signed": cert.subject == cert.issuer,
    }


def delete_cert():
    """Remove local test cert (for regeneration)."""
    if KEY_PATH.exists():
        KEY_PATH.unlink()
    if CERT_PATH.exists():
        CERT_PATH.unlink()


if __name__ == "__main__":
    if ensure_cert():
        print("Generated fresh test certificate (old was missing or corrupted).")
    else:
        print("Test certificate already exists and is valid.")

    print("\nCertificate info:")
    for k, v in load_cert_info().items():
        print(f"  {k}: {v}")

    print("\n✅ certs.py works.")