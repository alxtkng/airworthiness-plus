"""Rehearse a stop and fallback with the two synthetic organisations."""

import hashlib
import importlib
import json
import os
import subprocess
import sys
from datetime import datetime
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from playwright.sync_api import Browser, Page, expect

from airworthiness_plus.exports.verify import verify
from tests.e2e.browser import choose_aircraft, fill, reveal, save, signed_in, submit
from tests.e2e.conftest import Account
from tests.test_exports import (
    OFFLINE_RECEIVER,
    _signed_fixture_key,
    _stamp,
    _trial_json,
    _whole_signing_time,
    opened,
)

AIRCRAFT = "G-EJKL"
DEFECT = "Right Headset Socket Crackle"
DISCREPANCY = "G-EJKL transfer fixture gives a different deferred defect limit"


def _aircraft_archive(page: Page) -> bytes:
    page.goto("/records-export/")
    row = page.locator("main tbody tr:not(.detail)").filter(
        has=page.get_by_role("cell", name=AIRCRAFT, exact=True)
    )
    with page.expect_download() as downloaded:
        reveal(row).get_by_role("button", name=f"Export the Record of {AIRCRAFT}").click()
    return downloaded.value.path().read_bytes()


def test_parallel_handover_stops_and_returns_to_source_records(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    sender = personas["your-organisation"][0]
    receiver = personas["second-organisation"][3]
    with signed_in(chromium, live_site, sender) as issuing_page:
        original = _aircraft_archive(issuing_page)
        assert verify(original).problems == ()
        with ZipFile(BytesIO(original)) as archive:
            defect = next(
                item
                for item in json.loads(archive.read("records/defects_defect.json"))
                if item["title"] == DEFECT
            )
        assert defect["closed_on"] is None
        assert defect["limit_on"] != "2026-12-31"

        with signed_in(chromium, live_site, receiver) as receiving_page:
            receiving_page.goto("/problem-log/")
            save(receiving_page, "Add Entry", {"problem": DISCREPANCY}, DISCREPANCY)
            row = receiving_page.locator("main tr:not(.detail)").filter(has_text=DISCREPANCY)
            details = reveal(row)
            form = details.locator("form")
            action = (
                "Stop handover. Receiver planner refers the difference to the sender records lead. "
                "Sender records remain the system of record."
            )
            fill(form, {"kind": "Action", "text": action})
            submit(receiving_page, form.get_by_role("button", name="Add to This Entry"))
            receiving_page.reload()
            expect(row.get_by_text("Action Taken", exact=True)).to_be_visible()
            expect(reveal(row)).to_contain_text(action)
            receiving_page.goto("/records-export/")
            expect(receiving_page.locator("main")).not_to_contain_text(AIRCRAFT)

        choose_aircraft(issuing_page, AIRCRAFT, "Maintenance Forecast")
        expect(issuing_page.locator("main")).to_contain_text(DEFECT)
        after_stop = _aircraft_archive(issuing_page)
        assert verify(after_stop).problems == ()
        with ZipFile(BytesIO(original)) as before, ZipFile(BytesIO(after_stop)) as after:
            record_paths = ("records/", "history/")
            records = {name for name in before.namelist() if name.startswith(record_paths)}
            assert records
            recovered = {name for name in after.namelist() if name.startswith(record_paths)}
            assert records == recovered
            for name in records:
                assert before.read(name) == after.read(name), name


def test_gejkl_completion_and_correction_transfer_from_normal_forms(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Record completion and both reading versions, then reconcile the aircraft export offline."""
    title = "G-EJKL Trial Repeat Inspection"
    instruction = "Synthetic applicable instruction AW-I-05"
    measurements = "Clearance 1.2 mm"
    readings_table = "records/aircraft_utilisationentry.json"
    history_table = "history/aircraft_utilisationentry.json"
    project = Path(__file__).resolve().parents[2]
    monkeypatch.syspath_prepend(str(project / "tools"))
    signatures = importlib.import_module("sign_handover")
    key = Ed25519PrivateKey.generate()
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, AIRCRAFT, "Maintenance Programme")
        page.get_by_role("link", name="Record the Programme", exact=True).click()
        save(
            page,
            "Save Programme",
            {
                "basis": "Design Approval Holder's Instructions",
                "reference": "G-EJKL Trial Programme",
            },
            "G-EJKL Trial Programme",
        )
        page.get_by_role("link", name="Add a Task", exact=True).click()
        page.get_by_label("Runs Against", exact=True).select_option(index=1)
        save(
            page,
            "Add Task",
            {
                "title": title,
                "kind": "Programme Task",
                "source": instruction,
                "interval_days": "30",
            },
            title,
        )
        page.get_by_role("link", name="Record Work Done", exact=True).click()
        save(
            page,
            "Record Work",
            {
                "task": title,
                "description": "G-EJKL Trial Completed Inspection",
                "dated": "2026-11-18",
                "hours": "11206.8",
                "cycles": "0",
                "instruction_reference": instruction,
                "instruction_revision": "2",
                "completion_measurements": measurements,
            },
            measurements,
        )
        choose_aircraft(page, AIRCRAFT)
        page.get_by_role("link", name="Enter Hours and Cycles", exact=True).click()
        page.get_by_label("Counter", exact=True).select_option(index=1)
        save(
            page,
            f"Save Entry for {AIRCRAFT}",
            {"dated": "2026-11-18", "hours": "11208.6", "cycles": "0"},
            "11,208.6",
        )
        original_archive = opened(_aircraft_archive(page))
        original = next(
            item for item in original_archive[readings_table] if item["hours"] == 11208.6
        )
        original_event = next(
            item for item in original_archive[history_table] if item["record_id"] == original["id"]
        )
        original_at = _whole_signing_time(datetime.fromisoformat(original_event["at"]))
        identity = {
            "signer_id": original_event["actor_id"],
            "organisation_id": original["organisation_id"],
            "aircraft_id": original_archive["manifest.json"]["aircraft"]["id"],
            "key_id": "GEJKL-BROWSER-TRIAL-KEY",
            "authority_id": "GEJKL-BROWSER-TRIAL-UTILISATION",
        }
        endorsed = signatures.sign_original(
            original, private_key=key, signed_at=_stamp(original_at), **identity
        )
        (tmp_path / "browser-original-signature.json").write_bytes(_trial_json(endorsed))
        choose_aircraft(page, AIRCRAFT)
        page.get_by_role("link", name="Enter Hours and Cycles", exact=True).click()
        page.get_by_label("Counter", exact=True).select_option(index=1)
        page.get_by_label("Corrects an Earlier Entry", exact=True).select_option(
            value=original["id"]
        )
        save(
            page,
            f"Save Entry for {AIRCRAFT}",
            {"dated": "2026-11-18", "hours": "11207.0", "cycles": "0"},
            "11,207.0",
        )
        choose_aircraft(page, AIRCRAFT, "Maintenance Forecast")
        expect(page.locator("main")).to_contain_text(DEFECT)
        expect(page.locator("main")).to_contain_text(title)
        content = _aircraft_archive(page)

    verdict = verify(content)
    assert not verdict.problems
    records = opened(content)
    defect = next(
        item for item in records["records/defects_defect.json"] if item["title"] == DEFECT
    )
    task = next(item for item in records["records/programme_task.json"] if item["title"] == title)
    correction = next(
        item for item in records[readings_table] if item["supersedes_id"] == original["id"]
    )
    aircraft_id = records["manifest.json"]["aircraft"]["id"]
    archive = tmp_path / "browser-source.zip"
    archive.write_bytes(content)
    corrected_event = next(
        item for item in records[history_table] if item["record_id"] == correction["id"]
    )
    corrected_at = _whole_signing_time(datetime.fromisoformat(corrected_event["at"]))
    signed_correction = signatures.sign_correction(
        original,
        correction,
        endorsed,
        private_key=key,
        signed_at=_stamp(corrected_at),
        reason="Corrected the synthetic airframe log transcription.",
        **identity,
    )
    signed_path = tmp_path / "browser-signatures.json"
    signed_path.write_bytes(_trial_json(signatures.signature_envelope(endorsed, signed_correction)))
    custodian = tmp_path / "custodian"
    custodian.mkdir()
    trust = _trial_json(
        _signed_fixture_key(
            identity, key.public_key().public_bytes_raw(), original_at, corrected_at
        )
    )
    pin = hashlib.sha256(trust).hexdigest()
    trust_file = custodian / "trust.json"
    trust_file.write_bytes(trust)
    (custodian / "trust.sha256").write_text(pin + "\n")
    command = [
        sys.executable,
        "-c",
        OFFLINE_RECEIVER,
        str(project / "tools/receive_handover.py"),
        str(archive),
        str(tmp_path / "receiver.sqlite"),
        "--manifest-digest",
        verdict.manifest_sha256,
        "--aircraft-id",
        aircraft_id,
        "--defect-id",
        defect["id"],
        "--inspection-id",
        task["id"],
        "--correction-id",
        correction["id"],
        "--signatures",
        str(signed_path),
        "--trust",
        str(trust_file),
        "--trust-sha256",
        pin,
    ]
    for imported in (True, False):
        receiver = subprocess.run(  # noqa: S603  fixed offline executable and synthetic archive
            command,
            env={**os.environ, "PYTHONPATH": str(project / "src")},
            capture_output=True,
            text=True,
            check=False,
        )
        assert receiver.returncode == 0, receiver.stderr
        received = json.loads(receiver.stdout)
        assert received["imported"] is imported
        assert received["defect"]["limit_on"] == defect["limit_on"]
        assert received["next_due"] == "2026-12-18"
        assert received["inspection"]["source"] == instruction
        assert received["last_completion"]["instruction_revision"] == "2"
        assert received["last_completion"]["completion_measurements"] == measurements
        assert received["original_reading"] == original
        assert received["corrected_reading"] == correction
        assert received["signature"] == "Both detached Ed25519 signatures verified"
    (tmp_path / "browser-reconciliation.json").write_text(json.dumps(received, indent=2) + "\n")
