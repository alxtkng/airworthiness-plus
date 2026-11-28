"""The Stores posting contract for Goods In acceptances."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import definition, signed_in
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
