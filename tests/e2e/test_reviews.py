"""Review staff, externally issued certificates, extensions and retained evidence."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import (
    choose_aircraft,
    definition,
    fill,
    form_with,
    reveal,
    save,
    signed_in,
    submit,
)
from tests.e2e.conftest import Account


def test_review_staff_authorisation_and_restoration(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/review-staff/")
        person = "[Planning and Records Name]"
        save(
            page,
            "Record Review Staff",
            {
                "user": person,
                "authorisation_reference": "TEST-AR-018",
                "accepted_on": "2023-04-12",
                "months_involved": "2",
                "last_review_before_records": "2025-08-01",
            },
            "TEST-AR-018",
        )
        row = page.locator("main tbody tr:not(.detail)").filter(has_text=person)
        expect(row).to_contain_text("Restoration Needed")
        involvement = reveal(row).get_by_role("button", name="Save", exact=True)
        fill(involvement.locator("xpath=ancestor::form[1]"), {"months": "3"})
        submit(page, involvement)
        expect(row).to_contain_text("3, Recorded 18 November 2026")
        restore = reveal(row).get_by_role("button", name="Record Restoration")
        form = restore.locator("xpath=ancestor::form[1]")
        form.locator('[name="supervisor"]').select_option(label="[Authorisation Reference 1]")
        fill(form, {"on": "2026-11-18"})
        submit(page, restore)
        page.reload()
        expect(row).to_contain_text("Restored 18 November 2026 Under Lucy Grant")


def test_external_review_certificate_and_extension_copy(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-EJKL", "Airworthiness Review")
        address = page.url
        save(
            page,
            "Record Certificate",
            {
                "reference": "TEST-EXTERNAL-AR",
                "issued_elsewhere_by": "Test Review Organisation",
                "issued_on": "2024-11-18",
                "valid_to": "2025-11-18",
                "airframe_hours": "10600.0",
            },
            "TEST-EXTERNAL-AR",
        )
        page.get_by_role("link", name="TEST-EXTERNAL-AR", exact=True).click()
        assert definition(page, "Date of Issue") == "18 November 2024"

        page.goto(address)
        form = form_with(page, "managed_for_12_months")
        for checkbox in form.get_by_role("checkbox").all():
            checkbox.check()
        submit(page, form.get_by_role("button"))
        row = page.locator("main tr:not(.detail)").filter(has_text="Extension 1")
        expect(row).to_contain_text("6 December 2027")
        copy = reveal(row).get_by_role("button", name="Record Copy Sent", exact=True)
        fill(copy.locator("xpath=ancestor::form[1]"), {"on": "2026-11-18"})
        submit(page, copy)
        expect(row).to_contain_text("Sent 18 November 2026")


def test_certificate_copy_and_void_are_retained(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    _, _, reviewer, planner, _ = personas["your-organisation"]
    reference = "UK.CAO.[Number]-ARC-0001"
    with signed_in(chromium, live_site, planner) as page:
        choose_aircraft(page, "G-CDEF", "Airworthiness Review")
        address = page.url
        row = page.locator("main tr:not(.detail)").filter(has_text=reference)
        copy = reveal(row).get_by_role("button", name="Record Copy Sent", exact=True)
        fill(copy.locator("xpath=ancestor::form[1]"), {"on": "2026-11-18"})
        submit(page, copy)
        expect(row).to_contain_text("Sent 18 November 2026")
    with signed_in(chromium, live_site, reviewer) as page:
        page.goto(address)
        page.get_by_role("link", name=reference, exact=True).click()
        save(
            page,
            "Void Certificate",
            {"reason": "Test invalid certificate"},
            "Test invalid certificate",
        )
        expect(page.get_by_role("alert")).to_contain_text("Void")
        assert definition(page, "Certificate Reference") == reference
