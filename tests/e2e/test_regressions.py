"""The independent test's three high-severity findings."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import (
    change_aircraft_details,
    choose_aircraft,
    definition,
    fill,
    form_with,
    reveal,
    signed_in,
    submit,
)
from tests.e2e.conftest import Account
from tests.e2e.server import LEGACY_REFERENCE, LEGACY_WORK


def test_issued_certificate_keeps_aircraft_identity(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-CDEF", "Airworthiness Review")
        page.get_by_role("link", name="UK.CAO.[Number]-ARC-0001", exact=True).click()
        certificate = page.url
        labels = (
            "Aircraft Manufacturer",
            "Manufacturer\u2019s Designation",
            "Aircraft Serial Number",
        )
        original = tuple(definition(page, label) for label in labels)
        change_aircraft_details(page, "G-CDEF", "QA-018")
        page.goto(certificate)
        expect(page.locator("main")).to_contain_text("UK.CAO.[Number]-ARC-0001")
        assert tuple(definition(page, label) for label in labels) == original


def test_completed_review_keeps_its_reviewer(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    admin, manager, reviewer, _, reader = personas["your-organisation"]
    with signed_in(chromium, live_site, manager) as page:
        change_aircraft_details(page, "G-EJKL", "QA152-022")
    with signed_in(chromium, live_site, reviewer) as page:
        choose_aircraft(page, "G-EJKL", "Airworthiness Review")
        submit(page, page.get_by_role("button", name="Start an Airworthiness Review of G-EJKL"))
        rows = page.locator("main table.compact tbody > tr:not(.detail)")
        expect(rows).to_have_count(16)
        for index in range(16):
            form = reveal(rows.nth(index)).locator("form").first
            note = f"[Test evidence point {index + 1}]"
            result = "Finding" if index == 0 else "Satisfactory"
            values = {"result": result, "evidence": note}
            if index == 0:
                values["finding"] = "Logbook cover did not identify the aircraft"
            fill(form, values)
            submit(page, form.get_by_role("button"))
            expect(rows.nth(index)).to_contain_text(result)
        first = rows.first
        closure = reveal(first).get_by_role("button", name="Close Finding")
        fill(closure.locator("xpath=ancestor::form[1]"), {"closure": "Logbook cover corrected"})
        submit(page, closure)
        expect(first).to_contain_text("Logbook cover corrected")
        form = form_with(page, "assisted_by")
        fill(
            form,
            {
                "assisted_by": "[Test survey engineer]",
                "airframe_hours": "11206.8",
                "programme_discrepancy": "None Found",
            },
        )
        submit(page, form.get_by_role("button"))
        submit(
            page,
            page.get_by_role("button", name="Issue Airworthiness Review Certificate for G-EJKL"),
        )
        certificate = page.url
        expect(page.locator("main")).to_contain_text("UK.CAO.[Number]-ARC-0002")
        assert definition(page, "Date of Expiry") == "6 December 2027"
        assert definition(page, "Airframe Flight Hours at the Time of Review") == "11,206.8"
        name = definition(page, "Airworthiness Review Staff")
        page.get_by_role("link", name="The Review and Its Evidence", exact=True).click()
        review = page.url
        at_issue = definition(page, "Review Staff")
        assert name in at_issue

    with signed_in(chromium, live_site, admin) as page:
        page.goto("/staff/")
        page.get_by_role("link", name=name, exact=True).click()
        form = form_with(page, "full_name")
        fill(form, {"full_name": "Taylor Morgan"})
        submit(page, form.get_by_role("button"))
        expect(page.locator("main h1")).to_have_text("Taylor Morgan")

    with signed_in(chromium, live_site, reader) as page:
        page.goto(certificate)
        assert definition(page, "Airworthiness Review Staff") == name
        page.goto(review)
        expect(page.locator("main")).to_contain_text("[Test evidence point 16]")
        assert definition(page, "Review Staff") == at_issue


def test_release_cannot_be_entered_before_issue(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/release-to-service/")
        row = page.locator("main table.compact tbody tr:not(.detail)").filter(has_text=LEGACY_WORK)
        link = f"Record the Certificate, G-ABCD, {LEGACY_WORK}"
        expect(row).to_contain_text("11 November 2026")
        reveal(row).get_by_role("link", name=link, exact=True).click()
        form = form_with(page, "reference")
        expect(form.locator('[name="reference"]')).to_have_value(LEGACY_REFERENCE)
        fill(
            form,
            {
                "kind": "Independent Certifying Staff",
                "issuer_name": "Test Engineer",
                "licence": "TEST-B12",
                "issued_on": "2026-11-13",
                "recorded_on": "2026-11-14",
            },
        )
        submit(page, form.get_by_role("button"))
        expect(page.get_by_role("alert")).to_contain_text(
            "Use the Day the Release Was Already Entered in the Records"
        )
        fill(form, {"recorded_on": ""})
        submit(page, form.get_by_role("button"))
        expect(page.get_by_role("alert")).to_contain_text("On or After the Day It Was Issued")
        page.goto("/release-to-service/")
        expect(row).to_contain_text("11 November 2026")
        expect(reveal(row).get_by_role("link", name=link, exact=True)).to_be_visible()


def test_grounded_release_can_only_be_retained_as_historical_evidence(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/defects/")
        page.get_by_role("link", name="Record a Defect", exact=True).click()
        defect = form_with(page, "found_on")
        fill(
            defect,
            {
                "aircraft": "G-ABCD",
                "title": "Test grounding defect",
                "found_on": "2026-10-22",
                "chapter": "71",
                "system": "Engine",
                "decision": "Not Deferrable",
                "decided_on": "2026-10-22",
            },
        )
        submit(page, defect.get_by_role("button"))
        expect(page.locator("main")).to_contain_text("Test grounding defect")

        page.goto("/release-to-service/")
        certificates = page.get_by_role("table").filter(
            has=page.get_by_role("columnheader", name="In Records")
        )
        row = certificates.get_by_role("row").filter(has_text="Right Main Tyre Replaced")
        reveal(row).get_by_role("link", name="Record the Certificate, G-ABCD").click()
        page.get_by_role("link", name="Retain Unverified Historical Evidence").click()
        evidence = form_with(page, "source")
        fill(
            evidence,
            {
                "reference": "TEST-GROUNDED",
                "issuer_name": "Test Engineer",
                "issued_on": "2026-10-22",
                "source": "Signed work sheet",
            },
        )
        submit(page, evidence.get_by_role("button"))
        expect(page.get_by_role("heading", name="Unverified Historical Evidence")).to_be_visible()
        expect(page.get_by_role("row").filter(has_text="TEST-GROUNDED")).to_contain_text(
            "Signed work sheet"
        )
        expect(row).to_contain_text("Due 21 November 2026")
