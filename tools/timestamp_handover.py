"""Issue local RFC 3161 responses for the synthetic handover rehearsal."""

import base64
import os
import secrets
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

FORMAT = "Airworthiness+ Synthetic Reading Timestamps"
POLICY_OID = "1.3.6.1.4.1.32473.1.1"

_CONFIGURATION = f"""\
[tsa]
default_tsa = rehearsal
[rehearsal]
serial = serial
crypto_device = builtin
signer_cert = tsa.pem
certs = root.pem
signer_key = tsa.key
signer_digest = sha256
default_policy = {POLICY_OID}
digests = sha256
ordering = no
tsa_name = yes
ess_cert_id_chain = no
"""


@dataclass(frozen=True)
class SyntheticTimestampAuthority:
    """A rehearsal trust anchor and its dedicated, ephemeral timestamp signer."""

    root_pem: bytes
    workdir: Path
    _root_key: rsa.RSAPrivateKey = field(repr=False)
    _leaf_pem: bytes = field(repr=False)
    _leaf_key: rsa.RSAPrivateKey = field(repr=False)
    _openssl: str = field(repr=False)


def _name(common_name: str) -> x509.Name:
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])


def _usage(*, ca: bool) -> x509.KeyUsage:
    return x509.KeyUsage(
        digital_signature=not ca,
        content_commitment=False,
        key_encipherment=False,
        data_encipherment=False,
        key_agreement=False,
        key_cert_sign=ca,
        crl_sign=ca,
        encipher_only=False,
        decipher_only=False,
    )


def make_timestamp_authority(workdir: Path) -> SyntheticTimestampAuthority:
    """Create a synthetic root and dedicated TSA leaf using the current UTC clock.

    Keep keys in memory. Supply an existing disposable work directory for the
    private temporary directories needed by the local OpenSSL CLI.
    """
    openssl = shutil.which("openssl")
    if openssl is None:
        raise RuntimeError("The synthetic timestamp authority requires local OpenSSL")
    if not workdir.is_dir():
        raise ValueError("Supply an existing disposable timestamp work directory")

    now = datetime.now(UTC)
    root_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    leaf_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    root_name = _name("Airworthiness+ Synthetic Handover Timestamp Root")
    leaf_name = _name("Airworthiness+ Synthetic Handover Timestamp Authority")
    root = (
        x509.CertificateBuilder()
        .subject_name(root_name)
        .issuer_name(root_name)
        .public_key(root_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(_usage(ca=True), critical=True)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(root_key.public_key()), critical=False
        )
        .sign(root_key, hashes.SHA256())
    )
    leaf = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(root_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(_usage(ca=False), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.TIME_STAMPING]), critical=True)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()),
            critical=False,
        )
        .sign(root_key, hashes.SHA256())
    )
    return SyntheticTimestampAuthority(
        root_pem=root.public_bytes(serialization.Encoding.PEM),
        workdir=workdir.resolve(),
        _root_key=root_key,
        _leaf_pem=leaf.public_bytes(serialization.Encoding.PEM),
        _leaf_key=leaf_key,
        _openssl=openssl,
    )


def _crl_time(moment: datetime) -> datetime:
    if moment.utcoffset() is None:
        raise ValueError("CRL fixture times must be timezone-aware")
    return moment.astimezone(UTC).replace(microsecond=0)


def make_timestamp_crl(
    authority: SyntheticTimestampAuthority,
    *,
    last_update: datetime,
    next_update: datetime,
    revoked_at: datetime | None = None,
    invalidity_date: datetime | None = None,
    reason: x509.ReasonFlags | None = x509.ReasonFlags.cessation_of_operation,
) -> bytes:
    """Build a complete PEM CRL for one counterfactual synthetic status scenario.

    The CRL covers the TSA leaf issued by this root. Times are explicitly
    supplied, including for future-dated replay fixtures. No private key is
    exported with the result. Use reason=None to omit the entry extension.
    """
    last_update, next_update = _crl_time(last_update), _crl_time(next_update)
    if last_update >= next_update:
        raise ValueError("CRL nextUpdate must follow thisUpdate")
    if revoked_at is None and invalidity_date is not None:
        raise ValueError("An invalidity date requires a revoked TSA leaf")

    root = x509.load_pem_x509_certificate(authority.root_pem)
    builder = (
        x509.CertificateRevocationListBuilder()
        .issuer_name(root.subject)
        .last_update(last_update)
        .next_update(next_update)
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(authority._root_key.public_key()),
            critical=False,
        )
        .add_extension(x509.CRLNumber(1), critical=False)
    )
    if revoked_at is not None:
        revoked_at = _crl_time(revoked_at)
        if revoked_at > last_update:
            raise ValueError("A revocation listed in the CRL cannot follow thisUpdate")
        leaf = x509.load_pem_x509_certificate(authority._leaf_pem)
        entry = (
            x509.RevokedCertificateBuilder()
            .serial_number(leaf.serial_number)
            .revocation_date(revoked_at)
        )
        if reason is not None:
            entry = entry.add_extension(x509.CRLReason(reason), critical=False)
        if invalidity_date is not None:
            invalidity_date = _crl_time(invalidity_date)
            if invalidity_date > revoked_at:
                raise ValueError("The invalidity date cannot follow the revocation date")
            entry = entry.add_extension(x509.InvalidityDate(invalidity_date), critical=False)
        builder = builder.add_revoked_certificate(entry.build())
    crl = builder.sign(authority._root_key, hashes.SHA256())
    return crl.public_bytes(serialization.Encoding.PEM)


