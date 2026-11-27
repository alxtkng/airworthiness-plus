"""Browser workflows for user administration and session management."""

from playwright.sync_api import Browser, Locator, Page, expect

from airworthiness_plus.accounts.roles import Role
from tests.e2e.browser import (
    browser_page,
    fill,
    form_with,
    reveal,
    sign_in,
    sign_in_again,
    signed_in,
    submit,
    wait_for_next_code,
)
from tests.e2e.conftest import Account, RunningSite


def first_password(page: Page) -> str:
    # Read the generated value without putting it in assertion output.
    return page.locator('main [role="status"] code').inner_text()


def user_row(page: Page, name: str) -> Locator:
    return page.locator("main tbody tr:not(.detail)").filter(
        has=page.get_by_role("cell", name=name, exact=True)
    )


def test_administrator_manages_user_sign_in(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    name = "Test Records User"
    username = "records-test@example.test"
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as admin:
        admin.goto("/users/")
        form = form_with(admin, "username")
        fill(form, {"full_name": name, "username": username})
        form.get_by_role("checkbox", name="Read Only", exact=True).check()
        submit(admin, form.get_by_role("button", name="Add User", exact=True))
        account = Account(username, Role.READ_ONLY, password=first_password(admin))
        row = user_row(admin, name)
        expect(row).to_contain_text(username)
        with browser_page(chromium, live_site) as user:
            authenticator = sign_in(user, account)
            admin.reload()
            roles = reveal(row).get_by_role("button", name=f"Save Roles of {name}")
            form = roles.locator("xpath=ancestor::form[1]")
            form.get_by_role("checkbox", name="Read Only", exact=True).uncheck()
            form.get_by_role("checkbox", name="Planning and Records", exact=True).check()
            submit(admin, roles)
            user.goto("/dashboard/")
            expect(user.locator("aside .roles")).to_have_text("Planning and Records")

            submit(admin, reveal(row).get_by_role("button", name=f"End Sessions of {name}"))
            user.goto("/dashboard/")
            expect(user.get_by_role("heading", name="Sign In", exact=True)).to_be_visible()

        submit(
            admin,
            reveal(row).get_by_role("button", name=f"Give {name} a New First Password"),
        )
        account = Account(username, Role.PLANNING_AND_RECORDS, password=first_password(admin))
        expect(row).to_contain_text("Password to Be Changed")
        admin.goto("/users/")
        submit(admin, reveal(row).get_by_role("button", name=f"Reset Second Factor of {name}"))
        expect(row).to_contain_text("Not Set Up")
        wait_for_next_code(authenticator.step)
        with signed_in(chromium, live_site, account) as user:
            submit(admin, reveal(row).get_by_role("button", name=f"Make {name} Inactive"))
            expect(row.get_by_role("cell", name="Inactive", exact=True)).to_be_visible()
            user.goto("/dashboard/")
            expect(user.get_by_role("heading", name="Sign In", exact=True)).to_be_visible()
        submit(admin, reveal(row).get_by_role("button", name=f"Make {name} Active"))
        expect(row.get_by_role("cell", name="Active", exact=True)).to_be_visible()


def test_user_can_close_one_session_and_sign_out_everywhere_else(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    account = personas["second-organisation"][4]
    with (
        browser_page(chromium, live_site) as first,
        browser_page(chromium, live_site) as second,
        browser_page(chromium, live_site) as third,
    ):
        authenticator = sign_in(first, account)
        authenticator = sign_in_again(second, account, authenticator)
        second.goto("/account/password/")
        submit(second, second.get_by_role("button", name="End This Session", exact=True))
        first.goto("/dashboard/")
        expect(first.get_by_role("heading", name="Sign In", exact=True)).to_be_visible()
        expect(second.get_by_text("This Session", exact=True)).to_be_visible()

        sign_in_again(third, account, authenticator)
        third.goto("/account/password/")
        submit(third, third.get_by_role("button", name="Sign Out Everywhere Else", exact=True))
        second.goto("/dashboard/")
        expect(second.get_by_role("heading", name="Sign In", exact=True)).to_be_visible()
        expect(third.get_by_text("This Session", exact=True)).to_be_visible()


def test_passkey_enrolment_sign_in_and_revocation(
    chromium: Browser, running_site: RunningSite, personas: dict[str, tuple[Account, ...]]
) -> None:
    account = personas["your-organisation"][4]
    site = running_site.address.replace("127.0.0.1", "localhost")
    with browser_page(chromium, site) as page:
        authenticator = sign_in(page, account)
        cdp = page.context.new_cdp_session(page)
        cdp.send("WebAuthn.enable")
        cdp.send(
            "WebAuthn.addVirtualAuthenticator",
            {
                "options": {
                    "protocol": "ctap2",
                    "transport": "usb",
                    "hasResidentKey": True,
                    "hasUserVerification": True,
                    "isUserVerified": True,
                    "automaticPresenceSimulation": True,
                }
            },
        )
        page.get_by_role("link", name="Passkeys", exact=True).click()
        page.get_by_label("Passkey Name").fill("Workshop Security Key")
        page.get_by_role("button", name="Add Passkey", exact=True).click()
        remove = page.get_by_role("button", name="Remove Workshop Security Key")
        expect(remove).to_be_visible()

        submit(page, page.get_by_role("button", name="Sign Out"))
        page.get_by_label("User Name").fill(account.username)
        submit(page, page.get_by_role("button", name="Sign In with a Passkey"))
        expect(page.locator("aside .roles")).to_have_text(str(account.role))
        page.reload()
        expect(page.locator("aside .roles")).to_have_text(str(account.role))
        tab = page.context.new_page()
        tab.goto("/sign-in/")
        expect(tab).to_have_url(site + "/dashboard/")
        tab.close()

        cookie = next(cookie for cookie in page.context.cookies() if cookie["name"] == "sessionid")
        running_site.advance_verification_age(cookie["value"])
        page.get_by_role("link", name="Passkeys", exact=True).click()
        submit(page, page.get_by_role("button", name="Verify Your Identity to Add a Passkey"))
        submit(page, page.get_by_role("button", name="Verify with a Passkey"))
        expect(page.get_by_role("button", name="Add Passkey", exact=True)).to_be_visible()
        submit(page, remove)
        expect(remove).to_have_count(0)
        submit(page, page.get_by_role("button", name="Sign Out"))
        page.get_by_label("User Name").fill(account.username)
        page.get_by_role("button", name="Sign In with a Passkey").click()
        expect(page.get_by_role("alert")).to_have_text("Passkey Not Accepted")
        sign_in_again(page, account, authenticator)
