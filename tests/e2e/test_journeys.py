"""Navigation, saved form values, keyboard operation and export downloads."""

import json
import os
import re
from collections import deque
from io import StringIO
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from zipfile import ZipFile

import pytest
from django.core.management import call_command
from playwright.sync_api import Browser, Page, expect

from airworthiness_plus.accounts.roles import Role
from tests.accessibility_scan import violations
from tests.e2e.browser import fill, form_with, reveal, signed_in, submit
from tests.e2e.conftest import Account

PRIMARY = "your-organisation"
# Light, dark and high contrast as the device asks for it (REQ-405, REQ-406).
SIDEWAYS = "document.documentElement.scrollWidth > document.documentElement.clientWidth"
SCHEMES = (("light", "no-preference"), ("dark", "no-preference"), ("light", "more"))
SECONDARY = "second-organisation"
FLEETS = {
    PRIMARY: ("G-DGHI", "G-BXYZ", "G-ABCD", "G-EJKL", "G-FMNO", "G-CDEF"),
    SECONDARY: ("G-JNOP", "G-KQRS"),
}

# Older pages still offer some controls that are unavailable to the role.
# See Decisions.md, “What each role is shown”. These are ordinary link clicks.
MANAGER = Role.CONTINUING_AIRWORTHINESS_MANAGER
PLANNER = Role.PLANNING_AND_RECORDS
RESTRICTED_LINKS = (
    (r"/records-export/", set(Role) - {Role.READ_ONLY}),
    (r"/imports/[^/]+/check/", {MANAGER, PLANNER, Role.AIRWORTHINESS_REVIEW_STAFF}),
    (r"/directives/add/", {MANAGER, PLANNER}),
    (r"/directive-decisions/[^/]+/terminate/", {MANAGER}),
    (r"/maintenance-data/add/", {MANAGER, PLANNER}),
    (r"/aircraft/[^/]+/(?:hours-and-cycles|counters|unserviceable|work/add)/", {MANAGER, PLANNER}),
    (r"/aircraft/[^/]+/programme/(?:set-up|tasks/add)/", {MANAGER}),
    (r"/aircraft/[^/]+/directives/[^/]+/decide/", {MANAGER}),
    (r"/directive-decisions/[^/]+/comply/", {MANAGER, PLANNER}),
)


def sign_out(page: Page) -> None:
    submit(page, page.get_by_role("button", name="Sign Out", exact=True))
    expect(page.get_by_role("heading", name="Sign In", exact=True)).to_be_visible()


def fleet(page: Page, organisation: str) -> None:
    page.goto("/")
    rows = page.locator("main tbody tr:not(.detail)")
    expect(rows).to_have_count(len(FLEETS[organisation]))
    assert tuple(rows.locator('a[href^="/aircraft/"]').all_text_contents()) == FLEETS[organisation]
    if organisation == PRIMARY:
        for registration, remaining in (
            ("G-EJKL", "18 Days"),
            ("G-ABCD", "12.4 Hours"),
            ("G-ABCD", "15 Days"),
            ("G-BXYZ", "9 Days"),
            ("G-FMNO", "78 Days"),
            ("G-CDEF", "358 Days"),
        ):
            expect(rows.filter(has_text=registration)).to_contain_text(remaining)
    else:
        expect(rows.filter(has_text="G-JNOP")).to_contain_text("2,406.5")
        expect(rows.filter(has_text="G-KQRS")).to_contain_text("5,120.0")


@pytest.mark.parametrize("organisation", FLEETS)
@pytest.mark.parametrize("role", list(Role), ids=str)
def test_persona_can_open_its_pages(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    organisation: str,
    role: Role,
) -> None:
    account = next(person for person in personas[organisation] if person.role == role)
    with signed_in(
        chromium,
        live_site,
        account,
        width=390,
        returning=organisation == PRIMARY and role == Role.READ_ONLY,
    ) as page:
        fleet(page, organisation)
        if not os.environ.get("AIRWORTHINESS_E2E_FULL"):
            page.goto("/dashboard/")
            expect(page.locator("main")).to_contain_text("Continuing Airworthiness")
            sign_out(page)
            return
        pending = deque(["/dashboard/"])
        seen: set[str] = set()
        opened: set[str] = set()
        while pending:
            path = pending.popleft()
            if path in seen:
                continue
            seen.add(path)
            response = page.goto(path, wait_until="domcontentloaded")
            assert response is not None, path
            if response.status == 403:
                assert any(
                    re.fullmatch(pattern, path) and role not in allowed
                    for pattern, allowed in RESTRICTED_LINKS
                ), (path, role)
                continue
            assert response.ok and page.url == urljoin(live_site, path), (path, response.status)
            expect(page.locator("main")).to_be_visible()
            expect(page.locator("aside .roles")).to_have_text(str(role))
            opened.add(path)
            # Date pagination is exercised by the dispatch journey. Following both
            # directions here adds another day on every iteration.
            for href in page.locator('a[href]:not([rel="prev"]):not([rel="next"])').evaluate_all(
                "(links) => links.map(link => link.getAttribute('href'))"
            ):
                target = urlsplit(urljoin(page.url, href))
                if target.netloc != urlsplit(live_site).netloc or target.fragment:
                    continue
                pending.append(target.path + (f"?{target.query}" if target.query else ""))
        assert {"/", "/dashboard/", "/settings/", "/staff/", "/customers/"} <= opened
        assert ("/users/" in opened) == (role == Role.ADMINISTRATOR)
        page.goto("/dashboard/")
        sign_out(page)


