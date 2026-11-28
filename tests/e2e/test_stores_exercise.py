"""Work through the sample lookup on the normal Stores page at phone width."""

import re

from playwright.sync_api import Browser, expect

from airworthiness_plus.accounts.roles import Role
from tests.e2e.browser import signed_in
from tests.e2e.conftest import Account


def test_stores_lookup_exercise_resumes_at_saved_question(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    reader = next(
        account for account in personas["your-organisation"] if account.role == Role.READ_ONLY
    )
    with signed_in(chromium, live_site, reader) as page:
        page.set_viewport_size({"width": 320, "height": 700})
        page.goto("/stores/")
        page.get_by_role("link", name="Practise Stock Lookup").press("Enter")

        expect(
            page.get_by_role("row", name=re.compile(r"\bZRH Main 7 0 7 Serviceable$"))
        ).to_be_visible()
        expect(page.get_by_role("row", name=re.compile(r"\bZRH 8 0 8$"))).to_be_visible()
        expect(page.get_by_role("row", name=re.compile(r"\bNetwork 10 0 10$"))).to_be_visible()
        expect(
            page.get_by_role("row", name=re.compile(r"\bGVA Main 0 0 0 Serviceable$"))
        ).to_be_visible()

        answer = page.get_by_label("Quantity")
        answer.fill("7")
        answer.press("Enter")
        expect(
            page.get_by_role("heading", name="How many items are on hand across ZRH?")
        ).to_be_visible()

        page.get_by_role("link", name="Back to Stock").press("Enter")
        page.get_by_role("link", name="Practise Stock Lookup").press("Enter")
        expect(
            page.get_by_role("heading", name="How many items are on hand across ZRH?")
        ).to_be_visible()
        answer.fill("8")
        answer.press("Enter")
        expect(
            page.get_by_role("heading", name="How many items are on hand across the network?")
        ).to_be_visible()
        answer.fill("10")
        answer.press("Enter")
        expect(page.get_by_role("row", name=re.compile(r"\bNetwork 10 1 8$"))).to_be_visible()
        expect(
            page.get_by_role(
                "row", name="ZRH Quarantine 1 0 0 Quarantined — Identity check unresolved"
            )
        ).to_be_visible()
        answer.fill("8")
        answer.press("Enter")
        expect(page.get_by_role("heading", name="Exercise Complete")).to_be_visible()
