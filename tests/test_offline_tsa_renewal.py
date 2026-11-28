"""Renew a synthetic timestamp while valid and verify it after real leaf expiry."""

import hashlib
import importlib
import json
import shutil
import subprocess
from base64 import b64encode
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from time import sleep
from typing import Any, cast

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _utc(value: datetime) -> str:
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def _encoded(value: Any) -> bytes:
    return json.dumps(value).encode()


def test_renewal_preserves_predecessor_evidence_beyond_its_actual_certificate_expiry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    executable = shutil.which("openssl")
    if executable is None:
        pytest.skip("Historical verification requires OpenSSL 3")
    version = subprocess.run(  # noqa: S603  fixed OpenSSL version command
        [executable, "version"],
        capture_output=True,
        check=True,
        timeout=5,
    )
    if not version.stdout.startswith(b"OpenSSL 3."):
        pytest.skip("Historical verification requires OpenSSL 3 and ts -attime")

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))
    issuer = importlib.import_module("timestamp_handover")
    receiver = importlib.import_module("verify_handover_timestamps")
    private = Ed25519PrivateKey.generate()
    signed_at = _utc(datetime.now(UTC))
    signatures = [
        {
            "claim": {"record_id": record_id, "signed_at": signed_at},
            "signature": b64encode(private.sign(record_id.encode())).decode("ascii"),
        }
        for record_id in ("trial-original", "trial-correction")
    ]
    received = {
        "signatures": signatures,
        "manifest_sha256": "1" * 64,
        "trust_sha256": "2" * 64,
    }
    successor = issuer.make_timestamp_authority(tmp_path, leaf_validity_days=180)
    predecessor = issuer.make_timestamp_authority(tmp_path, leaf_validity_days=8 / 86400)
    predecessor_pin = hashlib.sha256(predecessor.root_pem).hexdigest()
    successor_pin = hashlib.sha256(successor.root_pem).hexdigest()
    initial = issuer.timestamp_envelope(predecessor, signatures)
    alternate = deepcopy(initial)
    alternate["timestamps"][1] = issuer.timestamp_signature(predecessor, signatures[1])
    before = datetime.now(UTC).replace(microsecond=0)
    initial_evidence = receiver.verify_timestamps(
        signatures,
        _encoded(initial),
        predecessor.root_pem,
        predecessor_pin,
        evaluated_at=_utc(before),
    )
    expiry = datetime.fromisoformat(
        initial_evidence["tsa_certificate_evaluation"]["findings"][0]["not_after"]
    )
    original_crl = issuer.make_timestamp_crl(predecessor, last_update=before, next_update=expiry)
    different_crl = issuer.make_timestamp_crl(
        predecessor,
        last_update=before,
        next_update=expiry + timedelta(seconds=1),
    )

    def issue(crl: bytes | None) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            issuer.renewal_envelope(
                successor,
                signatures,
                initial,
                archive_manifest_sha256=received["manifest_sha256"],
                reading_trust_sha256=received["trust_sha256"],
                previous_tsa_root_sha256=predecessor_pin,
                previous_crl=crl,
            ),
        )

    on_time = issue(original_crl)
    missing_history = issue(None)
    delay = (expiry + timedelta(seconds=1) - datetime.now(UTC)).total_seconds()
    if delay > 0:
        sleep(delay)
    late = issue(original_crl)
    after = datetime.now(UTC).replace(microsecond=0)
    assert after > expiry
    current_crl = issuer.make_timestamp_crl(
        successor,
        last_update=after,
        next_update=after + timedelta(days=1),
    )

    def verify(
        renewals: dict[str, Any], crl: bytes | None, previous: dict[str, Any] = initial
    ) -> dict[str, Any]:
        return cast(
            "dict[str, Any]",
            receiver.verify_renewals(
                received,
                _encoded(previous),
                predecessor.root_pem,
                predecessor_pin,
                crl,
                _encoded(renewals),
                successor.root_pem,
                successor_pin,
                current_crl,
                _utc(after),
            ),
        )

    result = verify(on_time, original_crl)
    assert result["renewal_chain_status"] == "Verified"
    assert {
        row["status"]
        for row in result["original_timestamp_evidence"]["tsa_certificate_evaluation"]["findings"]
    } == {"Expired"}
    assert {row["status"] for row in result["renewal_tsa_certificate_evaluation"]["findings"]} == {
        "Within Validity"
    }
    assert all(datetime.fromisoformat(row["gen_time"]) < expiry for row in result["renewals"])
    assert verify(missing_history, None)["renewal_chain_status"] == "Indeterminate"

    with pytest.raises(receiver.TimestampError, match="at or after predecessor TSA expiry"):
        verify(late, original_crl)
    for changed, crl in ((initial, None), (initial, different_crl), (alternate, original_crl)):
        with pytest.raises(receiver.TimestampError, match="exact payload"):
            verify(on_time, crl, previous=changed)
