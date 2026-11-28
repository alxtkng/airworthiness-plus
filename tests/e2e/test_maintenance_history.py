"""Faceted maintenance history from normal aircraft and planning screens."""

from playwright.sync_api import Browser, Page, expect

from tests.e2e.browser import choose_aircraft, fill, save, signed_in, submit
from tests.e2e.conftest import Account


def _record(page: Page, aircraft: str, title: str, chapter: str, section: str) -> str:
    page.goto("/defects/")
    page.get_by_role("link", name="Record a Defect", exact=True).click()
    save(
        page,
        "Record Defect",
        {
            "aircraft": aircraft,
            "title": title,
            "found_on": "2026-11-17",
            "chapter": chapter,
            "section": section,
            "system": "Synthetic equipment",
            "decision": "Deferred",
            "basis": "Pilot-in-Command",
            "decided_on": "2026-11-18",
            "rectification": "Test fastener replaced",
            "closed_on": "2026-11-18",
        },
        title,
    )
    return page.url


def test_maintenance_history_combines_ata_and_aircraft_with_separate_text_filters(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        detail = _record(page, "G-FMNO", "Seat buckle loose", "25", "21")
        _record(page, "G-FMNO", "Seat cushion worn", "25", "22")
        _record(page, "G-FMNO", "Cabin lamp dim", "33", "")
        _record(page, "G-CDEF", "Other aircraft seat buckle loose", "25", "21")
        page.goto("/work-packages/")
        page.get_by_role("link", name="Maintenance History", exact=True).click()
        form = page.get_by_role("form", name="Maintenance History Filters")
        values = {
            "aircraft": "G-FMNO",
            "ata": "25",
            "from_date": "2026-11-17",
            "to_date": "2026-11-17",
            "state": "Closed",
            "source": "Defects",
            "record_type": "Defect",
        }
        fill(form, values)
        search = form.get_by_role("button", name="Search History")
        form.get_by_label("Corrective Action").focus()
        page.keyboard.press("Tab")
        expect(search).to_be_focused()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        expect(page.get_by_role("link", name="Seat buckle loose", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="Seat cushion worn", exact=True)).to_be_visible()
        expect(page.get_by_role("link", name="Cabin lamp dim", exact=True)).to_have_count(0)
        expect(page.get_by_role("link", name="Other aircraft seat buckle loose")).to_have_count(0)

        fill(form, {"ata": "25-21", "report": "fastener"})
        submit(page, search)
        expect(page.get_by_text("No Records Match the Filters")).to_be_visible()
        fill(form, {"report": "buckle", "rectification": "fastener"})
        submit(page, search)
        expect(page.get_by_role("link", name="Seat cushion worn", exact=True)).to_have_count(0)
        result = page.get_by_role("link", name="Seat buckle loose", exact=True)
        result.focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        expect(page).to_have_url(detail)
        choose_aircraft(page, "G-FMNO", "Maintenance History")
        expect(page.get_by_role("link", name="Seat buckle loose", exact=True)).to_be_visible()
        aircraft_history = page.url

    with signed_in(chromium, live_site, personas["second-organisation"][3]) as page:
        response = page.goto(aircraft_history)
        assert response is not None and response.status == 404
        page.goto("/maintenance-history/?ata=25-21")
        expect(page.get_by_role("link", name="Seat buckle loose", exact=True)).to_have_count(0)
