"""Dispatch through the roster, with text conflict and handover evidence."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import save, signed_in
from tests.e2e.conftest import Account
from tests.e2e.test_records import _record_critical_card_completion

DAY = "/staffing/dispatch/?day=2026-11-18"
INCOMING = "[Browser Test Continuing Airworthiness Manager]"
PACKAGE = "WP-TEST-DISPATCH"


def test_dispatch_moves_work_and_retains_the_incoming_acknowledgement(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    _, manager, _, planner, _ = personas["your-organisation"]
    old_shift = "Sam Patel · Day Dispatch, Bay 2 · 18 Nov 08:00"
    new_shift = f"{INCOMING} · Evening Dispatch, Bay 2 · 18 Nov 18:30"
    with signed_in(chromium, live_site, planner, width=390) as page:
        _record_critical_card_completion(page, PACKAGE, "Sam Patel", with_dispatch_card=True)
        page.goto("/staffing/roster/")
        for person, name, starts, ends in (
            ("Sam Patel", "Day Dispatch", "08:00", "19:00"),
            (INCOMING, "Evening Dispatch", "18:30", "23:00"),
        ):
            page.get_by_role("link", name="Add Shift", exact=True).click()
            save(
                page,
                "Add Shift",
                {
                    "approval": "Part-CAO, UK.CAO.[Number]",
                    "person": person,
                    "area": "Bay 2",
                    "shift_name": name,
                    "maintenance": "on",
                    "starts_at": f"2026-11-18T{starts}",
                    "ends_at": f"2026-11-18T{ends}",
                    "break_minutes": "30",
                },
                name,
            )
        page.get_by_role("link", name="Dispatch", exact=True).click()
        expect(page).to_have_url(live_site + "/staffing/dispatch/")
        page.get_by_role("link", name="Next Day", exact=True).click()
        expect(page.get_by_role("heading", name="19 November 2026")).to_be_visible()
        page.get_by_role("link", name="Previous Day", exact=True).click()
        expect(page).to_have_url(live_site + DAY)
        page.get_by_role("link", name="Record Break", exact=True).click()
        save(
            page,
            "Record Break",
            {
                "shift": old_shift,
                "starts_at": "2026-11-18T12:00",
                "ends_at": "2026-11-18T12:30",
                "note": "Protected meal break",
            },
            "Protected meal break",
        )
        page.get_by_role("link", name="Record Turnaround", exact=True).click()
        save(
            page,
            "Record Turnaround",
            {
                "package": PACKAGE,
                "starts_at": "2026-11-18T11:00",
                "ends_at": "2026-11-18T21:00",
                "note": "Bay 2 arrival and return window",
            },
            "Bay 2 arrival and return window",
        )
        for card, reason in (
            ("Test Landing Light Card", "Original inspection slot"),
            ("Test Dispatch Cover Card", "Concurrent corrective work"),
        ):
            page.get_by_role("link", name="Assign Work", exact=True).click()
            save(
                page,
                "Assign Work",
                {
                    "card": f"{PACKAGE} · {card}",
                    "shift": old_shift,
                    "starts_at": "2026-11-18T12:15",
                    "ends_at": "2026-11-18T13:00",
                    "reason": reason,
                },
                reason,
            )
        expect(page.locator(".dispatch-block").first).to_be_visible()
        page.get_by_role("link", name="Go to Dispatch Details").focus()
        page.keyboard.press("Enter")
        expect(page.get_by_role("heading", name="Dispatch Details")).to_be_focused()
        expect(page.get_by_text("Overlaps a recorded break", exact=True)).to_have_count(2)
        expect(
            page.get_by_text(f"Overlaps assignment {PACKAGE} · Test Dispatch Cover Card")
        ).to_be_visible()
        expect(page.get_by_text("Long Shift", exact=True)).to_have_count(2)
        expect(page.get_by_text("Independent inspection outstanding", exact=False)).to_be_visible()
        move = page.get_by_role("link", name="Move Assignment for Test Landing Light Card")
        move_url = move.get_attribute("href")
        assert move_url
        move.click()
        save(
            page,
            "Move Assignment for Test Landing Light Card",
            {
                "shift": new_shift,
                "starts_at": "2026-11-18T19:00",
                "ends_at": "2026-11-18T20:00",
                "reason": "Moved to evening inspector after day shift",
            },
            "Moved to evening inspector after day shift",
        )
        expect(page.get_by_text("Overlaps a recorded break", exact=True)).to_have_count(1)
        expect(page.get_by_text("Original inspection slot", exact=False)).to_be_visible()
        expect(page.get_by_text(f"Moved to: {INCOMING}", exact=False)).to_be_visible()

        page.get_by_role("link", name="Hand Over Test Landing Light Card").click()
        save(
            page,
            "Record Handover",
            {
                "outgoing": "Sam Patel",
                "incoming": INCOMING,
                "handed_at": "2026-11-18T18:45",
                "stage": (
                    "Landing light installed, function check and independent inspection still due"
                ),
                "parts": "Lockout tag retained in Bay 2",
            },
            "Awaiting Acknowledgement",
        )
        expect(page.get_by_text("Planned Overlap: 30 of 15 Minutes")).to_be_visible()
        expect(page.get_by_role("link", name="Acknowledge Handover")).to_have_count(0)
    with signed_in(chromium, live_site, manager) as page:
        page.goto(DAY)
        page.get_by_role("link", name="Acknowledge Handover").click()
        save(page, "Acknowledge Handover", {}, f"Acknowledged by {INCOMING}")
        expect(page.get_by_text("Awaiting Acknowledgement")).to_have_count(0)
        expect(
            page.get_by_text("Landing light installed, function check", exact=False)
        ).to_be_visible()
        expect(page.get_by_text("Lockout tag retained in Bay 2", exact=False)).to_be_visible()
    with signed_in(chromium, live_site, personas["second-organisation"][3]) as page:
        page.goto(DAY)
        expect(page.locator("main")).not_to_contain_text(PACKAGE)
        expect(page.locator("main")).not_to_contain_text("Protected meal break")
        response = page.goto(move_url)
        assert response is not None and response.status == 404
