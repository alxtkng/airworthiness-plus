"""Goods In from the record pages under the primary sample maintenance approval."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import definition, fill, form_with, save, signed_in, submit
from tests.e2e.conftest import Account
from tests.test_receiving import CHECKS


def test_goods_in_can_receive_check_and_quarantine(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/goods-in/")
        page.get_by_role("link", name="Receive an Item", exact=True).click()
        save(
            page,
            "Record Receipt",
            {
                "item": "Test Owner Supplied Alternator",
                "received_on": "2026-11-18",
                "classification": "Serviceable Component",
                "source": "Owner Supplied",
                "item_reference": "T-1, serial 23",
                "quantity": "1",
                "delivery_reference": "TEST-RECEIVE-01",
                "release_document": "Claimed CAA Form 1",
            },
            "Test Owner Supplied Alternator",
        )
        page.get_by_role("link", name="Record a Check", exact=True).click()
        save(
            page,
            "Record a Check",
            {
                "check": CHECKS[-1],
                "outcome": "Fail",
                "checked_on": "2026-11-18",
                "evidence": "The serial number does not match the item",
            },
            "The serial number does not match the item",
        )
        page.get_by_role("link", name="Record the Disposition", exact=True).click()
        form = form_with(page, "destination")
        fill(
            form,
            {
                "approval": "Part-CAO",
                "inspector": "Chris Moore",
                "inspector_authority": "Sample RI-6",
                "inspected_on": "2026-11-18",
                "disposition_on": "2026-11-18",
                "outcome": "Returned to Supplier",
                "destination": "Segregated Bay",
                "evidence": "Document serial mismatch",
            },
        )
        submit(page, form.get_by_role("button", name="Record the Disposition"))
        expect(page.get_by_role("alert")).to_contain_text("Must Go to Quarantine")
        expect(form.locator('[name="destination"]')).to_have_value("Segregated Bay")
        fill(form, {"outcome": "Quarantined"})
        submit(page, form.get_by_role("button", name="Record the Disposition"))
        assert definition(page, "Disposition") == "Quarantined"
        assert definition(page, "Location or Recipient") == "Segregated Bay"
        assert definition(page, "Receiving Inspector") == "Chris Moore"
        expect(page.get_by_role("link", name="Record the Disposition")).to_have_count(0)
