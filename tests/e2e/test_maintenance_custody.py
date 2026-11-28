"""Live custody forms and independent issue contention on the published Stores ledger."""

import threading
from typing import Any

import psycopg
from playwright.sync_api import Browser, expect

from tests.e2e.browser import definition, fill, form_with, save, signed_in, submit
from tests.e2e.conftest import Account, RunningSite
from tests.e2e.test_stores import _application, _as, site_dsn

ISSUE = """
INSERT INTO logistics_stockallocation (
    id, organisation_id, submission, entered_at, posting_id, kind, source_id, destination_id,
    card_id, preceding_id, substitution_id, quantity, required_identity, applicable_source,
    evidence, recorded_on, appointment_id
)
SELECT gen_random_uuid(), event.organisation_id, gen_random_uuid(), now(), event.posting_id,
       'Issue', event.source_id, NULL, event.card_id, event.id, event.substitution_id,
       event.quantity,
       event.required_identity, event.applicable_source, 'Independent PostgreSQL issue',
       event.recorded_on, %(appointment)s
  FROM logistics_stockallocation event
 WHERE event.id = %(reservation)s
"""


def _race_issue(site: RunningSite, username: str) -> None:
    with psycopg.connect(site_dsn(site), autocommit=True) as owner:
        row = owner.execute(
            "SELECT account.organisation_id, account.id, reservation.id, grant_record.id "
            "FROM accounts_user account JOIN people_person person ON person.user_id = account.id "
            "JOIN logistics_stockappointment grant_record ON grant_record.person_id = person.id "
            "JOIN logistics_stockallocation reservation "
            " ON reservation.organisation_id = account.organisation_id "
            "WHERE account.username = %s AND grant_record.action = 'Issue' "
            "AND reservation.kind = 'Reserve' AND NOT EXISTS "
            " (SELECT 1 FROM logistics_stockallocation child "
            "WHERE child.preceding_id = reservation.id)",
            [username],
        ).fetchone()
    assert row is not None
    organisation, actor, reservation, appointment = row
    values: dict[str, Any] = {"appointment": appointment, "reservation": reservation}
    outcomes: list[str] = []
    with _application(site) as first, _application(site) as second:
        _as(first, str(organisation), str(actor))
        _as(second, str(organisation), str(actor))
        first.execute(ISSUE, values)

        def contend() -> None:
            try:
                second.execute(ISSUE, values)
                second.commit()
                outcomes.append("committed")
            except (psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation) as error:
                outcomes.append(type(error).__name__)
                second.rollback()

        thread = threading.Thread(target=contend)
        thread.start()
        thread.join(timeout=1)
        assert thread.is_alive(), "The competing issue must wait for the lot lock"
        first.commit()
        thread.join(timeout=10)
        assert outcomes == ["CheckViolation"]


def test_stores_reserves_issues_and_quarantines_a_maintenance_return(
    chromium: Browser,
    running_site: RunningSite,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    live_site = running_site.address
    ours = personas["your-organisation"]
    with signed_in(chromium, live_site, ours[0]) as page:
        certifier = "[Browser Test Continuing Airworthiness Manager]"
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
        for duty in (
            "Reserve Stock for a Work Card",
            "Issue Stock to Maintenance",
            "Accept Maintenance Returns to Quarantine",
            "Move Unreserved Stock to Quarantine",
            "Resolve and Post Stock",
            "Move Stock Between Locations",
            "Count Stock",
            "Adjust Stock From a Count",
        ):
            page.goto("/stores/locations/")
            page.get_by_role("link", name="Stores Appointments").click()
            page.get_by_role("link", name="Record a Stores Appointment").click()
            save(
                page,
                "Record a Stores Appointment",
                {
                    "person": certifier,
                    "approval": "Part-CAO, UK.CAO.[Number]",
                    "action": duty,
                    "starts_on": "2026-11-18",
                    "ends_on": "2026-11-20",
                    "evidence": "Synthetic signed custody appointment",
                },
                duty,
            )
        page.get_by_role("row").filter(has_text="Reserve Stock for a Work Card").filter(
            has_text=certifier
        ).get_by_role("link", name="Withdraw Appointment").click()
        save(
            page,
            "Withdraw Stores Appointment",
            {"evidence": "Corrected synthetic appointment"},
            "Corrected synthetic appointment",
        )
        page.get_by_role("link", name="Record a Stores Appointment").click()
        save(
            page,
            "Record a Stores Appointment",
            {
                "person": certifier,
                "approval": "Part-CAO, UK.CAO.[Number]",
                "action": "Reserve Stock for a Work Card",
                "starts_on": "2026-11-18",
                "ends_on": "2026-11-20",
                "evidence": "Replacement signed appointment",
            },
            "Replacement signed appointment",
        )
        for name, kind, secure in (
            ("Synthetic Main", "Serviceable Stores", ""),
            ("Synthetic Cage", "Quarantine", "on"),
        ):
            page.goto("/stores/locations/")
            page.get_by_role("link", name="Add a Stores Location", exact=True).click()
            save(
                page,
                "Add a Stores Location",
                {
                    "name": name,
                    "station": "ZRH",
                    "kind": kind,
                    "holds_components": "on",
                    "secure": secure,
                },
                name,
            )
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
        page.get_by_role("link", name="Resolve for Stock", exact=True).click()
        main_store = "Synthetic Main (Serviceable Stores)"
        quarantine = "Synthetic Cage (Quarantine)"
        save(
            page,
            "Resolve RX-002 for Stock",
            {
                "unit": "Each",
                "part_number": "PN-TEST-713",
                "serial_number": "SN-TEST-863",
                "shelf_life_basis": "Not Applicable",
                "location": main_store,
                "evidence": "Synthetic verified Form 1 mapping",
                "authority": "Published Stores duty",
            },
            "None. Ready to Post",
        )
        save(page, "Post to Stock", {"authority": "Published Stores duty"}, "Posted to Stock")
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
        assert definition(page, "On Hand") == "1 Each"
        assert definition(page, "Reserved Quantity") == "1"
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
        _race_issue(running_site, ours[1].username)
        save(
            page,
            "Issue Reserved Stock",
            {"evidence": "Replayed issue form"},
            "Already Been Continued",
        )
        page.goto(entry_url)
        expect(page.get_by_text("Issued to Maintenance", exact=True)).to_have_count(1)
        assert definition(page, "On Hand") == "0 Each"
        assert definition(page, "Reserved Quantity") == "0"
        page.get_by_role("link", name="Return Stock to Quarantine", exact=True).click()
        save(
            page,
            "Return Stock to Quarantine",
            {"destination": quarantine, "evidence": "Opened packaging held for fresh inspection"},
            "Returned to Quarantine",
        )
        assert definition(page, "On Hand") == "1 Each"
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
