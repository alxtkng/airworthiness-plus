"""Verify RFC 3161 proof of existence for the synthetic G-EJKL signatures."""

import base64
import binascii
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.x509.oid import ExtendedKeyUsageOID

FORMAT = "Airworthiness+ Synthetic Reading Timestamps"
POLICY = "1.3.6.1.4.1.32473.1.1"
SHA256 = re.compile(r"[0-9a-f]{64}")
CLAIM_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
DISPLAY_TIME = re.compile(
    r"([A-Z][a-z]{2}) +([0-9]{1,2}) ([0-9]{2}:[0-9]{2}:[0-9]{2})"
    r"(\.[0-9]{1,6})? ([0-9]{4}) GMT"
)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class TimestampError(ValueError):
    """Trusted timestamp evidence did not pass a required verification check."""

    def __init__(self, outcome: str, message: str):
        self.outcome = outcome
        super().__init__(f"{outcome}: {message}")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, value in pairs:
        if field in result:
            raise TimestampError("Invalid", f"Duplicate timestamp envelope field {field}")
        result[field] = value
    return result


def _parse_envelope(content: bytes) -> dict[str, str]:
    try:
        obj = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise TimestampError("Invalid", "Timestamp envelope is not valid UTF-8 JSON") from error
    if (
        not isinstance(obj, dict)
        or obj.keys() != {"format", "version", "timestamps"}
        or obj["format"] != FORMAT
        or type(obj["version"]) is not int
        or obj["version"] != 1
    ):
        raise TimestampError("Invalid", "Unsupported timestamp envelope format or version")
    rows = obj["timestamps"]
    if not isinstance(rows, list) or len(rows) != 2:
        raise TimestampError("Invalid", "Expected exactly two timestamp responses")
    responses = {}
    for row in rows:
        if (
            not isinstance(row, dict)
            or row.keys() != {"record_id", "response"}
            or not isinstance(row["record_id"], str)
            or not row["record_id"]
        ):
            raise TimestampError("Invalid", "Timestamp response row has invalid fields")
        record_id, response = row["record_id"], row["response"]
        if record_id in responses or not isinstance(response, str):
            raise TimestampError("Invalid", "Duplicate record or invalid timestamp response")
        responses[record_id] = response
    return responses


def _b64(value: Any, label: str) -> bytes:
    try:
        if not isinstance(value, str):
            raise ValueError(label)
        raw = base64.b64decode(value, validate=True)
        if not raw or base64.b64encode(raw).decode("ascii") != value:
            raise ValueError(label)
        return raw
    except (ValueError, binascii.Error) as error:
        raise TimestampError("Invalid", f"{label} is not canonical base64") from error


def _check_der_sequence(payload: bytes) -> None:
    """Require exactly one DER object because OpenSSL may ignore trailing data."""
    if len(payload) < 2 or payload[0] != 0x30:
        raise TimestampError("Invalid", "Timestamp response is not a DER sequence")
    size = payload[1]
    header = 2
    if size >= 0x80:
        width = size & 0x7F
        if width == 0 or width > len(payload) - 2 or payload[2] == 0:
            raise TimestampError("Invalid", "Timestamp response has an invalid DER length")
        header += width
        size = int.from_bytes(payload[2:header], "big")
        if size < 128:
            raise TimestampError("Invalid", "Timestamp response has a noncanonical DER length")
    if header + size != len(payload):
        raise TimestampError("Invalid", "Timestamp response is truncated or has trailing data")


def _load_root(content: bytes) -> x509.Certificate:
    try:
        roots = x509.load_pem_x509_certificates(content)
        if len(roots) != 1:
            raise ValueError("Need one root")
        root = roots[0]
        if not root.extensions.get_extension_for_class(x509.BasicConstraints).value.ca:
            raise ValueError("Root needs CA basic constraints")
        root.verify_directly_issued_by(root)
        return root
    except (
        InvalidSignature,
        UnsupportedAlgorithm,
        ValueError,
        x509.DuplicateExtension,
        x509.ExtensionNotFound,
    ) as error:
        raise TimestampError(
            "Invalid", "Pinned TSA trust must contain one self-signed CA"
        ) from error


