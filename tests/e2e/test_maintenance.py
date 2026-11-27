"""Browser workflows for aircraft status, repeat defects and maintenance records."""

from playwright.sync_api import Browser, expect

from tests.e2e.browser import (
    choose_aircraft,
    definition,
    fill,
    form_with,
    open_row_action,
    reveal,
    save,
    signed_in,
    submit,
)
from tests.e2e.conftest import Account


def test_aircraft_owner_counter_and_serviceability(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-ABCD")
        save(
            page,
            "Save the Owner of G-ABCD",
            {"customer": "[Owner Name G-EJKL]"},
            "[Owner Name G-EJKL]",
        )
        assert definition(page, "Customer") == "[Owner Name G-EJKL]"
        page.get_by_role("link", name="Add an Engine or Propeller", exact=True).click()
        save(
            page,
            "Add",
            {
                "kind": "Engine",
                "position": "Test position",
                "serial_number": "TEST-ENGINE",
            },
            "TEST-ENGINE",
        )
        page.get_by_role("link", name="Record as Unserviceable", exact=True).click()
        save(
            page,
            "Record as Unserviceable",
            {
                "reason": "Test inspection pending",
                "since": "2026-11-18",
            },
            "Test inspection pending",
        )
        assert "Unserviceable" in definition(page, "Status")
        save(page, "Record as Serviceable", {}, "Serviceable")
        assert definition(page, "Status") == "Serviceable"


def test_programme_review_and_release_reference(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-ABCD", "Maintenance Programme")
        save(page, "Record Programme Review", {"reviewed_on": "2026-11-18"}, "18 November 2026")
        assert definition(page, "Last Reviewed") == "18 November 2026"
        page.get_by_role("link", name="Record Work Done", exact=True).click()
        work = "Test inspection recorded without release reference"
        save(
            page,
            "Record Work",
            {
                "description": work,
                "dated": "2026-11-17",
                "hours": "6411.0",
                "cycles": "0",
            },
            work,
        )
        row = page.locator("main tr:not(.detail)").filter(has_text=work)
        control = reveal(row).get_by_role("button", name="Record Release", exact=True)
        fill(control.locator("xpath=ancestor::form[1]"), {"release_reference": "TEST-WORK-RELEASE"})
        submit(page, control)
        page.reload()
        expect(row).to_contain_text("TEST-WORK-RELEASE")


def test_repeat_defect_action_survives_reload(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/defects/")
        page.get_by_role("link", name="Repeat Defects", exact=True).click()
        save(
            page,
            "Record Action",
            {
                "type_rating": "Piper PA-28 Series (Lycoming)",
                "chapter": "33",
                "action": "Inspect lamp connector",
            },
            "Inspect lamp connector",
        )


def test_component_review_and_overhaul_date(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/components/")
        row = page.locator("main tr:not(.detail)").filter(has_text="G-DGHI")
        row.get_by_role("link", name="Engine, Lycoming").click()
        save(
            page,
            "Record Review",
            {
                "airframe_hours": "9874.3",
                "reviewed_on": "2026-11-18",
            },
            "9,974.3",
        )
        page.goto("/components/")
        page.get_by_role("link", name="Add a Component", exact=True).click()
        save(
            page,
            "Add Component",
            {
                "name": "Test dated pump",
                "basis": "Service Life Limit",
                "limit_months": "12",
                "source": "[Test manual]",
            },
            "Test dated pump",
        )
        save(
            page,
            "Record Installation",
            {
                "aircraft": "G-ABCD",
                "position": "Test date position",
                "fitted_on": "2026-11-18",
                "airframe_hours_fitted": "6412.6",
                "hours_at_fitting": "0.0",
            },
            "Test date position",
        )
        save(page, "Record Day", {"life_from": "2026-11-10"}, "10 November 2026")


def test_embodied_change_and_weight_records(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/modifications/")
        page.get_by_role("link", name="Record a Change", exact=True).click()
        save(
            page,
            "Record Change or Repair",
            {
                "aircraft": "G-BXYZ",
                "title": "Test panel change",
                "route": "Standard Change",
                "reference": "TEST-21",
                "mass_effect": "0.4",
            },
            "Test panel change",
        )
        open_row_action(page, "Test panel change", "Record as Embodied")
        save(page, "Record as Embodied", {"embodied_on": "2026-11-18"}, "18 November 2026")
        page.goto("/weight-and-balance/")
        page.get_by_role("link", name="Record a Weight Schedule Issue", exact=True).click()
        save(
            page,
            "Record Weight Schedule Issue",
            {
                "aircraft": "G-BXYZ",
                "issue": "7",
                "issued_on": "2026-11-18",
            },
            "Issue 7",
        )
        page.get_by_role("link", name="Record a Weighing", exact=True).click()
        save(
            page,
            "Record Weighing",
            {
                "aircraft": "G-BXYZ",
                "weighed_on": "2026-11-18",
                "reference": "TEST-MASS",
            },
            "18 November 2026",
        )


def test_configuration_baseline_retains_signed_position(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-ABCD", "Configuration")
        page.get_by_role("link", name="Set Up Configuration", exact=True).click()
        setup = page.url
        form = form_with(page, "product")
        form.locator('[name="tracked"]').check()
        fill(form, {"product": "Airframe", "chapter": "33", "name": "Test cabin light"})
        submit(page, form.get_by_role("button"))
        row = page.locator("main tr:not(.detail)").filter(has_text="Test cabin light")
        record = reveal(row).locator("form")
        fill(
            record, {"part_number": "TEST-11", "serial_number": "TEST-12", "source": "Test logbook"}
        )
        submit(page, record.get_by_role("button"))
        submit(page, page.get_by_role("button", name="Sign Configuration Baseline", exact=True))
        expect(page.locator("main h1")).to_have_text("Configuration Baseline, G-ABCD")
        expect(page.locator("main")).to_contain_text("TEST-12")
        baseline = page.url
        page.goto(setup)
        record = reveal(row).locator("form")
        fill(record, {"serial_number": "TEST-13"})
        submit(page, record.get_by_role("button"))
        expect(row).to_contain_text("TEST-13")
        page.goto(baseline)
        expect(page.locator("main")).to_contain_text("TEST-12")
        expect(page.locator("main")).not_to_contain_text("TEST-13")
