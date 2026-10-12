"""
Self-signed X.509 certificate generator for PDF signing.

Generates:
    certs/signing_key.pem      — private key (KEEP SECRET, server-side only)
    certs/signing_cert.pem     — X.509 certificate (public)

Covers FR-11: cryptographic signing requires appropriate signing key and certificate.
"""
import datetime
from pathlib import Path

from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa


CERTS_DIR = Path("certs")
KEY_PATH = CERTS_DIR / "signing_key.pem"
CERT_PATH = CERTS_DIR / "signing_cert.pem"


def generate_self_signed_cert(
    common_name: str = "M Adnan Taj",
    org: str = "Biometric Verification Portfolio",
    country: str = "PK",
    valid_days: int = 365,
    key_size: int = 2048,
) -> tuple:
    """Generate a self-signed RSA key + X.509 certificate."""
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
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
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
    return KEY_PATH.exists() and CERT_PATH.exists()


def load_cert_info() -> dict:
    """Load certificate metadata for UI display."""
    if not CERT_PATH.exists():
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
    if KEY_PATH.exists():
        KEY_PATH.unlink()
    if CERT_PATH.exists():
        CERT_PATH.unlink()


if __name__ == "__main__":
    print("Generating self-signed certificate...")
    key_path, cert_path = generate_self_signed_cert(
        common_name="Test Signer",
        org="Portfolio Demo",
    )
    print(f"✅ Key:  {key_path}")
    print(f"✅ Cert: {cert_path}")

    print("\nCertificate info:")
    info = load_cert_info()
    for k, v in info.items():
        print(f"  {k}: {v}")

    print("\n✅ certs.py works.")