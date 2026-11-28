"""Verify detached G-EJKL synthetic reading evidence using recipient-pinned trust."""

import base64
import binascii
import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

PURPOSE = "airworthiness-plus:synthetic-utilisation-reading:v1"
ENVELOPE_FORMAT = "Airworthiness+ Synthetic Reading Signatures"
TRUST_FORMAT = "Airworthiness+ Synthetic Reading Trust"
CLAIM_FIELDS = {
    "purpose",
    "organisation_id",
    "aircraft_id",
    "record_id",
    "record_sha256",
    "supersedes_id",
    "supersedes_claim_sha256",
    "reason",
    "signer_id",
    "key_id",
    "authority_id",
    "signed_at",
}
VALIDITY_FIELDS = {"valid_from", "valid_to", "status_as_of", "revoked_at"}
TRUST_KEY_FIELDS = {"key_id", "signer_id", "organisation_id", "public_key"} | VALIDITY_FIELDS
AUTHORITY_FIELDS = {
    "authority_id",
    "signer_id",
    "organisation_id",
    "aircraft_id",
    "scope",
} | VALIDITY_FIELDS
READING_TABLE = "aircraft_utilisationentry"
UTC_SECONDS = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
SHA256 = re.compile(r"[0-9a-f]{64}")


class SignatureError(ValueError):
    """The signed transfer failed a required verification check."""

    def __init__(self, outcome: str, message: str):
        self.outcome = outcome
        super().__init__(f"{outcome}: {message}")


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise SignatureError("Invalid", f"Duplicate JSON field {key}")
        obj[key] = value
    return obj


