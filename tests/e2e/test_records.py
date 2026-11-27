"""Sample record workflows through rendered browser forms."""

import pytest
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


def test_record_and_close_a_defect(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/defects/")
        page.get_by_role("link", name="Record a Defect", exact=True).click()
        save(
            page,
            "Record Defect",
            {
                "aircraft": "G-FMNO",
                "title": "Test cabin light",
                "found_on": "2026-11-17",
                "chapter": "33",
                "system": "Lights",
                "decision": "Deferred",
                "basis": "Pilot-in-Command",
                "decided_on": "2026-11-18",
            },
            "Test cabin light",
        )
        detail = page.url
        form = form_with(page, "rectification")
        fill(form, {"rectification": "Bulb replaced", "closed_on": "2026-11-16"})
        submit(page, form.get_by_role("button"))
        expect(page.get_by_role("alert")).to_contain_text("Before")
        page.goto(detail)
        expect(page.locator("main")).not_to_contain_text("Bulb replaced")
        form = form_with(page, "rectification")
        fill(form, {"rectification": "Bulb replaced", "closed_on": "2026-11-18"})
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main")).to_contain_text("Bulb replaced")


def test_component_fit_limit_and_removal(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/components/")
        page.get_by_role("link", name="Add a Component", exact=True).click()
        save(
            page,
            "Add Component",
            {
                "name": "Test Pump",
                "part_number": "TEST-P-1",
                "serial_number": "TEST-18",
                "basis": "Service Life Limit",
                "limit_hours": "500.0",
                "source": "[Test manual]",
            },
            "Test Pump",
        )
        save(
            page,
            "Record Installation",
            {
                "aircraft": "G-ABCD",
                "position": "Test position",
                "fitted_on": "2026-11-18",
                "airframe_hours_fitted": "6412.6",
                "hours_at_fitting": "5.0",
                "release_document": "TEST-FIT-18",
            },
            "495.0",
        )
        save(page, "Change Limit", {"limit_hours": "600.0"}, "595.0")
        save(
            page,
            "Record Removal",
            {
                "removed_on": "2026-11-18",
                "airframe_hours_removed": "6412.6",
                "airframe_cycles_removed": "0",
                "removal_reason": "Test inspection",
                "sent_to": "Test workshop",
                "due_back_on": "2026-11-28",
            },
            "28 November 2026",
        )


def test_contract_keeps_the_signed_owner(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/contracts/")
        page.get_by_role("link", name="G-CDEF", exact=True).first.click()
        contract = page.url
        owner = definition(page, "Owner")
        assert owner == "[Syndicate Name G-CDEF]"
        page.goto("/customers/")
        page.get_by_role("link", name=owner, exact=True).click()
        save(page, f"Save the Record of {owner}", {"name": "Test Syndicate"}, "Test Syndicate")
        page.goto(contract)
        assert definition(page, "Owner") == owner


@pytest.mark.parametrize("organisation", ["your-organisation", "second-organisation"])
def test_problem_and_permanent_note(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    organisation: str,
) -> None:
    with signed_in(chromium, live_site, personas[organisation][1]) as page:
        page.goto("/problem-log/")
        save(page, "Add Entry", {"problem": "Test discrepancy in the logbook"}, "Test discrepancy")
        row = page.locator("main tr:not(.detail)").filter(has_text="Test discrepancy")
        form = reveal(row).locator("form")
        fill(form, {"kind": "Solution", "text": "Checked against the original logbook"})
        submit(page, form.get_by_role("button", name="Add to This Entry"))
        page.reload()
        expect(row).to_contain_text("Solved")
        expect(reveal(row)).to_contain_text("Checked against the original logbook")


@pytest.mark.parametrize("organisation", ["your-organisation", "second-organisation"])
def test_aircraft_programme_and_directive(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
    organisation: str,
) -> None:
    with signed_in(chromium, live_site, personas[organisation][1]) as page:
        page.goto("/")
        page.get_by_role("link", name="Add an Aircraft", exact=True).click()
        aircraft = {
            "registration": "G-TTST",
            "type_rating": "Piper PA-28 Series (Lycoming)",
            "serial_number": "TEST-301",
            "manufacturer": "[Test Maker]",
            "designation": "Variant A",
            "regime": "Part 21",
            "dated": "2026-11-16",
            "hours": "120.5",
            "cycles": "93",
        }
        form = form_with(page, "registration")
        fill(form, aircraft)
        submit(page, form.get_by_role("button"))
        expect(page.get_by_role("alert")).to_contain_text("Choose a Customer or Name a New One")
        fill(form, {**aircraft, "owner": "[Test Owner]"})
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main h1")).to_have_text("G-TTST")
        record = page.url
        page.get_by_role("link", name="Enter Hours and Cycles", exact=True).click()
        form = form_with(page, "counter")
        form.locator('[name="counter"]').select_option(index=1)
        fill(form, {"dated": "2026-11-17", "hours": "124.0", "cycles": "95"})
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main")).to_contain_text("124.0")

        page.get_by_role("link", name="Maintenance Programme", exact=True).click()
        programme = page.url
        page.get_by_role("link", name="Record the Programme", exact=True).click()
        form = form_with(page, "basis")
        fill(
            form,
            {
                "basis": "Design Approval Holder's Instructions",
                "reference": "[Test plan]",
                "hours_per_day": "1.0",
            },
        )
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main")).to_contain_text("[Test plan]")
        page.get_by_role("link", name="Add a Task", exact=True).click()
        form = form_with(page, "title")
        form.locator('[name="counter"]').select_option(index=1)
        fill(
            form,
            {
                "title": "Cabin light inspection",
                "kind": "Programme Task",
                "source": "[Test manual]",
                "interval_hours": "20.0",
                "starts_dated": "2026-11-16",
                "starts_hours": "120.0",
                "starts_cycles": "93",
            },
        )
        submit(page, form.get_by_role("button"))
        page.goto(programme)
        expect(page.locator("main")).to_contain_text("Cabin light inspection")

        page.goto("/directives/")
        page.get_by_role("link", name="Record an Airworthiness Directive", exact=True).click()
        form = form_with(page, "number")
        fill(
            form,
            {
                "number": "TEST-2026-01",
                "authority": "[Test Authority]",
                "subject": "Cabin light cable",
                "effective_date": "2026-11-01",
                "revision": "1",
            },
        )
        submit(page, form.get_by_role("button"))
        page.reload()
        expect(page.locator("main")).to_contain_text("TEST-2026-01")
        page.goto(record)
        page.get_by_role("link", name="Airworthiness Directives", exact=True).click()
        open_row_action(page, "TEST-2026-01", "Decide Applicability")
        form = form_with(page, "decision")
        form.locator('[name="counter"]').select_option(index=1)
        fill(
            form,
            {
                "decision": "Applicable",
                "basis": "Applies to this model",
                "starts_dated": "2026-11-16",
                "starts_hours": "120.0",
                "starts_cycles": "93",
                "first_hours": "10.0",
                "repeat_hours": "10.0",
            },
        )
        submit(page, form.get_by_role("button"))
        page.reload()
        row = page.locator("main tbody tr:not(.detail)").filter(has_text="TEST-2026-01")
        expect(row).to_contain_text("Applicable")
        open_row_action(page, "TEST-2026-01", "Record Compliance")
        form = form_with(page, "method")
        fill(
            form,
            {
                "method": "Visual cable inspection",
                "dated": "2026-11-17",
                "hours": "124.0",
                "cycles": "95",
            },
        )
        submit(page, form.get_by_role("button"))
        expect(row).to_contain_text("Visual cable inspection")
        open_row_action(page, "TEST-2026-01", "Record Terminating Action")
        form = form_with(page, "action")
        fill(form, {"action": "Replacement cable fitted", "on": "2026-11-18"})
        submit(page, form.get_by_role("button"))
        expect(row).to_contain_text("Replacement cable fitted")


def test_service_bulletin_owner_decision(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/modifications/")
        page.get_by_role("link", name="Record a Service Bulletin", exact=True).click()
        save(
            page,
            "Record Service Bulletin",
            {
                "aircraft": "G-BXYZ",
                "title": "Test inspection notice",
                "reference": "TEST-SB-18",
                "classification": "Recommended",
                "sent_on": "2026-11-17",
                "reminder_on": "2026-11-25",
                "decision": "Awaiting Owner",
            },
            "Test inspection notice",
        )
        open_row_action(page, "Test inspection notice", "Record the Owner Decision")
        save(
            page,
            "Record Owner Decision",
            {
                "decision": "Accepted",
                "detail": "At next scheduled check",
                "decided_on": "2026-11-18",
            },
            "At next scheduled check",
        )


def test_maintenance_data_revision_and_amendment_check(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/maintenance-data/")
        page.locator('a[href="/maintenance-data/add/"]').first.click()
        form = form_with(page, "title")
        form.locator('[name="held"]').check()
        save(
            page,
            "Record Maintenance Data",
            {
                "title": "Test maintenance sheet",
                "author": "[Test Author]",
                "kind": "Airworthiness Directive",
                "applies_to": "Piper PA-28 Series (Lycoming)",
                "revision": "TEST-1",
                "revision_date": "2026-11-15",
                "provided_by": "Test data owner",
                "evidence": "Written Confirmation",
                "evidence_dated": "2026-11-15",
            },
            "TEST-1",
        )
        data_set = page.url
        bad_revision = page.get_by_role("button", name="Record New Revision", exact=True)
        fill(
            bad_revision.locator("xpath=ancestor::form[1]"),
            {"revision": "TEST-2", "revision_date": "2026-11-14"},
        )
        submit(page, bad_revision)
        expect(page.get_by_role("alert")).to_contain_text("Before")
        page.goto(data_set)
        expect(page.locator("main")).not_to_contain_text("TEST-2")
        save(
            page,
            "Record New Revision",
            {
                "revision": "TEST-2",
                "revision_date": "2026-11-17",
            },
            "TEST-2",
        )
        expect(page.locator("main")).to_contain_text("TEST-1")
        save(
            page,
            "Record Amendment Check",
            {
                "checked_on": "2026-11-18",
                "result": "Test revision checked",
                "next_due": "2027-01-18",
            },
            "18 January 2027",
        )
        save(
            page,
            "Record Amendment Status",
            {
                "evidence": "Work Order",
                "dated": "2026-11-18",
            },
            "Work Order",
        )
        save(page, "Record as No Longer Held", {"on": "2026-11-18"}, "No Longer Held")


def test_contract_work_order_and_closure(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/contracts/")
        page.get_by_role("link", name="Draw Up a Contract", exact=True).click()
        save(
            page,
            "Record Contract",
            {
                "aircraft": "G-FMNO",
                "scope": "Limited Tasks",
                "tasks": "Test programme review",
                "type_of_operation": "Private",
                "owner_address": "10 Test Road",
                "signed_on": "2026-11-12",
            },
            "Test programme review",
        )
        contract = page.url
        page.goto("/contracts/")
        page.get_by_role("link", name="Record a Work Order", exact=True).click()
        save(
            page,
            "Record Work Order",
            {
                "aircraft": "G-FMNO",
                "work": "Test panel inspection",
                "ordered_by": "Owner",
                "agreed_on": "2026-11-13",
            },
            "Test panel inspection",
        )
        open_row_action(page, "Test panel inspection", "Close the Work Order")
        save(
            page,
            "Close Work Order",
            {
                "outcome": "Withdrawn",
                "closed_on": "2026-11-14",
            },
            "Withdrawn",
        )
        page.goto(contract)
        save(
            page,
            "End the Contract",
            {
                "ended_on": "2026-11-15",
                "end_reason": "Non-Conformity With the Contract",
            },
            "29 November 2026",
        )
        save(page, "Record the Day", {"told_on": "2026-11-16"}, "16 November 2026")


def test_departure_records_owner_copy_and_withdrawal(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-ABCD", "Maintenance Programme")
        page.get_by_role("link", name="Record a Departure", exact=True).click()
        form = form_with(page, "task")
        fill(
            form,
            {
                "task": "Test inspection interval",
                "manufacturer": "500 hours",
                "programme_says": "On condition",
                "compensating_measures": "Check at every service",
                "justification": "Test inspection evidence",
                "recorded_on": "2026-11-16",
            },
        )
        submit(page, form.get_by_role("button"))
        page.reload()
        row = page.locator("main tr:not(.detail)").filter(has_text="Test inspection interval")
        expect(row).to_be_visible()
        copy = reveal(row).get_by_role("button", name="Record Owner Copy Sent", exact=True)
        fill(copy.locator("xpath=ancestor::form[1]"), {"on": "2026-11-17"})
        submit(page, copy)
        page.reload()
        expect(row).to_contain_text("Sent 17 November 2026")
        withdraw = reveal(row).get_by_role("button", name="Withdraw Departure", exact=True)
        fill(withdraw.locator("xpath=ancestor::form[1]"), {"on": "2026-11-18"})
        submit(page, withdraw)
        page.reload()
        details = reveal(row)
        expect(
            details.get_by_text("Withdrawn", exact=True).locator("xpath=following-sibling::dd[1]")
        ).to_have_text("18 November 2026")
        expect(details).to_contain_text("Test inspection evidence")


def test_annual_programme_review_keeps_checklist_and_calculates_next_due(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        choose_aircraft(page, "G-ABCD", "Maintenance Programme")
        save(page, "Start the Annual Review", {}, "0 of 6 Complete")
        checklist = page.get_by_role("button", name="Save the Review", exact=True)
        form = checklist.locator("xpath=ancestor::form[1]")
        notes = form.locator('[name$="_note"]')
        points = form.get_by_role("checkbox")
        expect(notes).to_have_count(6)
        expect(points).to_have_count(6)
        for index in range(6):
            notes.nth(index).fill(f"[Test annual review evidence {index + 1}]")
            points.nth(index).check()
        submit(page, checklist)
        expect(page.locator("main")).to_contain_text("6 of 6 Complete")
        save(
            page,
            "Complete the Review",
            {
                "completed_on": "2026-11-18",
            },
            "Annual Review Completed 18 November 2026",
        )
        assert definition(page, "Last Reviewed") == "18 November 2026"
        assert definition(page, "Next Review By") == "18 November 2027"


def test_directive_source_check_records_next_check(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/directives/")
        page.get_by_role("link", name="Record a Source", exact=True).click()
        save(
            page,
            "Record Source",
            {
                "name": "Test State of Design Authority",
                "covers": "Airframes",
            },
            "Test State of Design Authority",
        )
        open_row_action(page, "Test State of Design Authority", "Record a Check")
        save(
            page,
            "Record Check",
            {
                "checked_on": "2026-11-18",
                "next_check_on": "2026-12-02",
            },
            "2 December 2026",
        )
        row = page.locator("main tr:not(.detail)").filter(has_text="Test State of Design Authority")
        expect(row).to_contain_text("18 November 2026")
        expect(row).to_contain_text("2 December 2026")


def test_administrator_records_maintenance_authorisation(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/staff/")
        page.get_by_role("link", name="Chris Moore", exact=True).click()
        page.get_by_role("link", name="Record Maintenance Authorisation").click()
        save(
            page,
            "Save Authorisation",
            {
                "reference": "TEST-CA-42",
                "scope": "Piper PA-28 Airframe",
                "valid_from": "2026-11-15",
                "valid_to": "2026-12-01",
            },
            "TEST-CA-42",
        )
        page.reload()
        row = page.get_by_role("row").filter(has_text="TEST-CA-42")
        expect(row).to_contain_text("Chris Moore")
        expect(row).to_contain_text("1 December 2026")
        row.get_by_role("link", name="TEST-CA-42").click()
        save(
            page,
            "Save Evidence",
            {
                "kind": "Approved Maintenance Employment",
                "evidence_reference": "TEST-EMP-1",
                "qualification_basis": "Approved maintenance employment within this scope",
                "starts_on": "2025-01-01",
                "ends_on": "2025-06-30",
            },
            "TEST-EMP-1",
        )
        page.get_by_role("link", name="Recency", exact=True).click()
        assessed = page.get_by_role("row").filter(has_text="TEST-CA-42")
        expect(assessed).to_contain_text("6 Complete Months")
        expect(assessed).to_contain_text("Duration Met")
        assessed.get_by_role("link", name="TEST-CA-42").click()
        evidence = page.locator("main tbody tr:not(.detail)").filter(has_text="TEST-EMP-1")
        button = reveal(evidence).get_by_role("button", name="Withdraw Evidence")
        fill(button.locator("xpath=ancestor::form[1]"), {"reason": "Wrong employment dates"})
        submit(page, button)
        expect(reveal(evidence)).to_contain_text("Wrong employment dates")
        page.get_by_role("link", name="Recency", exact=True).click()
        expect(assessed).to_contain_text("Further Evidence Needed")
        assessed.get_by_role("link", name="TEST-CA-42").click()
        save(
            page,
            "Withdraw Authorisation",
            {"withdrawn_from": "2026-11-18", "reason": "Authorisation superseded"},
            "Authorisation superseded",
        )
        expect(page.locator("main")).to_contain_text("Withdrawn From")


def test_administrator_records_recurrent_training(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/staff/")
        page.get_by_role("link", name="Chris Moore", exact=True).click()
        page.get_by_role("link", name="Record Recurrent Training").click()
        save(
            page,
            "Save Training",
            {
                "subject": "Human Factors",
                "evidence_reference": "TEST-TR-65",
                "completed_on": "2025-11-15",
                "due_on": "2027-11-15",
            },
            "TEST-TR-65",
        )
        page.reload()
        row = page.get_by_role("row").filter(has_text="TEST-TR-65")
        expect(row).to_contain_text("Human Factors")
        expect(row).to_contain_text("15 November 2027")
        page.goto("/staff/")
        expect(page.get_by_role("row").filter(has_text="Chris Moore")).to_contain_text(
            "Human Factors, Completed 15 November 2025, Due 15 November 2027"
        )


def test_administrator_records_staff_approvals_and_limits(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/staff/")
        page.get_by_role("link", name="Add a Person", exact=True).click()
        save(
            page,
            "Add Person",
            {
                "full_name": "[Test Records Assistant]",
                "role": "Planning",
                "licence": "TEST-112",
                "joined_on": "2026-11-16",
            },
            "TEST-112",
        )
        assert definition(page, "Name") == "[Test Records Assistant]"

        page.goto("/settings/")
        save(
            page,
            "Save Organisation Details",
            {
                "name": "[Test Continuing Airworthiness]",
                "address": "18 Test Road",
            },
            "18 Test Road",
        )
        save(
            page,
            "Save Deferral Limits",
            {
                "deferral_days_non_required": "11",
                "deferral_days_with_agreement": "10",
                "deferral_days_certifying_staff": "9",
            },
            "11 Days",
        )
        save(page, "Save Reweigh Threshold", {"threshold": "2.5"}, "Reweigh Threshold")
        expect(form_with(page, "threshold").locator('[name="threshold"]')).to_have_value("2.5")
        save(
            page,
            "Record an Approval Held",
            {
                "approval": "Part-145",
                "reference": "UK.145.[Test]",
            },
            "UK.145.[Test]",
        )
        row = page.locator("main tr:not(.detail)").filter(has_text="UK.145.[Test]")
        end = reveal(row).get_by_role("button", name="Record Part-145 as No Longer Held")
        fill(end.locator("xpath=ancestor::form[1]"), {"on": "2026-11-18"})
        submit(page, end)
        page.reload()
        expect(row).to_contain_text("No Longer Held From 18 November 2026")

        page.goto("/organisation/")
        save(
            page,
            "Record Approval",
            {
                "reference": "TEST-RECORDS-431",
                "dated": "2026-11-17",
            },
            "TEST-RECORDS-431",
        )
        save(page, "Record Parallel Run", {"started_on": "2026-05-18"}, "18 May 2026")


def test_open_transfer_checklist_keeps_aircraft_out_of_fleet(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/")
        registration = page.get_by_role("link", name="G-HKLM", exact=True)
        expect(registration).to_have_count(0)
        page.get_by_role("link", name="Transfers", exact=True).click()
        row = page.locator("main tbody tr:not(.detail)").filter(has=registration)
        expect(row).to_contain_text("Records 14 of 18 Received")
        form = reveal(row).locator("form")
        fill(form, {"received": "16"})
        submit(page, form.get_by_role("button", name="Save", exact=True))
        expect(row).to_contain_text("Records 16 of 18 Received")
        form = reveal(row).locator("form")
        fill(form, {"received": "18"})
        submit(page, form.get_by_role("button", name="Save and Move to Fleet"))
        page.goto("/")
        expect(registration).to_have_count(0)
        page.get_by_role("link", name="Transfers", exact=True).click()
        expect(row).to_contain_text("Records 18 of 18 Received")
        checklist_row = page.locator("main tr:not(.detail)").filter(
            has_text="Exposition Scope of Work"
        )
        item = reveal(checklist_row).locator("form")
        fill(item, {"state": "Complete", "note": "Checked in test exposition revision 8"})
        submit(page, item.get_by_role("button"))
        page.reload()
        expect(checklist_row).to_contain_text("Checked in test exposition revision 8")

        page.goto("/")
        page.get_by_role("link", name="Add an Aircraft", exact=True).click()
        form = form_with(page, "records_expected")
        fill(
            form,
            {
                "registration": "G-TTFR",
                "type_rating": "Piper PA-28 Series (Lycoming)",
                "regime": "Part 21",
                "owner": "[Test Owner]",
                "records_expected": "3",
            },
        )
        submit(page, form.get_by_role("button"))
        page.goto("/transfers/")
        save(page, "Start the Checklist for G-TTFR", {}, "0 of 10 Complete")


def test_configuration_position_is_saved_before_baseline(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/transfers/")
        page.get_by_role("link", name="Set Up Configuration", exact=True).click()
        expect(page.locator("main h1")).to_have_text("Set Up Configuration, G-HKLM")
        expect(page.locator("main")).to_contain_text("A Configuration Baseline Is Not Signed")
        form = form_with(page, "product")
        form.locator('[name="tracked"]').check()
        fill(form, {"product": "Airframe", "chapter": "33", "name": "Test cabin light"})
        submit(page, form.get_by_role("button"))
        row = page.locator("main tr:not(.detail)").filter(has_text="Test cabin light")
        expect(row).to_contain_text("Not Recorded")
        record = reveal(row).locator("form")
        fill(
            record,
            {
                "part_number": "TEST-11",
                "serial_number": "TEST-12",
                "source": "Test inspection",
            },
        )
        submit(page, record.get_by_role("button"))
        page.reload()
        expect(row).to_contain_text("TEST-12")
        expect(row).to_contain_text("Test inspection")
        expect(page.get_by_role("button", name="Sign Configuration Baseline")).to_have_count(0)


def test_certifying_staff_evidence_is_retained_with_release_and_deferral(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    admin, _, _, planner, _ = personas["your-organisation"]
    scope = "G-ABCD Airframe, Inspection and Deferral"
    with signed_in(chromium, live_site, admin) as page:
        page.goto("/staff/")
        page.get_by_role("link", name="Sam Patel", exact=True).click()
        page.get_by_role("link", name="Record Maintenance Authorisation").click()
        save(
            page,
            "Save Authorisation",
            {"reference": "TEST-CA-81", "scope": scope, "valid_from": "2026-11-01"},
            "TEST-CA-81",
        )
    evidence = {
        "maintenance_authorisation": f"Sam Patel, TEST-CA-81, {scope}, From 1 November 2026",
        "scope_confirmed": "on",
    }
    with signed_in(chromium, live_site, planner) as page:
        page.goto("/defects/")
        page.get_by_role("link", name="Record a Defect", exact=True).click()
        save(
            page,
            "Record Defect",
            {
                **evidence,
                "aircraft": "G-ABCD",
                "title": "Test certified light deferral",
                "found_on": "2026-11-18",
                "chapter": "33",
                "system": "Lights",
                "decision": "Deferred",
                "basis": "Certifying Staff",
                "decided_on": "2026-11-18",
                "decided_by": "Sam Patel",
            },
            "Test certified light deferral",
        )
        assert definition(page, "Certification Evidence") == "TEST-CA-81, Scope Confirmed"

        choose_aircraft(page, "G-ABCD", "Maintenance Programme")
        page.get_by_role("link", name="Record Work Done", exact=True).click()
        work = "Inspection covered by TEST-CA-81"
        save(
            page,
            "Record Work",
            {"description": work, "dated": "2026-11-18", "hours": "6412.6", "cycles": "0"},
            work,
        )
        row = page.locator("main tr:not(.detail)").filter(has_text=work)
        reveal(row).get_by_role("link", name="Record Certificate of Release to Service").click()
        save(
            page,
            "Record Certificate",
            {
                **evidence,
                "reference": "TEST-RELEASE-81",
                "kind": "Organisation Certifying Staff",
                "issued_by": "Sam Patel",
                "issued_on": "2026-11-18",
            },
            "Sam Patel",
        )
        page.goto("/release-to-service/")
        expect(reveal(row)).to_contain_text("TEST-CA-81, Scope Confirmed")
        expect(page.locator("main")).to_contain_text("Unverified Historical Evidence")


def test_work_package_from_draft_to_release(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/staff/")
        page.get_by_role("link", name="Sam Patel", exact=True).click()
        page.get_by_role("link", name="Record Maintenance Authorisation").click()
        save(
            page,
            "Save Authorisation",
            {
                "reference": "TEST-PACKAGE-AUTH",
                "scope": "Piper PA-28 aircraft maintenance release",
                "valid_from": "2026-11-16",
            },
            "TEST-PACKAGE-AUTH",
        )

    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/maintenance-data/add/")
        save(
            page,
            "Record Maintenance Data",
            {
                "title": "Test Piper Maintenance Instructions",
                "author": "Piper",
                "kind": (
                    "Instructions for Continued Airworthiness, From a Type or "
                    "Supplementary Type Certificate Holder"
                ),
                "held": "on",
                "revision": "1",
                "revision_date": "2026-11-16",
                "check_due": "2026-11-30",
            },
            "Test Piper Maintenance Instructions",
        )
        page.goto("/work-packages/")
        page.get_by_role("link", name="Build a Work Package").click()
        save(
            page,
            "Build a Work Package",
            {
                "aircraft": "G-ABCD",
                "reference": "WP-2026-TEST",
                "title": "Test Landing Light",
                "location": "Bay 2",
                "starts_on": "2026-11-18",
                "ends_on": "2026-11-19",
            },
            "WP-2026-TEST",
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
                "title": "Test Landing Light Card",
                "data_set": "Test Piper Maintenance Instructions",
                "instruction": "Chapter 33",
                "planned_hours": "2.0",
                "critical": "on",
                "inspection_hours": "0.5",
            },
            "Test Landing Light Card",
        )
        page.get_by_role("link", name="Issue Work Package").click()
        save(page, "Issue Work Package", {}, "Revision 1")
        page.get_by_role("link", name="Record Signed Work").click()
        save(
            page,
            "Record Signed Work",
            {
                "performed_by": "Sam Patel",
                "revision": "1",
                "completed_on": "2026-11-18",
                "sign_off_reference": "Signed test card",
                "hours": "6412.6",
                "cycles": "0",
            },
            "Awaiting Inspection",
        )
        page.get_by_role("link", name="Record Independent Inspection").click()
        save(
            page,
            "Record Independent Inspection",
            {
                "inspector": "Chris Moore",
                "inspected_on": "2026-11-18",
                "qualification": "Test inspection authorisation",
                "evidence": "Function checked",
            },
            "1 of 1 Signed",
        )
        page.get_by_role("link", name="Record Package Release").click()
        save(
            page,
            "Record Package Release",
            {
                "reference": "TEST-PACKAGE-CRS",
                "issued_by": "Sam Patel",
                "issued_on": "2026-11-18",
                "maintenance_authorisation": "Sam Patel (TEST-PACKAGE-AUTH)",
                "scope_confirmed": "on",
                "verification": "Tools accounted for and panels refitted",
            },
            "Released",
        )
        page.get_by_role("link", name="Release Certificate", exact=True).click()
        expect(page.get_by_role("heading", name="TEST-PACKAGE-CRS")).to_be_visible()


def test_staffing_plan_records_part_145_shortfall_and_cover(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["second-organisation"][3]) as page:
        page.goto("/staffing/")
        page.get_by_role("link", name="Record Staffing Hours").click()
        values = {
            "approval": "Part-145, UK.145.[Number]",
            "month": "2026-12-01",
            "function": "Certifying Staff",
            "needed": "290",
            "employed": "192",
            "contracted": "0",
            "basis": "Required maintenance and time available before cover",
        }
        save(page, "Record Staffing Hours", values, "34%")
        open_row_action(page, "Certifying Staff", "Record a Shortfall Report")
        save(
            page,
            "Record a Shortfall Report",
            {"reported_on": "2026-11-16", "action": "Book extra qualified cover"},
            "Book extra qualified cover",
        )
        page.get_by_role("link", name="Record Staffing Hours").click()
        save(page, "Record Staffing Hours", {**values, "contracted": "88"}, "3%")
        page.get_by_role("link", name="Review the Plan", exact=True).click()
        save(
            page,
            "Review the Plan",
            {
                "approval": "Part-145, UK.145.[Number]",
                "reviewed_on": "2026-09-02",
                "outcome": "Reviewed for December",
            },
            "2 December 2026",
        )

    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/staffing/")
        page.get_by_role("link", name="Record an Absence").click()
        save(
            page,
            "Record an Absence",
            {
                "person": "Sam Patel",
                "kind": "Holiday",
                "starts_on": "2026-12-07",
                "ends_on": "2026-12-18",
            },
            "18 December 2026",
        )


def test_roster_records_fatigue_handover_and_publication(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/settings/planning/")
        page.get_by_role("link", name="Edit Planning Settings").click()
        save(page, "Save Planning Settings", {"load_margin_percent": "87"}, "87")
    with signed_in(chromium, live_site, personas["your-organisation"][3]) as page:
        page.goto("/staffing/roster/")
        page.get_by_role("link", name="Add Shift").click()
        save(
            page,
            "Add Shift",
            {
                "approval": "Part-CAO, UK.CAO.[Number]",
                "person": "Sam Patel",
                "area": "Hangar",
                "shift_name": "Day Shift",
                "maintenance": "on",
                "starts_at": "2026-11-19T08:00",
                "ends_at": "2026-11-19T19:00",
                "break_minutes": "30",
                "other_minutes": "0",
                "mitigation": "Additional supervision",
            },
            "Long Shift",
        )
        page.goto("/staffing/capacity/")
        expect(page.locator("main")).to_contain_text("10.5")
        expect(page.locator("main")).to_contain_text("Due and Not Yet Planned")
        page.goto("/staffing/roster/")
        page.get_by_role("link", name="Publish Roster").click()
        save(page, "Publish Roster", {"note": "Duty hours reviewed"}, "Duty hours reviewed")
        page.get_by_role("link", name="Record Handover").click()
        save(
            page,
            "Record Handover",
            {
                "outgoing": "Sam Patel",
                "incoming": "[Browser Test Continuing Airworthiness Manager]",
                "handed_at": "2026-11-18T16:30",
                "stage": "Inspection outstanding",
                "parts": "Tools checked in",
            },
            "Awaiting Acknowledgement",
        )
        open_row_action(page, "Long Shift", "Withdraw Shift")
        save(page, "Withdraw Shift", {"reason": "Shift moved"}, "No Shifts Recorded")

    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        page.goto("/staffing/roster/")
        open_row_action(page, "Awaiting Acknowledgement", "Acknowledge")
        save(page, "Acknowledge Handover", {}, "Handovers")
        expect(page.get_by_text("Awaiting Acknowledgement", exact=True)).to_have_count(0)


def test_planning_policy_records_are_editable(
    chromium: Browser, live_site: str, personas: dict[str, tuple[Account, ...]]
) -> None:
    with signed_in(chromium, live_site, personas["your-organisation"][0]) as page:
        page.goto("/settings/planning/")
        page.get_by_role("link", name="Record Bank Holiday").click()
        save(
            page,
            "Record Bank Holiday",
            {"on": "2026-12-25", "name": "Christmas Day"},
            "Christmas Day",
        )
        page.get_by_role("link", name="Record Shift Pattern").click()
        save(
            page,
            "Record Shift Pattern",
            {
                "name": "Day Shift",
                "area": "Hangar",
                "days": "Monday to Friday",
                "starts_at": "08:00",
                "ends_at": "16:30",
                "break_minutes": "30",
            },
            "Day Shift",
        )
        page.get_by_role("link", name="Record Staffing Minimum").click()
        save(
            page,
            "Record Staffing Minimum",
            {
                "approval": "Part-CAO, UK.CAO.[Number]",
                "function": "Certifying Staff",
                "minimum": "1",
                "normal": "2",
                "applies_on": "Hangar Working Days",
            },
            "Hangar Working Days",
        )
        page.goto("/staffing/capacity/?week=2026-12-21")
        expect(page.locator("main")).to_contain_text("40.0")
