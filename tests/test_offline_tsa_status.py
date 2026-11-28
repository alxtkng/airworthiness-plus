"""Historical TSA certificate and CRL checks for the synthetic timestamp profile."""

import hashlib
import importlib
import json
from base64 import b64encode
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, cast

import pytest
from cryptography import x509
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_offline_timestamp_retains_historical_expiry_and_checks_revocation_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    issuer = importlib.import_module("timestamp_handover")
    receiver = importlib.import_module("verify_handover_timestamps")
    signing_key = Ed25519PrivateKey.generate()
    signed_at = _utc(datetime.now(UTC))
    signatures = [
        {
            "claim": {"record_id": record, "signed_at": signed_at},
            "signature": b64encode(signing_key.sign(record.encode())).decode("ascii"),
        }
        for record in ("synthetic-original", "synthetic-correction")
    ]

    with TemporaryDirectory(prefix="aw-historical-tsa-") as temporary:
        authority = issuer.make_timestamp_authority(Path(temporary))
        envelope = json.dumps(issuer.timestamp_envelope(authority, signatures)).encode()
        pinned_root = authority.root_pem
        pin = hashlib.sha256(pinned_root).hexdigest()

        def assess(*, evaluated_at: str | None = None, crl: bytes | None = None) -> dict[str, Any]:
            return cast(
                "dict[str, Any]",
                receiver.verify_timestamps(
                    signatures,
                    envelope,
                    pinned_root,
                    pin,
                    evaluated_at=evaluated_at,
                    revocation_pem=crl,
                ),
            )

        initial = assess()
        times = [datetime.fromisoformat(row["gen_time"]) for row in initial["trusted_timestamps"]]
        first, last = min(times), max(times)
        evaluation = last + timedelta(days=1)
        window = {
            "last_update": last + timedelta(hours=2),
            "next_update": evaluation + timedelta(days=1),
        }
        before, after = first - timedelta(minutes=1), last + timedelta(minutes=1)

        clear = issuer.make_timestamp_crl(authority, **window)
        in_date = assess(evaluated_at=_utc(evaluation), crl=clear)
        assert in_date["tsa_revocation_status"]["status"] == "Verified"
        assert {row["status"] for row in in_date["tsa_certificate_evaluation"]["findings"]} == {
            "Within Validity"
        }

        not_after = datetime.fromisoformat(
            in_date["tsa_certificate_evaluation"]["findings"][0]["not_after"]
        )
        expired_at = _utc(not_after + timedelta(seconds=1))
        expired = assess(evaluated_at=expired_at)
        assert expired["trusted_timestamps"] == initial["trusted_timestamps"]
        assert {row["status"] for row in expired["tsa_certificate_evaluation"]["findings"]} == {
            "Expired"
        }
        assert expired["tsa_revocation_status"]["status"] == "Indeterminate"

        later = issuer.make_timestamp_crl(authority, **window, revoked_at=after)
        accepted = assess(evaluated_at=_utc(evaluation), crl=later)
        assert {row["status"] for row in accepted["tsa_revocation_status"]["findings"]} == {
            "Revoked After genTime"
        }
        assert accepted["trusted_timestamps"] == initial["trusted_timestamps"]

        for variant in (
            {"revoked_at": before},
            {"revoked_at": first},
            {"revoked_at": after, "invalidity_date": before},
            {"revoked_at": after, "reason": x509.ReasonFlags.key_compromise},
            {"revoked_at": after, "reason": None},
        ):
            status = issuer.make_timestamp_crl(authority, **window, **variant)
            with pytest.raises(receiver.TimestampError):
                assess(evaluated_at=_utc(evaluation), crl=status)

        stale = issuer.make_timestamp_crl(authority, **(window | {"next_update": evaluation}))
        with pytest.raises(receiver.TimestampError, match="Indeterminate"):
            assess(evaluated_at=_utc(evaluation), crl=stale)

        prior_crl = issuer.make_timestamp_crl(
            authority, last_update=first - timedelta(seconds=1), next_update=window["next_update"]
        )
        with pytest.raises(receiver.TimestampError, match="issued before trusted genTime"):
            assess(evaluated_at=_utc(evaluation), crl=prior_crl)

        unrelated = issuer.make_timestamp_authority(Path(temporary))
        foreign = issuer.make_timestamp_crl(unrelated, **window)
        with pytest.raises(receiver.TimestampError):
            assess(evaluated_at=_utc(evaluation), crl=foreign)

        issued_after_expiry = issuer.make_timestamp_crl(
            authority,
            last_update=not_after + timedelta(seconds=1),
            next_update=not_after + timedelta(days=1),
        )
        with pytest.raises(receiver.TimestampError, match="Indeterminate"):
            assess(evaluated_at=expired_at, crl=issued_after_expiry)
