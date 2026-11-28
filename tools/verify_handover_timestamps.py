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
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from cryptography import x509
from cryptography.exceptions import InvalidSignature, UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.x509.oid import CRLEntryExtensionOID, ExtendedKeyUsageOID, ExtensionOID

FORMAT = "Airworthiness+ Synthetic Reading Timestamps"
POLICY = "1.3.6.1.4.1.32473.1.1"
SHA256 = re.compile(r"[0-9a-f]{64}")
CLAIM_TIME = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z")
EVALUATION_TIME = re.compile(CLAIM_TIME.pattern.removesuffix("Z") + r"(?:\.[0-9]{1,6})?Z")
UNSUPPORTED_CRL_EXTENSIONS = {
    ExtensionOID.DELTA_CRL_INDICATOR,
    ExtensionOID.FRESHEST_CRL,
    ExtensionOID.ISSUING_DISTRIBUTION_POINT,
}
POST_GENTIME_REASONS = {
    x509.ReasonFlags.unspecified,
    x509.ReasonFlags.affiliation_changed,
    x509.ReasonFlags.superseded,
    x509.ReasonFlags.cessation_of_operation,
}
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


@dataclass(frozen=True)
class _VerifiedSigner:
    record_id: str
    gen_time: datetime
    certificate: x509.Certificate
    accuracy_unspecified: bool


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


def _check_certificate_evidence(
    pem: bytes, root: x509.Certificate, gen_time: datetime
) -> x509.Certificate:
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
    return signer


def _verify_token(
    executable: str,
    root: x509.Certificate,
    workspace: Path,
    environment: dict[str, str],
    libressl: bool,
    response: str,
    signature: bytes,
) -> tuple[datetime, x509.Certificate, bool]:
    der = _b64(response, "Timestamp response")
    _check_der_sequence(der)
    token = workspace / "response.tsr"
    token.write_bytes(der)
    inspect = ["ts", "-reply", "-in", str(token)]
    report = _run(executable, [*inspect, "-text"], environment)
    if report.returncode:
        raise TimestampError("Invalid", "OpenSSL could not parse the timestamp response")
    rendered = report.stdout.decode("ascii", errors="replace")
    gen_time = _gen_time(rendered)
    accuracy_unspecified = _one_field(rendered, "Accuracy") == "unspecified"
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
    signer = _check_certificate_evidence(certificates.stdout, root, gen_time)

    historical_time = [] if libressl else ["-attime", str(int(gen_time.timestamp()))]
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
            "-CApath",
            str(workspace / "empty"),
            *historical_time,
        ],
        environment,
    )
    if checked.returncode:
        raise TimestampError(
            "Invalid", "RFC 3161 verification failed against the exact signature and pinned root"
        )
    return gen_time, signer, accuracy_unspecified


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


def _utc_label(instant: datetime) -> str:
    return instant.isoformat().replace("+00:00", "Z")


def _read_evaluation(value: str) -> datetime:
    if not isinstance(value, str) or not EVALUATION_TIME.fullmatch(value):
        raise TimestampError(
            "Indeterminate", "TSA status evaluation requires an explicit UTC instant"
        )
    try:
        return datetime.fromisoformat(value)
    except ValueError as error:
        raise TimestampError("Indeterminate", "TSA status evaluation instant is invalid") from error


def _effective_revocation(
    entry: x509.RevokedCertificate,
) -> tuple[datetime, x509.ReasonFlags | None]:
    for extension in entry.extensions:
        if extension.oid == CRLEntryExtensionOID.CERTIFICATE_ISSUER:
            raise TimestampError("Indeterminate", "Indirect TSA CRL entries are unsupported")
        if extension.critical and extension.oid not in {
            CRLEntryExtensionOID.CRL_REASON,
            CRLEntryExtensionOID.INVALIDITY_DATE,
        }:
            raise TimestampError(
                "Indeterminate", "TSA CRL entry has an unsupported critical extension"
            )
    try:
        reason = entry.extensions.get_extension_for_class(x509.CRLReason).value.reason
    except x509.ExtensionNotFound:
        reason = None
    if reason == x509.ReasonFlags.remove_from_crl:
        raise TimestampError("Indeterminate", "TSA CRL contains a delta-only removal entry")
    try:
        invalidity = entry.extensions.get_extension_for_class(x509.InvalidityDate).value
    except x509.ExtensionNotFound:
        return entry.revocation_date_utc, reason
    return min(entry.revocation_date_utc, invalidity.invalidity_date_utc), reason