def _decode_document(
    content: bytes, label: str, fields: set[str], expected_format: str
) -> dict[str, Any]:
    try:
        obj = json.loads(content.decode("utf-8"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise SignatureError("Invalid", f"{label} is not valid UTF-8 JSON") from error
    obj = _object(obj, fields | {"format", "version"}, label)
    if obj["format"] != expected_format or type(obj["version"]) is not int or obj["version"] != 1:
        raise SignatureError("Invalid", f"{label} format or version is unsupported")
    return obj


def _object(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or value.keys() != fields:
        raise SignatureError("Invalid", f"{label} has missing or unexpected fields")
    return value


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise SignatureError("Invalid", f"{label} must be a nonempty identifier")
    return value


def _instant(value: Any, label: str, *, history: bool = False) -> datetime:
    pattern = UTC_SECONDS + (r"(?:\.\d{1,6})?Z" if history else "Z")
    if not isinstance(value, str) or not re.fullmatch(pattern, value, flags=re.ASCII):
        raise SignatureError("Invalid", f"{label} must be a UTC timestamp")
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except ValueError as error:
        raise SignatureError("Invalid", f"{label} is not a valid UTC timestamp") from error


def _decoded_base64(value: Any, length: int, label: str) -> bytes:
    try:
        if not isinstance(value, str):
            raise ValueError(label)
        raw = base64.b64decode(value, validate=True)
        if len(raw) != length or base64.b64encode(raw).decode("ascii") != value:
            raise ValueError(label)
        return raw
    except (ValueError, binascii.Error) as error:
        raise SignatureError("Invalid", f"{label} is not a canonical Ed25519 value") from error


def _index(value: Any, fields: set[str], field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(value, list):
        raise SignatureError("Invalid", f"Expected a trust list for {field}")
    result = {}
    for row in value:
        entry = _object(row, fields, f"Trust entry for {field}")
        key = _identifier(entry[field], field)
        if key in result:
            raise SignatureError("Invalid", f"Duplicate trust entry for {field}")
        result[key] = entry
    return result


def _check_validity(entry: dict[str, Any], signed_at: datetime, label: str) -> None:
    first = _instant(entry["valid_from"], f"{label} validity start")
    end = _instant(entry["valid_to"], f"{label} validity end")
    if entry["status_as_of"] is None:
        raise SignatureError("Indeterminate", f"{label} historical status is unavailable")
    status = _instant(entry["status_as_of"], f"{label} status as of")
    revoked = (
        _instant(entry["revoked_at"], f"{label} revocation")
        if entry["revoked_at"] is not None
        else None
    )
    if first >= end or (revoked is not None and revoked > status):
        raise SignatureError("Invalid", f"{label} has inconsistent historical status evidence")
    if signed_at < first:
        raise SignatureError("Inapplicable", f"{label} is not yet valid at claimed signing time")
    if signed_at >= end:
        raise SignatureError("Inapplicable", f"{label} is expired at claimed signing time")
    if status < signed_at:
        raise SignatureError("Indeterminate", f"{label} status does not cover claimed signing time")
    if revoked is not None and revoked <= signed_at:
        raise SignatureError("Inapplicable", f"{label} is revoked at claimed signing time")


def _record_time(received: dict[str, Any], record_id: str) -> datetime:
    rows = [
        entry for entry in received["history"][READING_TABLE] if entry["record_id"] == record_id
    ]
    if not rows:
        raise SignatureError("Indeterminate", "Reading creation history is unavailable")
    if len(rows) != 1 or rows[0]["action"] != "Created" or rows[0]["sequence"] != 1:
        raise SignatureError("Invalid", "Expected one immutable creation event for each reading")
    return _instant(rows[0]["at"], "Reading creation event time", history=True)


def _verify_claim(
    row: dict[str, Any],
    keys: dict[str, dict[str, Any]],
    authorities: dict[str, dict[str, Any]],
) -> datetime:
    claim = row["claim"]
    key_id = _identifier(claim["key_id"], "Key ID")
    key = keys.get(key_id)
    if key is None:
        raise SignatureError("Unknown", "Signing key is absent from recipient trust")
    signer = _identifier(claim["signer_id"], "Signer ID")
    organisation = claim["organisation_id"]
    if (key["signer_id"], key["organisation_id"]) != (signer, organisation):
        raise SignatureError(
            "Inapplicable", "Signing key is for a different signer or organisation"
        )
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _decoded_base64(key["public_key"], 32, "Public key")
        )
        public_key.verify(_decoded_base64(row["signature"], 64, "Signature"), _canonical(claim))
    except InvalidSignature as error:
        raise SignatureError("Invalid", "Ed25519 signature verification failed") from error

    authority_id = _identifier(claim["authority_id"], "Authority ID")
    authority = authorities.get(authority_id)
    if authority is None:
        raise SignatureError("Unknown", "Maintenance authority is absent from recipient trust")
    scope = (authority["signer_id"], authority["organisation_id"], authority["aircraft_id"])
    if scope != (signer, organisation, claim["aircraft_id"]) or authority["scope"] != PURPOSE:
        raise SignatureError("Inapplicable", "Maintenance authority does not cover this claim")
    signed_at = _instant(claim["signed_at"], "Claim signing time")
    _check_validity(key, signed_at, "Signing key")
    _check_validity(authority, signed_at, "Maintenance authority")
    return signed_at


def _check_record(received: dict[str, Any], claim: dict[str, Any], reading: dict[str, Any]) -> None:
    if (
        claim["purpose"] != PURPOSE
        or claim["organisation_id"] != received["source_organisation_id"]
        or claim["aircraft_id"] != received["aircraft"]["id"]
    ):
        raise SignatureError("Inapplicable", "Claim is for a different purpose, issuer or aircraft")
    if claim["record_id"] != reading["id"] or claim["record_sha256"] != _digest(reading):
        raise SignatureError(
            "Invalid", "Claim digest or identity differs from the archived reading"
        )


def _verify_signatures(
    received: dict[str, Any], envelope_content: bytes, trust_content: bytes, trust_sha256: str
) -> dict[str, Any]:
    envelope = _decode_document(
        envelope_content, "Signature envelope", {"signatures"}, ENVELOPE_FORMAT
    )
    trust = _decode_document(trust_content, "Trust bundle", {"keys", "authorities"}, TRUST_FORMAT)
    keys = _index(trust["keys"], TRUST_KEY_FIELDS, "key_id")
    authorities = _index(trust["authorities"], AUTHORITY_FIELDS, "authority_id")

    original = received["original_reading"]
    corrected = received["corrected_reading"]
    original_id, corrected_id = original["id"], corrected["id"]
    signatures = envelope["signatures"]
    if not isinstance(signatures, list) or len(signatures) != 2:
        raise SignatureError("Invalid", "Expected exactly two signed readings")
    by_reading = {}
    for candidate in signatures:
        row = _object(candidate, {"claim", "signature"}, "Signed reading")
        claim = _object(row["claim"], CLAIM_FIELDS, "Reading claim")
        record_id = _identifier(claim["record_id"], "Record ID")
        if record_id in by_reading:
            raise SignatureError("Invalid", "Duplicate signed reading")
        by_reading[record_id] = row
    if original_id == corrected_id or set(by_reading) != {original_id, corrected_id}:
        raise SignatureError("Invalid", "Signed records differ from the archived reading pair")

    original_row, corrected_row = by_reading[original_id], by_reading[corrected_id]
    original_claim, corrected_claim = original_row["claim"], corrected_row["claim"]
    _check_record(received, original_claim, original)
    _check_record(received, corrected_claim, corrected)
    if (
        original["supersedes_id"] is not None
        or original_claim["supersedes_id"] is not None
        or original_claim["supersedes_claim_sha256"] is not None
        or original_claim["reason"] != ""
    ):
        raise SignatureError("Invalid", "Original reading cannot supersede an earlier record")
    reason = corrected_claim["reason"]
    if (
        corrected["supersedes_id"] != original_id
        or corrected_claim["supersedes_id"] != original_id
        or corrected_claim["supersedes_claim_sha256"] != _digest(original_claim)
        or not isinstance(reason, str)
        or not reason.strip()
    ):
        raise SignatureError(
            "Invalid", "Correction must link the archived and signed original with a reason"
        )

    original_time = _verify_claim(original_row, keys, authorities)
    corrected_time = _verify_claim(corrected_row, keys, authorities)
    if (
        corrected_time < original_time
        or original_time < _record_time(received, original_id)
        or corrected_time < _record_time(received, corrected_id)
    ):
        raise SignatureError("Invalid", "Claimed signing chronology conflicts with reading history")

    return {
        "trust_sha256": trust_sha256,
        "artifact_integrity": "Both claims match the archived reading contents",
        "issuer_trust": "Verified against recipient-pinned synthetic trust",
        "signature": "Both detached Ed25519 signatures verified",
        "signing_time": "Signer-asserted, without a trusted timestamp",
        "maintenance_authorisation": "Synthetic authority verified at the claimed signing times",
        "correction_reason": reason,
        "signatures": [original_row, corrected_row],
    }


def verify_signatures(
    received: dict[str, Any],
    envelope_content: bytes,
    trust_content: bytes,
    expected_trust_sha256: str,
) -> dict[str, Any]:
    """Verify both readings and their relationship before any receiver writes."""
    actual = hashlib.sha256(trust_content).hexdigest()
    if not isinstance(expected_trust_sha256, str) or not SHA256.fullmatch(expected_trust_sha256):
        raise SignatureError("Indeterminate", "A separately supplied SHA-256 trust pin is required")
    if not hmac.compare_digest(actual, expected_trust_sha256):
        raise SignatureError(
            "Invalid", "Trust bundle digest differs from the separately supplied pin"
        )
    try:
        return _verify_signatures(received, envelope_content, trust_content, actual)
    except SignatureError:
        raise
    except (KeyError, TypeError, ValueError, UnicodeError, RecursionError) as error:
        raise SignatureError("Invalid", "Malformed reading or signature evidence") from error