@pytest.mark.parametrize("organisation", FLEETS)
def test_customer_can_be_saved_and_updated(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]], organisation: str
) -> None:
    with signed_in(chromium, live_site, personas[organisation][3]) as page:
        page.goto("/customers/")
        page.get_by_role("link", name="Add a Customer", exact=True).click()
        form = form_with(page, "name")
        name = "O\u2019Neill & García \u2013 Test Syndicate"
        fill(
            form,
            {"name": name, "kind": "Syndicate", "members": "3", "customer_since": "2026-11-18"},
        )
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main h1")).to_have_text(name)
        expect(form.locator('[name="members"]')).to_have_value("3")
        fill(form, {"members": "4"})
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(form.locator('[name="members"]')).to_have_value("4")


def test_invalid_alert_lead_time_preserves_settings(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas[PRIMARY][0]) as page:
        page.goto("/settings/")
        form = form_with(page, "due_soon_hours")
        old = form.locator('[name="due_soon_hours"]').input_value()
        form.locator('[name="review_alert"]').check()
        fill(form, {"review_alert_days": "20", "due_soon_hours": "15.0"})
        submit(page, form.get_by_role("button"))
        expect(page.get_by_role("alert")).to_contain_text("More Days Than the Calendar Lead Time")
        page.goto("/settings/")
        expect(form.locator('[name="due_soon_hours"]')).to_have_value(old)
        expect(form.locator('[name="review_alert"]')).not_to_be_checked()
        fill(form, {"due_soon_hours": "15.0"})
        submit(page, form.get_by_role("button"))
        page.reload()
        assert float(form.locator('[name="due_soon_hours"]').input_value()) == 15.0


def test_fleet_row_can_be_opened_at_phone_width_by_keyboard(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas[PRIMARY][4], width=390) as page:
        fleet(page, PRIMARY)
        skip = page.get_by_role("link", name="Skip to Main Content")
        page.keyboard.press("Tab")
        expect(skip).to_be_focused()
        page.keyboard.press("Enter")
        row = page.locator("main tbody tr").first
        opener = row.get_by_role("button", name="Show Details")
        for _ in range(70):
            if opener.evaluate("(element) => element === document.activeElement"):
                break
            page.keyboard.press("Tab")
        expect(opener).to_be_focused()
        page.keyboard.press("Enter")
        expect(opener).to_have_attribute("aria-expanded", "true")
        expect(row.locator("xpath=following-sibling::tr[1]")).to_be_visible()
        page.keyboard.press("Space")
        expect(opener).to_have_attribute("aria-expanded", "false")


def test_aircraft_and_organisation_exports(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]], tmp_path: Path
) -> None:
    with signed_in(chromium, live_site, personas[PRIMARY][0]) as page:
        page.goto("/records-export/")
        aircraft = page.locator("main tbody tr:not(.detail)").filter(has_text="G-CDEF")
        for stem, button, registrations in (
            (
                "aircraft",
                reveal(aircraft).get_by_role("button", name="Export the Record of G-CDEF"),
                {"G-CDEF"},
            ),
            (
                "organisation",
                page.get_by_role("button", name="Export the Record of [Your Organisation]"),
                {*FLEETS[PRIMARY], "G-HKLM"},
            ),
        ):
            with page.expect_download() as downloaded:
                button.click()
            path = tmp_path / f"{stem}.zip"
            downloaded.value.save_as(path)
            verified = StringIO()
            call_command("verify_export", str(path), stdout=verified)
            digest = verified.getvalue().splitlines()[-1].rsplit(" ", 1)[-1]
            assert re.fullmatch(r"[0-9a-f]{64}", digest)
            page.reload()
            expect(page.locator("main")).to_contain_text(digest)
            with ZipFile(path) as archive:
                records = json.loads(archive.read("records/aircraft_aircraft.json"))
                assert {record["registration"] for record in records} == registrations
                certificates = json.loads(archive.read("records/reviews_certificate.json"))
                certificate = next(
                    item for item in certificates if item["reference"] == "UK.CAO.[Number]-ARC-0001"
                )
                assert certificate["valid_to"] == "2027-12-02"
                assert float(certificate["airframe_hours"]) == 7720.0


