"""Browser actions shared by the live journeys."""

import base64
import hmac
import time
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, field

from playwright.sync_api import Browser, Locator, Page, Route, expect

from tests.e2e.conftest import Account


def totp(key: str) -> tuple[str, int]:
    if time.time() % 30 > 25:
        time.sleep(30 - time.time() % 30 + 0.2)
    counter = int(time.time()) // 30
    digest = hmac.digest(base64.b32decode("".join(key.split())), counter.to_bytes(8), "sha1")
    offset = digest[-1] & 15
    number = int.from_bytes(digest[offset : offset + 4]) & 0x7FFF_FFFF
    return f"{number % 1_000_000:06d}", counter


def submit(page: Page, button: Locator) -> None:
    with page.expect_navigation(wait_until="load"):
        button.click()


@dataclass(frozen=True)
class Authenticator:
    key: str = field(repr=False)
    step: int


def enter_password(page: Page, username: str, password: str) -> None:
    page.goto("/sign-in/")
    page.locator("#username").fill(username)
    page.locator("#password").fill(password)
    submit(page, page.get_by_role("button", name="Continue", exact=True))


def sign_in(page: Page, account: Account) -> Authenticator:
    enter_password(page, account.username, account.password)
    # Avoid putting values from the authenticator page in assertion output or traces.
    key = page.locator("main dd code").first.inner_text()
    code, step = totp(key)
    page.locator("#code").fill(code)
    submit(page, page.get_by_role("button", name="Confirm and Sign In", exact=True))
    page.locator('[name="current"]').fill(account.password)
    page.locator('[name="new"]').fill(account.new_password)
    page.locator('[name="again"]').fill(account.new_password)
    submit(page, page.locator("main form").first.get_by_role("button", name="Change Password"))
    expect(page.locator("aside .roles")).to_have_text(str(account.role))
    return Authenticator(key, step)


def sign_in_again(page: Page, account: Account, authenticator: Authenticator) -> None:
    enter_password(page, account.username, account.new_password)
    expect(page.get_by_role("heading", name="Authenticator Code")).to_be_visible()
    time.sleep(max(0.0, (authenticator.step + 1) * 30 - time.time() + 0.1))
    code, _ = totp(authenticator.key)
    page.locator("#code").fill(code)
    submit(page, page.get_by_role("button", name="Sign In", exact=True))
    expect(page.locator("aside .roles")).to_have_text(str(account.role))


@contextmanager
def signed_in(
    browser: Browser, site: str, account: Account, width: int = 1280, *, returning: bool = False
) -> Iterator[Page]:
    with browser.new_context(base_url=site, viewport={"width": width, "height": 850}) as context:

        def loopback_only(route: Route) -> None:
            if route.request.url.startswith(site + "/"):
                route.continue_()
            else:
                route.abort()

        context.route("**/*", loopback_only)
        page = context.new_page()
        page.set_default_timeout(5_000)
        authenticator = sign_in(page, account)
        if returning:
            submit(page, page.get_by_role("button", name="Sign Out", exact=True))
            sign_in_again(page, account, authenticator)
        yield page


def form_with(page: Page, field: str) -> Locator:
    return page.locator("main form").filter(has=page.locator(f'[name="{field}"]')).first


def fill(form: Locator, fields: Mapping[str, str]) -> None:
    for name, value in fields.items():
        field = form.locator(f'[name="{name}"]').first
        if field.evaluate("element => element.tagName") == "SELECT":
            field.select_option(label=value)
        else:
            field.fill(value)


def choose_aircraft(page: Page, registration: str, tab: str = "Record") -> None:
    page.goto("/")
    page.get_by_role("link", name=registration, exact=True).first.click()
    if tab != "Record":
        page.locator("nav.tabs").get_by_role("link", name=tab, exact=True).click()


def change_aircraft_details(page: Page, registration: str, serial: str) -> None:
    choose_aircraft(page, registration)
    form = form_with(page, "manufacturer")
    fill(
        form,
        {
            "manufacturer": "Test Aircraft Works",
            "designation": "Test Type",
            "serial_number": serial,
        },
    )
    submit(page, form.get_by_role("button", name=f"Save Details of {registration}"))
    expect(page.locator("main")).to_contain_text(serial)


def reveal(row: Locator) -> Locator:
    row.get_by_role("button", name="Show Details", exact=True).click()
    return row.locator("xpath=following-sibling::tr[1]")


def definition(page: Page, label: str) -> str:
    return (
        page.locator("main dt")
        .get_by_text(label, exact=True)
        .locator("xpath=following-sibling::dd[1]")
        .inner_text()
    )
