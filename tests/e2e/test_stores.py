"""The Stores posting contract for Goods In acceptances."""

import threading
from typing import Any

import psycopg
from playwright.sync_api import Browser, expect

from tests.e2e.browser import definition, fill, form_with, save, signed_in, submit
from tests.e2e.conftest import Account, RunningSite


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


def test_rx_002_is_resolved_posted_moved_counted_and_adjusted_once(
    chromium: Browser,
    live_site: str,
    personas: dict[str, tuple[Account, ...]],
) -> None:
    """REQ-358. The manager resolves and posts RX-002, holds RX-004 and reconciles a count."""
    with signed_in(chromium, live_site, personas["your-organisation"][1]) as page:
        for name, kind, holds in (
            ("Sample Serviceable Bay A", "Serviceable Stores", "holds_components"),
            ("Sample Serviceable Bay B", "Serviceable Stores", "holds_components"),
            ("Sample Secure Quarantine Cage", "Quarantine", "holds_components"),
        ):
            page.goto("/stores/locations/")
            page.get_by_role("link", name="Add a Stores Location", exact=True).click()
            form = form_with(page, "name")
            fill(form, {"name": name, "kind": kind, holds: "on", "secure": "on"})
            submit(page, form.get_by_role("button", name="Add a Stores Location"))
            expect(page.get_by_role("cell", name=name, exact=True)).to_be_visible()

        page.goto("/stores/")
        page.get_by_role("link", name="Stabilator Trim Cable Assembly", exact=True).click()
        entry_url = page.url
        # The role alone offers no Stores control. A dated appointment does (REQ-358).
        expect(page.get_by_role("link", name="Resolve for Stock", exact=True)).to_have_count(0)
        for duty in (
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
                    "person": "[Browser Test Continuing Airworthiness Manager]",
                    "approval": "Part-CAO, UK.CAO.[Number]",
                    "action": duty,
                    "starts_on": "2026-11-18",
                    "ends_on": "2026-11-30",
                    "evidence": "Synthetic signed Stores appointment",
                },
                duty,
            )
        page.goto(entry_url)
        page.get_by_role("link", name="Resolve for Stock", exact=True).click()
        form = form_with(page, "unit")
        fill(
            form,
            {
                "unit": "Each",
                "part_number": "SAMPLE-PN-713",
                "serial_number": "SAMPLE-SN-002",
                "location": "Sample Serviceable Bay A (Serviceable Stores)",
                "shelf_life_basis": "Not Applicable",
                "evidence": "Sample release folder RX-002 and receiving checks reviewed",
                "authority": "Sample Stores Appointment ST-1",
            },
        )
        submit(page, form.get_by_role("button", name="Resolve RX-002 for Stock"))
        expect(page).to_have_url(entry_url)
        assert definition(page, "Posting Blockers") == "None. Ready to Post"
        form = form_with(page, "posted_on")
        fill(form, {"authority": "Sample Stores Appointment ST-1"})
        action = form.get_attribute("action")
        token = form.locator('[name="csrfmiddlewaretoken"]').input_value()
        posted_on = form.locator('[name="posted_on"]').input_value()
        submit(page, form.get_by_role("button", name="Post to Stock"))
        # A repeated submission of the same form returns the original posting.
        assert action is not None
        replay = page.request.post(
            action,
            form={
                "csrfmiddlewaretoken": token,
                "posted_on": posted_on,
                "authority": "Sample Stores Appointment ST-1",
            },
            headers={"Referer": entry_url},
        )
        assert replay.ok
        page.goto(entry_url)
        assert definition(page, "Posting State") == "Posted to Stock"
        assert definition(page, "Available Quantity") == "1"
        expect(page.get_by_role("cell", name="Intake", exact=True)).to_have_count(1)

        page.get_by_role("link", name="Move Stock", exact=True).click()
        form = form_with(page, "to_location")
        fill(
            form,
            {
                "from_location": "Sample Serviceable Bay A (Serviceable Stores)",
                "to_location": "Sample Serviceable Bay B (Serviceable Stores)",
                "quantity": "1",
                "evidence": "Sample transfer note T-1",
                "authority": "Sample Stores Appointment ST-1",
            },
        )
        submit(page, form.get_by_role("button", name="Move Stock"))
        expect(page).to_have_url(entry_url)
        expect(page.get_by_role("cell", name="Transfer", exact=True)).to_have_count(1)

        page.get_by_role("link", name="Record a Stock Count", exact=True).click()
        form = form_with(page, "counted_quantity")
        fill(
            form,
            {
                "location": "Sample Serviceable Bay B (Serviceable Stores)",
                "counted_quantity": "0",
                "evidence": "Sample count sheet C-1",
            },
        )
        submit(page, form.get_by_role("button", name="Record a Stock Count"))
        assert definition(page, "On Hand") == "1 Each"
        page.get_by_role("link", name="Adjust From This Count", exact=True).click()
        form = form_with(page, "evidence")
        fill(
            form,
            {
                "evidence": "Sample variance investigation V-1",
                "authority": "Sample Adjustment Authority A-1",
            },
        )
        submit(page, form.get_by_role("button", name="Adjust by -1 From the Count"))
        expect(page).to_have_url(entry_url)
        assert definition(page, "On Hand") == "0 Each"
        assert definition(page, "Available Quantity") == "0"

        page.goto("/stores/")
        page.get_by_role("link", name="RX-004", exact=True).click()
        assert definition(page, "Posting State") == "Quarantine Hold, Details to Verify"
        page.get_by_role("link", name="Resolve for Stock", exact=True).click()
        form = form_with(page, "unit")
        fill(
            form,
            {
                "unit": "Each",
                "part_number": "SAMPLE-ALTERNATOR",
                "serial_number": "SAMPLE-SN-004",
                "location": "Sample Secure Quarantine Cage (Quarantine)",
                "shelf_life_basis": "Not Applicable",
                "evidence": "Sample quarantine tag Q-004 and decision reviewed",
                "authority": "Sample Stores Appointment ST-1",
            },
        )
        submit(page, form.get_by_role("button", name="Resolve RX-004 for Stock"))
        form = form_with(page, "posted_on")
        fill(form, {"authority": "Sample Stores Appointment ST-1"})
        submit(page, form.get_by_role("button", name="Post to Stock"))
        assert definition(page, "Posting State") == "Quarantine Hold"
        assert definition(page, "On Hand") == "1 Each"
        assert definition(page, "Available Quantity") == "0"
        page.goto("/stores/")
        page.get_by_role("link", name="RX-003", exact=True).click()
        assert definition(page, "Posting State") == "Returned to Supplier"
        expect(page.get_by_role("link", name="Resolve for Stock")).to_have_count(0)