@pytest.mark.parametrize("organisation", FLEETS)
def test_import_is_checked_against_source_by_a_second_person(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    organisation: str,
) -> None:
    _, manager, _, planner, _ = personas[organisation]
    content = (
        "Aircraft Registration,Type Rating,Aircraft Serial Number,Aircraft Manufacturer,"
        "Manufacturer's Designation,Owned By,Totals Dated,Airframe Hours,Airframe Cycles\n"
        "G-TCSV,Piper PA-28 Series (Lycoming),TEST-302,[Test Maker],[Test Type],"
        "[Test Owner],2026-11-18,202.3,55\n"
    )
    with signed_in(chromium, live_site, manager) as page:
        page.goto("/imports/")
        form = form_with(page, "file")
        fill(form, {"kind": "Aircraft and Totals", "source": "[Test logbook]"})
        form.locator('[name="file"]').set_input_files(
            {"name": "aircraft.csv", "mimeType": "text/csv", "buffer": content.encode()}
        )
        submit(page, form.get_by_role("button", name="Load File"))
        expect(page.locator("main h1")).to_have_text("Verification Report")
        report = page.url
        expect(page.locator("main")).to_contain_text("G-TCSV")
    with signed_in(chromium, live_site, planner) as page:
        page.goto(report)
        form = page.locator("main form").first
        boxes = form.get_by_role("checkbox")
        assert boxes.count() > 2
        for box in boxes.all():
            box.check()
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main")).to_contain_text("100%")
        page.goto("/")
        expect(page.get_by_role("link", name="G-TCSV", exact=True)).to_be_visible()


@pytest.mark.parametrize("organisation", FLEETS)
def test_every_page_passes_the_accessibility_scan(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    organisation: str,
) -> None:
    """REQ-383 to REQ-404. axe-core, WCAG 2.2 Levels A and AA, on every page the
    Continuing Airworthiness Manager and the Administrator can open, at 320 pixels
    (SC 1.4.10), in light and dark and with high contrast asked for by the device.
    The pull request scans the Dashboard and the Fleet; the full walk scans every page."""
    found: dict[str, list[str]] = {}
    for role in (Role.CONTINUING_AIRWORTHINESS_MANAGER, Role.ADMINISTRATOR):
        account = next(person for person in personas[organisation] if person.role == role)
        with signed_in(chromium, live_site, account, width=320) as page:
            pending = deque(["/dashboard/", "/"])
            seen: set[str] = set()
            while pending:
                path = pending.popleft()
                if path in seen:
                    continue
                seen.add(path)
                response = page.goto(path, wait_until="load")
                if (
                    response is None
                    or not response.ok
                    or "text/html" not in (response.headers.get("content-type", ""))
                ):
                    continue
                for scheme, contrast in (
                    ("light", "no-preference"),
                    ("dark", "no-preference"),
                    ("light", "more"),
                ):
                    page.emulate_media(color_scheme=scheme, contrast=contrast)  # type: ignore[arg-type,unused-ignore]
                    problems = violations(page)
                    if page.evaluate(SIDEWAYS):
                        problems.append("the page scrolls sideways at 320 pixels")
                    if problems:
                        found[f"{path} {scheme} {contrast}"] = problems
                if not os.environ.get("AIRWORTHINESS_E2E_FULL"):
                    continue
                for href in page.locator("a[href]").evaluate_all(
                    "(links) => links.map(link => link.getAttribute('href'))"
                ):
                    target = urlsplit(urljoin(page.url, href))
                    if target.netloc != urlsplit(live_site).netloc or target.fragment:
                        continue
                    if "sign-out" in target.path or "export" in target.path:
                        continue
                    pending.append(target.path + (f"?{target.query}" if target.query else ""))
            page.emulate_media(color_scheme="light", contrast="no-preference")  # type: ignore[arg-type,unused-ignore]
            page.goto("/dashboard/")
            sign_out(page)
    assert found == {}
