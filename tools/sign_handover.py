"""Sign archived readings for the synthetic aircraft handover rehearsal."""

import base64
import hashlib
import json
import re
from datetime import datetime
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

FORMAT = "Airworthiness+ Synthetic Reading Signatures"
PURPOSE = "airworthiness-plus:synthetic-utilisation-reading:v1"


def _canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _sha256(value: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z", value
    ):
        raise ValueError("Signing time must use UTC with whole seconds")
    return datetime.fromisoformat(value)


def _sign(
    reading: dict[str, Any],
    *,
    organisation_id: str,
    aircraft_id: str,
    signer_id: str,
    key_id: str,
    authority_id: str,
    signed_at: str,
    private_key: Ed25519PrivateKey,
    reason: str = "",
    predecessor: dict[str, Any] | None = None,
) -> dict[str, Any]:
    identities = (organisation_id, aircraft_id, signer_id, key_id, authority_id)
    if not all(_nonblank(value) for value in identities):
        raise ValueError("Supply the organisation, aircraft, signer, key and authority")
    _timestamp(signed_at)
    if reading.get("organisation_id") != organisation_id or not _nonblank(reading.get("id")):
        raise ValueError("The archived reading must have an ID and belong to the organisation")
    claim = {
        "purpose": PURPOSE,
        "organisation_id": organisation_id,
        "aircraft_id": aircraft_id,
        "record_id": reading["id"],
        "record_sha256": _sha256(reading),
        "supersedes_id": reading["supersedes_id"],
        "supersedes_claim_sha256": _sha256(predecessor) if predecessor else None,
        "reason": reason,
        "signer_id": signer_id,
        "key_id": key_id,
        "authority_id": authority_id,
        "signed_at": signed_at,
    }
    signature = base64.b64encode(private_key.sign(_canonical(claim))).decode("ascii")
    return {"claim": claim, "signature": signature}


def sign_original(
    original: dict[str, Any],
    *,
    organisation_id: str,
    aircraft_id: str,
    signer_id: str,
    key_id: str,
    authority_id: str,
    signed_at: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    """Return a detached signature entry for the exact original archived reading.

    The caller supplies the archive's organisation and aircraft IDs, an externally
    assigned rehearsal signer, key and authority, and a UTC timestamp. The caller
    checks the archive and ensures the counter belongs to the aircraft.
    """
    if (
        "supersedes_id" not in original
        or original["supersedes_id"] is not None
        or not _nonblank(original.get("counter_id"))
    ):
        raise ValueError("An original reading needs a counter and no predecessor")
    return _sign(
        original,
        organisation_id=organisation_id,
        aircraft_id=aircraft_id,
        signer_id=signer_id,
        key_id=key_id,
        authority_id=authority_id,
        signed_at=signed_at,
        private_key=private_key,
    )


def sign_correction(
    original: dict[str, Any],
    correction: dict[str, Any],
    original_signature: dict[str, Any],
    *,
    organisation_id: str,
    aircraft_id: str,
    signer_id: str,
    key_id: str,
    authority_id: str,
    signed_at: str,
    reason: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    """Return a correction signature entry bound to the retained original claim.

    The caller provides the retained entry from sign_original and the correction
    reason. The archived reading schema has no reason field.
    """
    original_id = original.get("id")
    counter_id = original.get("counter_id")
    if (
        not _nonblank(original_id)
        or original_id == correction.get("id")
        or original_id != correction.get("supersedes_id")
        or "supersedes_id" not in original
        or original["supersedes_id"] is not None
        or original.get("organisation_id") != organisation_id
        or not _nonblank(counter_id)
        or counter_id != correction.get("counter_id")
    ):
        raise ValueError("The correction must supersede the original reading on the same counter")
    if not _nonblank(reason):
        raise ValueError("Supply a nonblank correction reason")
    predecessor = original_signature.get("claim")
    expected = {
        "purpose": PURPOSE,
        "organisation_id": organisation_id,
        "aircraft_id": aircraft_id,
        "record_id": original_id,
        "record_sha256": _sha256(original),
        "supersedes_id": None,
        "supersedes_claim_sha256": None,
        "reason": "",
    }
    if (
        not isinstance(predecessor, dict)
        or not _nonblank(original_signature.get("signature"))
        or any(
            field not in predecessor or predecessor[field] != value
            for field, value in expected.items()
        )
    ):
        raise ValueError("The retained original signature must describe the same archived reading")
    if _timestamp(signed_at) < _timestamp(predecessor.get("signed_at")):
        raise ValueError("The correction signature cannot precede the original signature")
    return _sign(
        correction,
        organisation_id=organisation_id,
        aircraft_id=aircraft_id,
        signer_id=signer_id,
        key_id=key_id,
        authority_id=authority_id,
        signed_at=signed_at,
        private_key=private_key,
        reason=reason,
        predecessor=predecessor,
    )


def signature_envelope(
    original_signature: dict[str, Any], correction_signature: dict[str, Any]
) -> dict[str, Any]:
    """Package the detached signatures for transfer beside the records archive."""
    return {
        "format": FORMAT,
        "version": 1,
        "signatures": [original_signature, correction_signature],
    }