def _application(site: RunningSite) -> psycopg.Connection[tuple[Any, ...]]:
    env = site.database.env
    connection = psycopg.connect(
        host=env["AIRWORTHINESS_DATABASE_HOST"],
        port=env["AIRWORTHINESS_DATABASE_PORT"],
        dbname=site.name,
        user=env["AIRWORTHINESS_DATABASE_USER"],
        password=env["AIRWORTHINESS_DATABASE_PASSWORD"],
    )
    connection.execute("SET ROLE airworthiness_application")
    return connection


def _as(connection: psycopg.Connection[tuple[Any, ...]], organisation: str, user: str) -> None:
    connection.execute("SELECT set_config('airworthiness.organisation', %s, true)", [organisation])
    connection.execute("SELECT set_config('airworthiness.user', %s, true)", [user])


POSTING = """
INSERT INTO logistics_stockposting (
    id, organisation_id, disposition_id, resolution_id, held, unit, quantity, part_number,
    serial_number, batch_number, specification, location_id, location_name, location_kind,
    shelf_life_basis, physical_on, posted_on, actor_id, actor_name, authority, recorded_at
) VALUES (
    gen_random_uuid(), %(organisation)s, %(disposition)s, %(resolution)s, false, 'Each', 1,
    '', '', '', '', %(location)s, '', '', '', '2026-11-16', '2026-11-18', %(person)s,
    'Concurrent Test', 'Concurrent ST-1', now()
)
"""

TRANSFER = """
INSERT INTO logistics_stockmovement (
    id, organisation_id, lot_id, kind, from_location_id, to_location_id, quantity, moved_on,
    actor_id, actor_name, authority, evidence, recorded_at
) VALUES (
    gen_random_uuid(), %(organisation)s, %(lot)s, 'Transfer', %(location)s, %(second)s, 1,
    '2026-11-18', %(person)s, 'Concurrent Test', 'Concurrent ST-1', 'Concurrent move', now()
)
"""


