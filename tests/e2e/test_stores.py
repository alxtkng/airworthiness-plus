"""The Stores posting contract for Goods In acceptances."""

import re

from playwright.sync_api import Browser, Page, expect

from tests.e2e.browser import definition, fill, form_with, save, signed_in, submit
from tests.e2e.conftest import Account


def test_rx_002_awaits_stock_posting_with_zero_available(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][4]) as page:
        page.goto("/goods-in/")
        accepted = page.get_by_role("row").filter(
            has=page.get_by_role("cell", name="Accepted into Stores", exact=True)
        )
        accepted.get_by_role("link", name="Stabilator Trim Cable Assembly", exact=True).click()
        assert definition(page, "Delivery Line Reference") == "RX-002"
        assert definition(page, "Disposition") == "Accepted into Stores"
        receipt_url = page.url

        page.get_by_role("link", name="View Stores Entry", exact=True).click()
        entry_url = page.url
        assert definition(page, "Received Quantity") == "1"
        page.get_by_role("link", name="View Goods In Receipt RX-002", exact=True).click()
        expect(page).to_have_url(receipt_url)

        page.goto("/stores/")
        page.get_by_role("link", name="Stabilator Trim Cable Assembly", exact=True).click()
        expect(page).to_have_url(entry_url)
        expect(page.get_by_text("Awaiting Stock Posting", exact=True)).to_be_visible()
        assert definition(page, "Available Quantity") == "0"
        blockers = definition(page, "Posting Blockers").lower()
        assert "identity" in blockers
        assert "location" in blockers


APPOINTMENT = {
    "approval": "Part-CAO",
    "person": "[Browser Test Continuing Airworthiness Manager]",
    "starts_on": "2026-11-18",
    "ends_on": "2027-11-17",
    "exposition_reference": "Synthetic Stores procedure, revision 1",
    "authority": "Synthetic signed appointment",
}


def _appoint(page: Page, action: str) -> None:
    page.goto("/stores/appointments/")
    page.get_by_role("link", name="Record a Stores Appointment", exact=True).click()
    form = form_with(page, "authority")
    fill(form, {**APPOINTMENT, "action": action})
    submit(page, form.get_by_role("button", name="Record a Stores Appointment"))
    expect(page).to_have_url(re.compile(r"/stores/appointments/$"))


