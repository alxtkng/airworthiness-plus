"""Rehearse a stop and fallback with the two synthetic organisations."""

import json
from io import BytesIO
from zipfile import ZipFile

from playwright.sync_api import Browser, Page, expect

from airworthiness_plus.exports.verify import verify
from tests.e2e.browser import choose_aircraft, fill, reveal, save, signed_in, submit
from tests.e2e.conftest import Account

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
