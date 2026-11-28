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


def test_goods_in_hands_off_to_stores_once(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/goods-in/receive/")
        item = "Test Sealant for Stores"
        save(
            page,
            "Record Receipt",
            {
                "item": item,
                "received_on": "2026-11-18",
                "classification": "Material",
                "source": "Sample Distributor",
                "item_reference": "Sample batch 2841",
                "quantity": "3",
                "delivery_reference": "TEST-STORES-01",
                "release_document": "Conformity statement as received",
                "shelf_life_to": "2026-11-30",
            },
            item,
        )
        receipt_url = page.url
        for check in CHECKS:
            page.get_by_role("link", name="Record a Check").click()
            save(
                page,
                "Record a Check",
                {
                    "check": check,
                    "outcome": "Pass",
                    "checked_on": "2026-11-18",
                    "evidence": f"Sample inspection record for {check}",
                },
                f"Sample inspection record for {check}",
            )
        page.get_by_role("link", name="Record the Disposition").click()
        decision_url = page.url
        form = form_with(page, "destination")
        fill(
            form,
            {
                "approval": "Part-CAO",
                "inspector": "Chris Moore",
                "inspector_authority": "Sample RI-6",
                "inspected_on": "2026-11-18",
                "disposition_on": "2026-11-18",
                "outcome": "Accepted into Stores",
                "destination": "Sample Shelf B",
                "evidence": "Sample Stores transfer ST-01",
                "document_kind": "Conformity Evidence",
                "document_reference": "Sample Document Store / COC-2841",
                "evidence_basis": "Sample Sealant Specification",
            },
        )
        submit(page, form.get_by_role("button", name="Record the Disposition"))
        expect(page.get_by_role("alert")).to_contain_text("Give the Manufacturing Source")
        fill(
            form,
            {
                "manufacturing_source": "Sample Factory",
                "material_supplier_source": "Supplier Named on Sample Statement",
            },
        )
        submit(page, form.get_by_role("button", name="Record the Disposition"))
        expect(page).to_have_url(receipt_url)
        page.get_by_role("link", name="View Stores Entry").click()
        assert definition(page, "Item Reference") == "Sample batch 2841"
        assert definition(page, "Received Quantity") == "3"
        assert definition(page, "Stock Location") == "Sample Shelf B"
        assert definition(page, "Evidence Reference") == "Sample Document Store / COC-2841"
        assert definition(page, "Manufacturing Source") == "Sample Factory"
        assert (
            definition(page, "Supplier Source on Material Evidence")
            == "Supplier Named on Sample Statement"
        )
        page.get_by_role("link", name="View Goods In Receipt TEST-STORES-01").click()
        expect(page).to_have_url(receipt_url)
        page.goto(decision_url)
        expect(page).to_have_url(receipt_url)
        page.goto("/stores/")
        expect(page.get_by_role("link", name=item, exact=True)).to_have_count(1)


def test_goods_in_returns_the_received_line_with_its_evidence(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/goods-in/receive/")
        item = "Test Oil Returned to Supplier"
        save(
            page,
            "Record Receipt",
            {
                "item": item,
                "received_on": "2026-11-16",
                "classification": "Material",
                "source": "Sample Oil Supplier",
                "item_reference": "Sample batch R-921",
                "quantity": "2",
                "delivery_reference": "TEST-RETURN-01",
                "release_document": "Sample delivery document with no conformity statement",
            },
            item,
        )
        page.get_by_role("link", name="Record a Check").click()
        save(
            page,
            "Record a Check",
            {
                "check": "Release Document",
                "outcome": "Fail",
                "checked_on": "2026-11-17",
                "evidence": "Sample delivery document lacks the conformity statement",
            },
            "Sample delivery document lacks the conformity statement",
        )
        page.get_by_role("link", name="Record the Disposition").click()
        save(
            page,
            "Record the Disposition",
            {
                "approval": "Part-CAO",
                "inspector": "Chris Moore",
                "inspector_authority": "Sample RI-6",
                "inspected_on": "2026-11-17",
                "disposition_on": "2026-11-18",
                "outcome": "Returned to Supplier",
                "destination": "Sample Oil Supplier",
                "evidence": "Sample return note RTV-01",
            },
            "Sample return note RTV-01",
        )
        assert definition(page, "Disposition") == "Returned to Supplier"
        assert definition(page, "Item Reference") == "Sample batch R-921"
        assert (
            definition(page, "Release Document Shown on Arrival")
            == "Sample delivery document with no conformity statement"
        )
        expect(page.get_by_role("link", name="View Stores Entry")).to_have_count(0)
        page.goto("/stores/")
        expect(page.get_by_role("link", name=item, exact=True)).to_have_count(0)