def test_stores_appointments_locations_posting_moves_counts_and_adjustment(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    """REQ-358 S04, S06, S08 and S11 through the signed-in routes, with synthetic data."""
    ours = personas["your-organisation"]
    with signed_in(chromium, live_site, ours[0]) as page:
        for action in (
            "Maintain Stores Locations",
            "Post Accepted Items to Stock",
            "Move Stock",
            "Count Stock",
            "Adjust Stock After a Count",
        ):
            _appoint(page, action)
        _appoint(page, "Count Stock")
        row = (
            page.get_by_role("row")
            .filter(has_text="Count Stock")
            .filter(has_text="[Browser Test Continuing Airworthiness Manager]")
        )
        row.first.get_by_role("link").click()
        form = form_with(page, "evidence")
        fill(form, {"evidence": "Synthetic duplicate appointment withdrawn"})
        submit(page, form.get_by_role("button"))
        expect(page.locator("main")).to_contain_text("Withdrawn 18 November 2026")

    with signed_in(chromium, live_site, ours[1]) as page:
        page.goto("/stores/locations/")
        page.get_by_role("link", name="Add a Stores Location", exact=True).click()
        form = form_with(page, "storage_conditions")
        fill(
            form,
            {
                "code": "TEST-E",
                "name": "Test Bay E",
                "kind": "Serviceable Store",
                "storage_conditions": "Dry, synthetic",
            },
        )
        page.get_by_label("Serviceable Component", exact=True).check()
        submit(page, form.get_by_role("button", name="Add a Stores Location"))
        expect(page.locator("main")).to_contain_text("Test Bay E")
        page.get_by_role("link", name="Withdraw TEST-E", exact=True).click()
        form = form_with(page, "evidence")
        fill(form, {"evidence": "Synthetic location taken out of use"})
        submit(page, form.get_by_role("button"))
        expect(page.locator("main")).to_contain_text("Withdrawn 18 November 2026")

        # RX-002: resolve the blockers, then post once. A duplicate submission changes nothing.
        page.goto("/stores/")
        page.get_by_role("link", name="Stabilator Trim Cable Assembly", exact=True).click()
        entry_url = page.url
        page.get_by_role("link", name="Record Posting Evidence", exact=True).click()
        form = form_with(page, "part_number")
        fill(
            form,
            {
                "unit": "Each",
                "quantity": "1",
                "manufacturer": "Synthetic Cable Maker",
                "part_number": "PN-TEST-713",
                "serial": "SN-TEST-863",
                "shelf_life_basis": "Not Applicable",
                "location": "BAY-A, Bay A, Serviceable Components",
                "evidence": "Synthetic mapping of the original CAA Form 1 in the RX-002 folder",
            },
        )
        submit(page, form.get_by_role("button", name="Record Posting Evidence"))
        assert definition(page, "Posting Blockers") == "None. Ready to Post"
        page.get_by_role("link", name="Post to Stock", exact=True).click()
        post_url = page.url
        button = page.get_by_role("button", name="Post to Stock", exact=True)
        submit(page, button)
        expect(page).to_have_url(entry_url)
        assert definition(page, "Posting Status") == "Posted to Stock"
        assert definition(page, "Available Quantity") == "1"
        page.go_back()
        if page.url == post_url and page.get_by_role("button", name="Post to Stock").count():
            submit(page, page.get_by_role("button", name="Post to Stock", exact=True))
        page.goto(entry_url)
        expect(page.get_by_role("row").filter(has_text="Opening posting")).to_have_count(1)

        # Engine oil: move 8 L of 24 L, count it, and keep 24 L in total.
        page.goto("/stores/")
        page.get_by_role("row").filter(has_text="BAY-C, Bay C").get_by_role(
            "link", name="Engine Oil", exact=True
        ).click()
        oil_url = page.url
        page.get_by_role("link", name="Move Stock", exact=True).click()
        form = form_with(page, "destination")
        fill(
            form,
            {
                "source": "BAY-C, Bay C, Oils and Materials",
                "destination": "OIL-2, Hangar Oil Store",
                "quantity": "8",
                "evidence": "Synthetic transfer note",
            },
        )
        submit(page, form.get_by_role("button", name="Move Stock"))
        expect(page).to_have_url(oil_url)
        custody = page.locator("main table").first
        expect(custody).to_contain_text("16 Litre")
        expect(custody).to_contain_text("8 Litre")
        assert definition(page, "On Hand") == "24 L (Litre)"
        page.get_by_role("link", name="Count Stock", exact=True).click()
        form = form_with(page, "counted")
        fill(
            form,
            {
                "location": "OIL-2, Hangar Oil Store",
                "counted": "8",
                "evidence": "Synthetic count",
            },
        )
        submit(page, form.get_by_role("button", name="Count Stock"))
        expect(page.locator("main")).to_contain_text("No Variance")

        # Bolts: the sample count of 46 against 50 is applied by an authorised adjustment.
        page.goto("/stores/")
        page.get_by_role("link", name="Bolts", exact=True).click()
        assert definition(page, "On Hand") == "50 (Each)"
        page.get_by_role("link", name="Adjust for Count 18 November 2026", exact=True).click()
        form = form_with(page, "evidence")
        fill(form, {"evidence": "Synthetic adjustment authority A-7"})
        submit(page, form.get_by_role("button", name="Adjust Stock After a Count"))
        assert definition(page, "On Hand") == "46 (Each)"


def test_stores_posting_works_by_keyboard_at_320_pixels(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    """REQ-358 S11. The quarantine hold is posted by keyboard on a narrow screen."""
    ours = personas["your-organisation"]
    with signed_in(chromium, live_site, ours[0]) as page:
        _appoint(page, "Post Accepted Items to Stock")
    with signed_in(chromium, live_site, ours[1], width=320) as page:
        page.goto("/stores/")
        link = page.get_by_role("link", name="Alternator", exact=True)
        link.focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        expect(page.get_by_text("Quarantine Hold, Details to Verify", exact=True)).to_be_visible()
        assert definition(page, "Available Quantity") == "0"
        blockers = definition(page, "Posting Blockers")
        assert "Quarantine Location to Verify" in blockers
        assert "Quarantine Tag Not Recorded" in blockers
        page.get_by_role("link", name="Record Posting Evidence", exact=True).click()
        form = page.locator("main form")
        form.get_by_label("Unit", exact=True).select_option(label="Each")
        form.get_by_label("Quantity", exact=True).fill("1")
        form.get_by_label("Location", exact=True).select_option(
            label="QUAR-1, Quarantine Store, Locked"
        )
        form.get_by_label("Quarantine Tag", exact=True).fill("Q-TEST-0042")
        form.get_by_label("Original Records and Evidence Relied On", exact=True).fill(
            "Synthetic hold verified in the locked cage"
        )
        button = page.get_by_role("button", name="Record Posting Evidence", exact=True)
        button.focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        page.get_by_role("link", name="Post the Quarantine Hold", exact=True).focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        page.get_by_role("button", name="Post the Quarantine Hold", exact=True).focus()
        with page.expect_navigation():
            page.keyboard.press("Enter")
        assert definition(page, "Posting Status") == "Quarantine Hold"
        assert definition(page, "On Hand") == "1 (Each)"
        assert definition(page, "Available Quantity") == "0"
        page.reload()
        assert definition(page, "Posting Status") == "Quarantine Hold"


def test_stores_reserves_issues_and_quarantines_a_maintenance_return(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    ours = personas["your-organisation"]
    with signed_in(chromium, live_site, ours[0]) as page:
        for action in (
            "Post Accepted Items to Stock",
            "Reserve Stock for a Work Card",
            "Issue Stock to Maintenance",
            "Accept Maintenance Returns to Quarantine",
            "Move Unreserved Stock to Quarantine",
        ):
            _appoint(page, action)
        certifier = APPOINTMENT["person"]
        page.goto("/staff/")
        page.get_by_role("link", name=certifier, exact=True).click()
        form = form_with(page, "staff_group")
        fill(form, {"staff_group": "Certifying Staff"})
        submit(page, form.get_by_role("button", name=f"Save the Record of {certifier}"))
        page.get_by_role("link", name="Record Maintenance Authorisation").click()
        save(
            page,
            "Save Authorisation",
            {
                "reference": "SYN-ALT-LIVE",
                "scope": "Part substitution approval for G-ABCD",
                "valid_from": "2026-11-18",
                "valid_to": "2026-11-20",
            },
            "SYN-ALT-LIVE",
        )

    with signed_in(chromium, live_site, ours[1]) as page:
        page.goto("/maintenance-data/add/")
        save(
            page,
            "Record Maintenance Data",
            {
                "title": "Synthetic Stores Parts Data",
                "author": "Synthetic Aircraft Maker",
                "kind": (
                    "Instructions for Continued Airworthiness, From a Type or "
                    "Supplementary Type Certificate Holder"
                ),
                "held": "on",
                "revision": "1",
                "revision_date": "2026-11-16",
                "check_due": "2026-11-30",
            },
            "Synthetic Stores Parts Data",
        )
        page.goto("/work-packages/")
        page.get_by_role("link", name="Build a Work Package").click()
        save(
            page,
            "Build a Work Package",
            {
                "aircraft": "G-ABCD",
                "reference": "WP-STORES-LIVE",
                "title": "Synthetic workshop installation",
                "location": "Bay A",
                "starts_on": "2026-11-18",
                "ends_on": "2026-11-19",
            },
            "WP-STORES-LIVE",
        )
        page.get_by_role("link", name="Link Work Order").click()
        save(
            page,
            "Link Work Order",
            {"order": "Landing Light Replacement (12 November 2026)"},
            "Landing Light Replacement",
        )
        page.get_by_role("link", name="Add Work Card").click()
        save(
            page,
            "Add Work Card",
            {
                "title": "Synthetic Installation Card",
                "data_set": "Synthetic Stores Parts Data",
                "instruction": "Chapter 33",
                "planned_hours": "2.0",
            },
            "Synthetic Installation Card",
        )
        package_url = page.url
        page.goto("/stores/")
        page.get_by_role("link", name="Stabilator Trim Cable Assembly", exact=True).click()
        entry_url = page.url
        page.get_by_role("link", name="Record Posting Evidence", exact=True).click()
        main_store = "BAY-A, Bay A, Serviceable Components"
        quarantine = "QUAR-1, Quarantine Store, Locked"
        save(
            page,
            "Record Posting Evidence",
            {
                "unit": "Each",
                "quantity": "1",
                "manufacturer": "Synthetic Cable Maker",
                "part_number": "PN-TEST-713",
                "serial": "SN-TEST-863",
                "shelf_life_basis": "Not Applicable",
                "location": main_store,
                "evidence": "Synthetic verified Form 1 mapping",
            },
            "None. Ready to Post",
        )
        page.get_by_role("link", name="Post to Stock", exact=True).click()
        save(page, "Post to Stock", {}, "Posted to Stock")
        reserve = {
            "source": main_store,
            "card": "WP-STORES-LIVE · G-ABCD · Synthetic Installation Card",
            "quantity": "1",
            "required_identity": "PN-TEST-713",
            "applicable_source": "Synthetic Parts Data revision 1, figure 33",
            "evidence": "Material requisition from workshop",
        }
        page.get_by_role("link", name="Reserve Stock", exact=True).click()
        save(page, "Reserve Stock", reserve, "Issued Package With an Open Written Order")
        page.goto(package_url)
        page.get_by_role("link", name="Issue Work Package").click()
        save(page, "Issue Work Package", {}, "Revision 1")
        page.goto(entry_url)
        page.get_by_role("link", name="Reserve Stock", exact=True).click()
        save(page, "Reserve Stock", reserve, "Reserved · Open")
        assert definition(page, "On Hand") == "1 (Each)"
        assert definition(page, "Reserved") == "1"
        assert definition(page, "Available Quantity") == "0"

        page.get_by_role("link", name="Quarantine Stock", exact=True).click()
        save(
            page,
            "Quarantine Stock",
            {
                "source": main_store,
                "destination": quarantine,
                "quantity": "1",
                "evidence": "Review integrity of the label",
            },
            "Less Unreserved Stock",
        )
        page.goto(entry_url)
        page.get_by_role("link", name="Release Reservation", exact=True).click()
        save(
            page,
            "Release Reservation",
            {"evidence": "Workshop changed its installation slot"},
            "Reservation Released",
        )
        assert definition(page, "Available Quantity") == "1"
        page.get_by_role("link", name="Approve an Alternate", exact=True).click()
        save(
            page,
            "Approve an Alternate",
            {
                "card": reserve["card"],
                "required_identity": "ORIGINAL-PART",
                "applicable_source": "Synthetic approved parts list revision 4",
                "authorisation": "SYN-ALT-LIVE · Part substitution approval for G-ABCD",
                "scope_confirmed": "on",
                "evidence": "Figure 33 approves PN-TEST-713 for this work card and aircraft",
            },
            "Applicable Approved Alternates",
        )
        page.get_by_role("link", name="Reserve Stock", exact=True).click()
        save(
            page,
            "Reserve Stock",
            {
                **reserve,
                "required_identity": "ORIGINAL-PART",
                "applicable_source": "Synthetic approved parts list revision 4",
                "substitution": (
                    "WP-STORES-LIVE · Synthetic Installation Card: PN-TEST-713 for ORIGINAL-PART"
                ),
            },
            "Reserved · Open",
        )
        expect(page.get_by_text("Alternate PN-TEST-713 approved by", exact=False)).to_be_visible()
        issue = page.get_by_role("link", name="Issue Reserved Stock", exact=True)
        issue_url = issue.get_attribute("href")
        assert issue_url
        issue.click()
        save(
            page,
            "Issue Reserved Stock",
            {"evidence": "Handed intact to the workshop"},
            "Issued to Maintenance",
        )
        assert definition(page, "On Hand") == "0 (Each)"
        assert definition(page, "Reserved") == "0"
        page.get_by_role("link", name="Return Stock to Quarantine", exact=True).click()
        save(
            page,
            "Return Stock to Quarantine",
            {"destination": quarantine, "evidence": "Opened packaging held for fresh inspection"},
            "Returned to Quarantine",
        )
        assert definition(page, "On Hand") == "1 (Each)"
        assert definition(page, "Available Quantity") == "0"
        page.get_by_role("link", name="Reserve Stock", exact=True).click()
        save(
            page,
            "Reserve Stock",
            {**reserve, "source": quarantine},
            "Does Not Hold Serviceable Stock",
        )

    with signed_in(chromium, live_site, personas["second-organisation"][1]) as page:
        response = page.goto(issue_url)
        assert response is not None and response.status == 404