def test_two_committed_sessions_cannot_post_or_overspend_twice(
    running_site: RunningSite, personas: dict[str, tuple[Account, ...]]
) -> None:
    """REQ-358, handoff S02 and S09. Independent PostgreSQL sessions race on RX-002."""
    manager = personas["your-organisation"][1].username
    with psycopg.connect(site_dsn(running_site), autocommit=True) as admin:
        row = admin.execute(
            "SELECT decision.id, decision.organisation_id, account.id, person.id "
            "FROM logistics_receivingdisposition decision "
            "JOIN logistics_receipt receipt ON receipt.id = decision.receipt_id "
            "JOIN accounts_user account ON account.organisation_id = decision.organisation_id "
            "JOIN people_person person ON person.user_id = account.id "
            "WHERE receipt.delivery_reference = 'RX-002' AND account.username = %s",
            [manager],
        ).fetchone()
    assert row is not None
    disposition, organisation, user, person = (str(value) for value in row)
    values: dict[str, str] = {
        "organisation": organisation,
        "disposition": disposition,
        "person": person,
    }
    with _application(running_site) as setup:
        _as(setup, organisation, user)
        # The person's own dated appointments for the Stores duties raced below (REQ-358).
        for duty in ("Post", "Move", "Count", "Adjust"):
            setup.execute(
                "INSERT INTO logistics_stockappointment (id, organisation_id, submission, "
                "entered_at, person_id, approval_id, action, starts_on, ends_on, evidence) "
                "SELECT gen_random_uuid(), %s, gen_random_uuid(), now(), %s, approval.id, %s, "
                "'2026-11-01', '2026-12-31', 'Synthetic signed appointment' "
                "FROM organisations_approval approval WHERE approval.approval = 'Part-CAO'",
                [organisation, person, duty],
            )
        for key, name in (("location", "Race Bay A"), ("second", "Race Bay B")):
            created = setup.execute(
                "INSERT INTO logistics_storelocation (id, organisation_id, name, kind, "
                "holds_components, holds_standard_parts, holds_materials, secure, "
                "storage_conditions, active) VALUES (gen_random_uuid(), %s, %s, "
                "'Serviceable Stores', true, false, false, false, '', true) RETURNING id",
                [organisation, name],
            ).fetchone()
            assert created is not None
            values[key] = str(created[0])
        resolution = setup.execute(
            "INSERT INTO logistics_stockresolution (id, organisation_id, disposition_id, unit, "
            "part_number, serial_number, batch_number, specification, location_id, "
            "shelf_life_basis, shelf_life_rule, evidence, evidence_on, recorded_by_id, "
            "recorded_by_name, authority, recorded_at) VALUES (gen_random_uuid(), %s, %s, "
            "'Each', 'RACE-PN', '', 'RACE-LOT', '', %s, 'Not Applicable', '', 'Race evidence', "
            "'2026-11-18', %s, 'Concurrent Test', 'Concurrent ST-1', now()) RETURNING id",
            [organisation, disposition, values["location"], person],
        ).fetchone()
        assert resolution is not None
        values["resolution"] = str(resolution[0])
        setup.commit()

    def race(statement: str) -> dict[str, str]:
        outcome: dict[str, str] = {}
        with _application(running_site) as first, _application(running_site) as second:
            _as(first, organisation, user)
            _as(second, organisation, user)
            first.execute(statement, values)

            def contend() -> None:
                try:
                    second.execute(statement, values)
                    second.commit()
                    outcome["second"] = "committed"
                except (psycopg.errors.UniqueViolation, psycopg.errors.CheckViolation) as error:
                    outcome["second"] = type(error).__name__
                    second.rollback()

            thread = threading.Thread(target=contend)
            thread.start()
            thread.join(timeout=1)
            assert thread.is_alive(), "The second session must wait for the first"
            first.commit()
            thread.join(timeout=10)
        return outcome

    assert race(POSTING) == {"second": "UniqueViolation"}
    with psycopg.connect(site_dsn(running_site), autocommit=True) as admin:
        lots = admin.execute(
            "SELECT id FROM logistics_stockposting WHERE disposition_id = %s", [disposition]
        ).fetchall()
        assert len(lots) == 1
        values["lot"] = str(lots[0][0])
        intakes = admin.execute(
            "SELECT count(*) FROM logistics_stockmovement WHERE lot_id = %s", [values["lot"]]
        ).fetchone()
        assert intakes == (1,)
    assert race(TRANSFER) == {"second": "CheckViolation"}
    with psycopg.connect(site_dsn(running_site), autocommit=True) as admin:
        balances = admin.execute(
            "SELECT logistics_stock_balance(%s, %s), logistics_stock_balance(%s, %s)",
            [values["lot"], values["location"], values["lot"], values["second"]],
        ).fetchone()
        assert balances == (0, 1)


def site_dsn(site: RunningSite) -> str:
    return psycopg.conninfo.make_conninfo(site.database.admin.info.dsn, dbname=site.name)