def _run(
    executable: str, args: list[str], environment: dict[str, str]
) -> subprocess.CompletedProcess[bytes]:
    try:
        # All options are fixed. File and directory arguments are created by the verifier.
        return subprocess.run(  # noqa: S603
            [executable, *args], capture_output=True, env=environment, timeout=15, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise TimestampError("Indeterminate", "The offline OpenSSL verifier failed") from error


def _one_field(report: str, field: str) -> str:
    prefix = field + ":"
    values = [
        line.removeprefix(prefix).strip() for line in report.splitlines() if line.startswith(prefix)
    ]
    if len(values) != 1:
        raise TimestampError("Invalid", f"Timestamp response has missing or ambiguous {field}")
    return values[0]


def _gen_time(report: str) -> datetime:
    if _one_field(report, "Status") != "Granted.":
        raise TimestampError("Invalid", "Timestamp response was not granted")
    if _one_field(report, "Policy OID") != POLICY:
        raise TimestampError("Inapplicable", "Timestamp response uses an unsupported TSA policy")
    if _one_field(report, "Hash Algorithm") != "sha256":
        raise TimestampError("Inapplicable", "Timestamp response does not use a SHA-256 imprint")
    match = DISPLAY_TIME.fullmatch(_one_field(report, "Time stamp"))
    if match is None or match[1] not in MONTHS:
        raise TimestampError("Invalid", "Timestamp response has an invalid genTime")
    month = MONTHS.index(match[1]) + 1
    try:
        return datetime.fromisoformat(
            f"{match[5]}-{month:02}-{int(match[2]):02}T{match[3]}{match[4] or ''}Z"
        )
    except ValueError as error:
        raise TimestampError("Invalid", "Timestamp response has an invalid genTime") from error


def _check_certificate_evidence(pem: bytes, root: x509.Certificate, gen_time: datetime) -> None:
    try:
        certificates = x509.load_pem_x509_certificates(pem)
        root_fingerprint = root.fingerprint(hashes.SHA256())
        leaves = []
        for cert in certificates:
            constraints = cert.extensions.get_extension_for_class(x509.BasicConstraints)
            if not constraints.value.ca:
                leaves.append(cert)
            elif cert.fingerprint(hashes.SHA256()) != root_fingerprint:
                raise TimestampError("Unknown", "Timestamp token includes a different TSA root")
        if len(leaves) != 1:
            raise TimestampError("Inapplicable", "Expected one embedded non-CA TSA signer")
        signer = leaves[0]
        usage = signer.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
        if not usage.critical or list(usage.value) != [ExtendedKeyUsageOID.TIME_STAMPING]:
            raise TimestampError(
                "Inapplicable", "TSA signer requires a critical timestamping-only EKU"
            )
        signer.verify_directly_issued_by(root)
    except TimestampError:
        raise
    except (x509.DuplicateExtension, x509.ExtensionNotFound) as error:
        raise TimestampError(
            "Inapplicable", "TSA certificate constraints are absent or ambiguous"
        ) from error
    except (InvalidSignature, UnsupportedAlgorithm, ValueError) as error:
        raise TimestampError(
            "Unknown", "Timestamp signer is outside the pinned TSA root"
        ) from error
    for cert in (root, signer):
        if not cert.not_valid_before_utc <= gen_time <= cert.not_valid_after_utc:
            raise TimestampError("Inapplicable", "TSA certificate was outside validity at genTime")


def _verify_token(
    executable: str,
    root: x509.Certificate,
    workspace: Path,
    environment: dict[str, str],
    libressl: bool,
    response: str,
    signature: bytes,
) -> datetime:
    der = _b64(response, "Timestamp response")
    _check_der_sequence(der)
    token = workspace / "response.tsr"
    token.write_bytes(der)
    inspect = ["ts", "-reply", "-in", str(token)]
    report = _run(executable, [*inspect, "-text"], environment)
    if report.returncode:
        raise TimestampError("Invalid", "OpenSSL could not parse the timestamp response")
    gen_time = _gen_time(report.stdout.decode("ascii", errors="replace"))
    extract = _run(executable, [*inspect, "-token_out"], environment)
    if extract.returncode:
        raise TimestampError("Invalid", "Timestamp response has no usable CMS token")
    cms = workspace / "token.p7"
    cms.write_bytes(extract.stdout)
    certificates = _run(
        executable, ["pkcs7", "-inform", "DER", "-in", str(cms), "-print_certs"], environment
    )
    if certificates.returncode:
        raise TimestampError("Invalid", "Timestamp response has unusable CMS certificates")
    _check_certificate_evidence(certificates.stdout, root, gen_time)

    trusted_paths = (
        ["-CApath", str(workspace / "empty")]
        if libressl
        else ["-no-CApath", "-no-CAstore", "-attime", str(int(gen_time.timestamp()))]
    )
    checked = _run(
        executable,
        [
            "ts",
            "-verify",
            "-in",
            str(token),
            "-digest",
            hashlib.sha256(signature).hexdigest(),
            "-CAfile",
            str(workspace / "pinned.pem"),
            *trusted_paths,
        ],
        environment,
    )
    if checked.returncode:
        raise TimestampError(
            "Invalid", "RFC 3161 verification failed against the exact signature and pinned root"
        )
    return gen_time


def _read_signature(row: dict[str, Any]) -> tuple[str, bytes, datetime]:
    try:
        record_id, signed_at = row["claim"]["record_id"], row["claim"]["signed_at"]
        signature = _b64(row["signature"], "Ed25519 signature")
        if (
            not isinstance(record_id, str)
            or not record_id
            or len(signature) != 64
            or not isinstance(signed_at, str)
            or not CLAIM_TIME.fullmatch(signed_at)
        ):
            raise ValueError("Invalid signature row")
        return record_id, signature, datetime.fromisoformat(signed_at)
    except TimestampError:
        raise
    except (KeyError, TypeError, ValueError) as error:
        raise TimestampError("Invalid", "Verified reading signature row is malformed") from error


def verify_timestamps(
    signatures: list[dict[str, Any]],
    timestamp_content: bytes,
    tsa_root_pem: bytes,
    expected_root_sha256: str,
) -> dict[str, Any]:
    """Independently verify time of existence for the verified reading signatures."""
    if not isinstance(expected_root_sha256, str) or not SHA256.fullmatch(expected_root_sha256):
        raise TimestampError(
            "Indeterminate", "A separately supplied TSA root SHA-256 pin is required"
        )
    actual_pin = hashlib.sha256(tsa_root_pem).hexdigest()
    if not hmac.compare_digest(actual_pin, expected_root_sha256):
        raise TimestampError("Invalid", "TSA root digest differs from the separately supplied pin")
    root = _load_root(tsa_root_pem)
    responses = _parse_envelope(timestamp_content)
    if len(signatures) != 2:
        raise TimestampError(
            "Invalid", "Expected a verified original and correction signature pair"
        )
    claims = [_read_signature(row) for row in signatures]
    if {record_id for record_id, _, _ in claims} != set(responses):
        raise TimestampError("Invalid", "Timestamp record IDs differ from the signed reading pair")
    executable = shutil.which("openssl")
    if executable is None:
        raise TimestampError("Indeterminate", "An offline OpenSSL verifier is unavailable")
    with TemporaryDirectory(prefix="aw-tsa-verify-") as directory:
        workspace = Path(directory)
        (workspace / "empty").mkdir()
        (workspace / "pinned.pem").write_bytes(tsa_root_pem)
        environment = {
            "LC_ALL": "C",
            "OPENSSL_CONF": os.devnull,
            "SSL_CERT_DIR": str(workspace / "empty"),
            "SSL_CERT_FILE": str(workspace / "pinned.pem"),
        }
        version = _run(executable, ["version"], environment)
        libressl = version.stdout.startswith(b"LibreSSL ")
        if version.returncode or (not libressl and not version.stdout.startswith(b"OpenSSL 3.")):
            raise TimestampError(
                "Indeterminate", "Timestamp verification requires LibreSSL or OpenSSL 3"
            )
        timestamps = []
        previous = None
        for record_id, signature, signed_at in claims:
            response = responses[record_id]
            gen_time = _verify_token(
                executable, root, workspace, environment, libressl, response, signature
            )
            if gen_time < signed_at or (previous is not None and gen_time < previous):
                raise TimestampError(
                    "Invalid", "Trusted genTime conflicts with the signed reading chronology"
                )
            previous = gen_time
            timestamps.append(
                {
                    "record_id": record_id,
                    "gen_time": gen_time.isoformat().replace("+00:00", "Z"),
                    "response": response,
                }
            )
    return {
        "tsa_root_sha256": actual_pin,
        "trusted_timestamps": timestamps,
        "timestamp_assurance": (
            "The exact signature existed by each verified RFC 3161 genTime. "
            "The signing instant remains signer-asserted."
        ),
    }