def _run(authority: SyntheticTimestampAuthority, directory: Path, *arguments: str) -> None:
    result = subprocess.run(  # noqa: S603
        [authority._openssl, "ts", *arguments],
        cwd=directory,
        env={"LC_ALL": "C", "OPENSSL_CONF": os.devnull},
        capture_output=True,
        timeout=15,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"Local timestamp {arguments[0]} failed: {result.stderr.decode().strip()}"
        )


def issue_timestamp(authority: SyntheticTimestampAuthority, signature_bytes: bytes) -> bytes:
    """Return a DER TimeStampResp covering the exact raw Ed25519 signature bytes."""
    if not isinstance(signature_bytes, bytes) or len(signature_bytes) != 64:
        raise ValueError("Timestamping requires exactly 64 raw Ed25519 signature bytes")
    with TemporaryDirectory(prefix="synthetic-tsa-", dir=authority.workdir) as temporary:
        directory = Path(temporary)
        (directory / "root.pem").write_bytes(authority.root_pem)
        (directory / "empty-ca").mkdir()
        (directory / "tsa.pem").write_bytes(authority._leaf_pem)
        key = directory / "tsa.key"
        key.touch(mode=0o600)
        key.write_bytes(
            authority._leaf_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
        (directory / "tsa.cnf").write_text(_CONFIGURATION, encoding="ascii")
        # Per-response independent random serial seeds avoid shared state on concurrent calls.
        (directory / "serial").write_text(secrets.token_hex(16) + "\n", encoding="ascii")
        (directory / "signature.bin").write_bytes(signature_bytes)
        _run(
            authority,
            directory,
            "-query",
            "-data",
            "signature.bin",
            "-sha256",
            "-cert",
            "-out",
            "request.tsq",
        )
        _run(
            authority,
            directory,
            "-reply",
            "-config",
            "tsa.cnf",
            "-queryfile",
            "request.tsq",
            "-out",
            "response.tsr",
        )
        _run(
            authority,
            directory,
            "-verify",
            "-queryfile",
            "request.tsq",
            "-in",
            "response.tsr",
            "-CAfile",
            "root.pem",
            "-CApath",
            "empty-ca",
        )
        return (directory / "response.tsr").read_bytes()


def timestamp_signature(
    authority: SyntheticTimestampAuthority, signature: dict[str, Any]
) -> dict[str, str]:
    """Timestamp a detached signature and retain its existing claim's record ID."""
    try:
        record_id = signature["claim"]["record_id"]
        encoded = signature["signature"]
        if not isinstance(record_id, str) or not record_id.strip() or not isinstance(encoded, str):
            raise ValueError
        raw = base64.b64decode(encoded, validate=True)
        if base64.b64encode(raw).decode("ascii") != encoded:
            raise ValueError
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(
            "Expected a record ID and a canonical Base64 detached signature"
        ) from error
    response = issue_timestamp(authority, raw)
    return {"record_id": record_id, "response": base64.b64encode(response).decode("ascii")}


def timestamp_envelope(
    authority: SyntheticTimestampAuthority, signatures: list[dict[str, Any]]
) -> dict[str, Any]:
    """Timestamp a list of retained detached signatures and return the transfer envelope."""
    return {
        "format": FORMAT,
        "version": 1,
        "timestamps": [timestamp_signature(authority, signature) for signature in signatures],
    }