def _read_crl(
    content: bytes, root: x509.Certificate, evaluated_at: datetime
) -> tuple[datetime, datetime, dict[int, tuple[datetime, x509.ReasonFlags | None]]]:
    try:
        pem = content.strip()
        if not re.fullmatch(
            rb"-----BEGIN X509 CRL-----[\r\n]+[A-Za-z0-9+/=\r\n]+-----END X509 CRL-----", pem
        ):
            raise ValueError("Expected one PEM CRL")
        crl = x509.load_pem_x509_crl(pem)
        public_key = root.public_key()
        key_usage = root.extensions.get_extension_for_class(x509.KeyUsage).value
        if (
            crl.issuer != root.subject
            or not isinstance(public_key, RSAPublicKey)
            or not key_usage.crl_sign
            or not crl.is_signature_valid(public_key)
        ):
            raise TimestampError(
                "Indeterminate", "TSA CRL was not authenticated by the pinned RSA root"
            )
        for extension in crl.extensions:
            if extension.oid in UNSUPPORTED_CRL_EXTENSIONS:
                raise TimestampError(
                    "Indeterminate", "Delta, indirect or scoped TSA CRLs are unsupported"
                )
            if extension.critical and extension.oid not in {
                ExtensionOID.AUTHORITY_KEY_IDENTIFIER,
                ExtensionOID.CRL_NUMBER,
            }:
                raise TimestampError(
                    "Indeterminate", "TSA CRL has an unsupported critical extension"
                )
        last_update, next_update = crl.last_update_utc, crl.next_update_utc
        if next_update is None or not last_update <= evaluated_at < next_update:
            raise TimestampError("Indeterminate", "TSA CRL does not cover the evaluation instant")
        if not root.not_valid_before_utc <= last_update <= root.not_valid_after_utc:
            raise TimestampError("Indeterminate", "TSA CRL issuance is outside issuer validity")
        effective_dates = {}
        for entry in crl:
            if entry.revocation_date_utc > last_update:
                raise TimestampError("Indeterminate", "TSA CRL lists a revocation after issuance")
            if entry.serial_number in effective_dates:
                raise TimestampError(
                    "Indeterminate", "TSA CRL contains duplicate certificate entries"
                )
            effective_dates[entry.serial_number] = _effective_revocation(entry)
        return last_update, next_update, effective_dates
    except TimestampError:
        raise
    except (
        InvalidSignature,
        UnsupportedAlgorithm,
        ValueError,
        x509.DuplicateExtension,
        x509.ExtensionNotFound,
        x509.UnsupportedGeneralNameType,
    ) as error:
        raise TimestampError("Indeterminate", "TSA CRL evidence is unusable") from error


def _checked_status(
    signer: _VerifiedSigner,
    revocation: tuple[datetime, x509.ReasonFlags | None] | None,
    evaluated_at: datetime,
) -> dict[str, str | None]:
    effective, reason = revocation if revocation is not None else (None, None)
    serial = signer.certificate.serial_number
    if effective is None:
        if evaluated_at > signer.certificate.not_valid_after_utc:
            raise TimestampError(
                "Indeterminate", "TSA CRL may omit previously revoked expired certificates"
            )
        status = "No Revocation Listed at genTime"
    else:
        if effective <= signer.gen_time:
            raise TimestampError(
                "Inapplicable",
                f"TSA signer for reading {signer.record_id} was revoked at or before genTime",
            )
        if reason not in POST_GENTIME_REASONS:
            raise TimestampError(
                "Inapplicable", "TSA revocation reason invalidates prior tokens under RFC 3161"
            )
        if not signer.accuracy_unspecified:
            raise TimestampError(
                "Indeterminate", "Explicit timestamp accuracy is outside the historical TSA profile"
            )
        status = "Revoked After genTime"
    return {
        "record_id": signer.record_id,
        "tsa_signer_serial": str(serial),
        "status": status,
        "effective_revocation_at": _utc_label(effective) if effective is not None else None,
        "revocation_reason": reason.value if reason is not None else None,
    }


