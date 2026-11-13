"""Учебный самоподписанный сертификат для пилота HTTPS (НФТ-06)."""

from __future__ import annotations

import datetime
import ipaddress
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from app.config import settings


def make_certs(folder: Path | None = None) -> tuple[Path, Path]:
    target = folder or Path(settings.SSL_DIR)
    target.mkdir(parents=True, exist_ok=True)
    key_path = target / "alllove.key"
    cert_path = target / "alllove.crt"

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.utcnow()
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(minutes=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(
            x509.SubjectAlternativeName(
                [
                    x509.DNSName("localhost"),
                    x509.DNSName("logistics.alllove.local"),
                    x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
                ]
            ),
            critical=False,
        )
        .sign(key, hashes.SHA256())
    )
    key_path.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.chmod(0o600)
    return cert_path, key_path


if __name__ == "__main__":
    cert, key = make_certs()
    print("Сертификат:", cert)
    print("Ключ:", key)
    print("Запуск API: uvicorn app.main:app --port 8443 --ssl-certfile", cert, "--ssl-keyfile", key)
