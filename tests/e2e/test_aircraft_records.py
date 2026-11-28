"""Aircraft drawing revisions, accessible markers and per-flight provenance."""

import io
import json
from zipfile import ZipFile

from playwright.sync_api import Browser, expect

from tests.e2e.browser import choose_aircraft, fill, form_with, reveal, save, signed_in, submit
from tests.e2e.conftest import Account


def test_damage_register_preserves_a_lightning_strike_across_drawing_revisions(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-FMNO", "Maintenance Programme")
        page.get_by_role("link", name="Add a Task", exact=True).click()
        form = form_with(page, "title")
        form.locator('[name="counter"]').select_option(index=1)
        fill(
            form,
            {
                "title": "Repeat Frame 17 inspection",
                "kind": "Programme Task",
                "source": "SYNTHETIC-SRM 51-01, rev 1",
                "interval_hours": "25.0",
                "starts_dated": "2026-11-18",
                "starts_hours": "4950.2",
                "starts_cycles": "0",
            },
        )
        submit(page, form.get_by_role("button"))
        expect(page.get_by_text("Repeat Frame 17 inspection", exact=True).first).to_be_visible()
        page.get_by_role("link", name="Record Work Done", exact=True).click()
        save(
            page,
            "Record Work",
            {
                "description": "Lightning damage repair",
                "dated": "2026-11-18",
                "hours": "4950.2",
                "cycles": "0",
            },
            "Lightning damage repair",
        )
        choose_aircraft(page, "G-FMNO", "Damage Register")
        page.get_by_role("link", name="Record a Drawing", exact=True).click()
        save(
            page,
            "Record a Drawing Revision",
            {
                "reference": "SYN-DRAW-17",
                "view": "Front",
                "revision": "A",
                "outline": "5,10 90,10 50,80",
            },
            "SYN-DRAW-17, Front, revision A",
        )
        drawing_a = page.url
        page.get_by_role("link", name="G-FMNO Damage Register").click()
        page.get_by_role("link", name="Record a Structural Finding").click()
        save(
            page,
            "Record a Structural Finding",
            {
                "title": "Lightning strike finding",
                "found_on": "2026-11-17",
                "frame_or_zone": "Frame 17, Zone 2",
                "dimensions": "15 x 5 mm",
                "evidence": "SYNTHETIC-PHOTO-17",
                "applicable_reference": "SYNTHETIC-SRM 51-01, rev 1",
                "disposition": "Repaired with recurring inspection",
                "marker_x": "30",
                "marker_y": "20",
                "repair": "Lightning damage repair",
                "follow_up": "Repeat Frame 17 inspection",
                "drawing": "SYN-DRAW-17, Front, revision A",
            },
            "Frame 17, Zone 2",
        )
        original = page.url
        page.get_by_role("link", name="Locate Marker").click()
        marker = page.locator("svg a")
        marker.focus()
        expect(marker).to_be_focused()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        expect(page).to_have_url(original)
        page.get_by_role("link", name="Locate Marker").click()
        with page.expect_navigation():
            page.get_by_role("link", name="Lightning strike finding", exact=True).click()
        expect(page).to_have_url(original)
        page.goto(drawing_a)
        page.get_by_role("link", name="Revise Drawing").click()
        save(
            page,
            "Record a Drawing Revision",
            {"revision": "B", "outline": "5,10 90,10 55,85"},
            "SYN-DRAW-17, Front, revision B",
        )
        drawing_b = page.url
        expect(page.get_by_text("No Markers Recorded for This Revision")).to_be_visible()
        page.goto(original)
        page.get_by_role("link", name="Revise Finding or Remap Marker").click()
        expect(page.get_by_label("Physical Frame or Zone")).to_have_value("Frame 17, Zone 2")
        save(page, "Record a Structural Finding", {"marker_x": "40"}, "revision B")
        expect(page.get_by_role("link", name="Previous Finding Version")).to_have_attribute(
            "href", original.removeprefix(live_site)
        )
        expect(page.get_by_role("link", name="Lightning damage repair", exact=True)).to_be_visible()
        expect(
            page.get_by_role("link", name="Repeat Frame 17 inspection", exact=True)
        ).to_be_visible()
        page.get_by_role("link", name="Locate Marker").click()
        assert page.url.split("#")[0] == drawing_b
        expect(page.locator("svg circle")).to_have_attribute("cx", "40")

    with signed_in(chromium, live_site, personas["second-organisation"][3]) as page:
        for url in (drawing_a, drawing_b, original):
            response = page.goto(url)
            assert response is not None and response.status == 404


def test_technical_log_filters_structured_parts_and_preserves_original_report(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3], returning=True) as page:
        for number in ("3291556-1", "3291556-2"):
            page.goto("/components/add/")
            save(
                page,
                "Add Component",
                {
                    "name": f"Starter {number}",
                    "part_number": number,
                    "basis": "No Limit Recorded",
                },
                f"Starter {number}",
            )
        choose_aircraft(page, "G-FMNO", "Maintenance Programme")
        page.get_by_role("link", name="Record Work Done", exact=True).click()
        save(
            page,
            "Record Work",
            {
                "description": "Synthetic starter rectification",
                "dated": "2026-11-18",
                "hours": "4950.2",
                "cycles": "0",
            },
            "Synthetic starter rectification",
        )
        row = page.locator("main tr:not(.detail)").filter(
            has_text="Synthetic starter rectification"
        )
        reveal(row).get_by_role("link", name="Record Certificate of Release to Service").click()
        save(
            page,
            "Record Certificate",
            {
                "reference": "SYN-CRS-18",
                "kind": "Independent Certifying Staff",
                "issuer_name": "Synthetic Certifier",
                "licence": "SYN-LICENCE-18",
                "issued_on": "2026-11-18",
            },
            "SYN-CRS-18",
        )
        page.goto("/defects/record/")
        save(
            page,
            "Record Defect",
            {
                "aircraft": "G-FMNO",
                "title": "Synthetic starter defect",
                "found_on": "2026-11-18",
                "chapter": "80",
                "section": "11",
                "system": "Starter",
                "decision": "Not Deferrable",
                "decided_on": "2026-11-18",
            },
            "Synthetic starter defect",
        )
        save(
            page,
            "Close Synthetic starter defect",
            {
                "closed_on": "2026-11-18",
                "rectification": "Starter fixed",
                "work_done": "Synthetic starter rectification",
            },
            "Starter fixed",
        )
        choose_aircraft(page, "G-FMNO", "Technical Log")
        page.get_by_role("link", name="Record a Flight").click()
        save(
            page,
            "Record a Flight",
            {
                "reference": "SYN-FLT-18",
                "flown_on": "2026-11-18",
                "departure": "EGKA",
                "arrival": "EGKB",
            },
            "SYN-FLT-18",
        )
        flight = page.url
        for kind, reference, component, reporter, report in (
            ("Pilot Report", "PILOT-18", "3291556-1", "Synthetic Pilot", "Starter did not engage"),
            (
                "Maintenance Finding",
                "MX-18",
                "3291556-1",
                "Synthetic Engineer",
                "Intermittent starter",
            ),
            ("Maintenance Finding", "OTHER-18", "3291556-2", "Synthetic Engineer", "Other starter"),
            ("Pilot Report", "TEXT-18", "", "Synthetic Pilot", "Mentioned 3291556-1 in text"),
        ):
            page.goto(flight)
            page.get_by_role("link", name="Transcribe a Flight Report").click()
            values = {
                "kind": kind,
                "chapter": "80",
                "section": "11",
                "source_reference": reference,
                "reporter": reporter,
                "report": report,
                "confirmed": "on",
            }
            if component:
                values["component"] = f"Starter {component}, Part Number {component}"
            if reference == "MX-18":
                values["defect"] = "Synthetic starter defect"
            save(page, "Transcribe a Flight Report", values, report)
            expect(page.get_by_text(reporter, exact=True)).to_be_visible()
            expect(page.get_by_text("Recorded By", exact=True)).to_be_visible()
            if reference == "MX-18":
                page.get_by_role("link", name="Link an Existing Release").click()
                save(page, "Link the Release", {"release": "SYN-CRS-18"}, "Synthetic Certifier")

        choose_aircraft(page, "G-FMNO", "Technical Log")
        controls = page.get_by_role("form", name="Filter Flight Reports")
        fill(controls, {"chapter": "80", "part": "3291556-1"})
        submit(page, controls.get_by_role("button", name="Filter Reports"))
        expect(page.get_by_role("link", name="Pilot Report · PILOT-18")).to_be_visible()
        expect(page.get_by_role("link", name="Maintenance Finding · MX-18")).to_be_visible()
        expect(page.get_by_role("link", name="Maintenance Finding · OTHER-18")).to_have_count(0)
        expect(page.get_by_role("link", name="Pilot Report · TEXT-18")).to_have_count(0)
        page.get_by_role("link", name="Pilot Report · PILOT-18").click()
        original = page.url
        expect(page.get_by_text("Starter did not engage", exact=True)).to_be_visible()

        page.goto("/records-export/")
        row = page.locator("main tbody tr:not(.detail)").filter(
            has=page.get_by_role("cell", name="G-FMNO", exact=True)
        )
        with page.expect_download() as obtained:
            reveal(row).get_by_role("button", name="Export the Record of G-FMNO").click()
        with ZipFile(io.BytesIO(obtained.value.path().read_bytes())) as export:
            records = json.loads(export.read("records/defects_flightreport.json"))
            report = next(row for row in records if row["source_reference"] == "PILOT-18")
            assert report["reporter"] == "Synthetic Pilot"
            assert report["report"] == "Starter did not engage"
            assert report["recorder_name"] != report["reporter"]
            finding = next(row for row in records if row["source_reference"] == "MX-18")
            (link,) = json.loads(export.read("records/defects_flightreportrelease.json"))
            releases = json.loads(export.read("records/releases_release.json"))
            release = next(row for row in releases if row["id"] == link["release_id"])
            assert link["report_id"] == finding["id"]
            assert release["issuer_name"] == "Synthetic Certifier"
            assert finding["reporter"] == "Synthetic Engineer"

    with signed_in(chromium, live_site, personas["second-organisation"][3]) as page:
        response = page.goto(original)
        assert response is not None and response.status == 404