def _revocation_status(
    content: bytes,
    root: x509.Certificate,
    evaluated_at: datetime,
    verified_signers: list[_VerifiedSigner],
) -> dict[str, Any]:
    last_update, next_update, effective_dates = _read_crl(content, root, evaluated_at)
    if any(last_update < signer.gen_time for signer in verified_signers):
        raise TimestampError("Indeterminate", "TSA CRL was issued before trusted genTime")
    return {
        "status": "Verified",
        "crl_sha256": hashlib.sha256(content).hexdigest(),
        "evaluated_at": _utc_label(evaluated_at),
        "last_update": _utc_label(last_update),
        "next_update": _utc_label(next_update),
        "findings": [
            _checked_status(
                signer, effective_dates.get(signer.certificate.serial_number), evaluated_at
            )
            for signer in verified_signers
        ],
    }


def _certificate_evaluation(
    evaluated_at: datetime, verified_signers: list[_VerifiedSigner]
) -> dict[str, Any]:
    if any(evaluated_at < signer.gen_time for signer in verified_signers):
        raise TimestampError("Indeterminate", "TSA status evaluation precedes trusted genTime")
    return {
        "evaluated_at": _utc_label(evaluated_at),
        "findings": [
            {
                "record_id": signer.record_id,
                "tsa_signer_serial": str(signer.certificate.serial_number),
                "not_after": _utc_label(signer.certificate.not_valid_after_utc),
                "status": "Expired"
                if evaluated_at > signer.certificate.not_valid_after_utc
                else "Within Validity",
            }
            for signer in verified_signers
        ],
    }


def verify_timestamps(
    signatures: list[dict[str, Any]],
    timestamp_content: bytes,
    tsa_root_pem: bytes,
    expected_root_sha256: str,
    *,
    revocation_pem: bytes | None = None,
    evaluated_at: str | None = None,
) -> dict[str, Any]:
    """Independently verify time of existence and any supplied historic TSA status."""
    if revocation_pem is not None and evaluated_at is None:
        raise TimestampError(
            "Indeterminate", "A TSA CRL requires an explicit UTC evaluation instant"
        )
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
        verified_signers = []
        previous = None
        for record_id, signature, signed_at in claims:
            response = responses[record_id]
            gen_time, signer, accuracy_unspecified = _verify_token(
                executable, root, workspace, environment, libressl, response, signature
            )
            if gen_time < signed_at or (previous is not None and gen_time < previous):
                raise TimestampError(
                    "Invalid", "Trusted genTime conflicts with the signed reading chronology"
                )
            previous = gen_time
            verified_signers.append(
                _VerifiedSigner(record_id, gen_time, signer, accuracy_unspecified)
            )
            timestamps.append(
                {
                    "record_id": record_id,
                    "gen_time": _utc_label(gen_time),
                    "response": response,
                }
            )
    evidence: dict[str, Any] = {
        "tsa_root_sha256": actual_pin,
        "trusted_timestamps": timestamps,
        "timestamp_assurance": (
            "The exact signature existed by each verified RFC 3161 genTime. "
            "The signing instant remains signer-asserted."
        ),
    }
    if evaluated_at is not None:
        evaluation = _read_evaluation(evaluated_at)
        evidence["tsa_certificate_evaluation"] = _certificate_evaluation(
            evaluation, verified_signers
        )
        evidence["tsa_revocation_status"] = (
            _revocation_status(revocation_pem, root, evaluation, verified_signers)
            if revocation_pem is not None
            else {
                "status": "Indeterminate",
                "evaluated_at": _utc_label(evaluation),
                "reason": "No independently supplied TSA CRL",
            }
        )
    return evidence
