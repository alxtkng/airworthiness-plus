"""Stores once-only posting and ledger invariants across independent PostgreSQL sessions.

REQ-358, handoff cases S02 and S09. The sample is seeded and committed in a
disposable database. Each case runs on its own clone, with every competing
caller on its own connection under the application role and row-level
security. ``tests/stores_race.py`` drives the application's services;
the direct cases below bypass them to show that PostgreSQL alone holds.
"""

import json
import os
import secrets
import subprocess
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

import psycopg
import pytest
from django.conf import settings
from psycopg import sql

ROOT = Path(__file__).resolve().parents[1]
APPLICATION_ROLE = "airworthiness_application"


@dataclass(frozen=True)
class Seeded:
    admin: psycopg.Connection[tuple[Any, ...]]
    template: str
    env: dict[str, str]
    organisation: str
    lucy: str


def _parameters(database: str) -> dict[str, Any]:
    default = settings.DATABASES["default"]
    return {
        "dbname": database,
        "host": default["HOST"],
        "port": default["PORT"] or 5432,
        "user": default["USER"],
        "password": default["PASSWORD"] or None,
    }


@pytest.fixture(scope="module")
def seeded() -> Iterator[Seeded]:
    template = f"airworthiness_stores_race_{secrets.token_hex(5)}"
    env = dict(
        os.environ,
        DJANGO_SETTINGS_MODULE="airworthiness_plus.settings",
        AIRWORTHINESS_DATABASE_NAME=template,
        AIRWORTHINESS_DATABASE_OWNER_WORK="true",
    )
    accounts = [
        [
            {
                "username": f"accountable.manager@{domain}.example",
                "role": "Administrator",
                "password": secrets.token_urlsafe(24),
            }
        ]
        for domain in ("your-organisation", "second-organisation")
    ]
    with psycopg.connect(**_parameters("postgres"), autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(template)))
        try:
            subprocess.run(
                [sys.executable, "-m", "tests.e2e.server", "seed"],
                input=json.dumps(accounts),
                text=True,
                cwd=ROOT,
                env=env,
                check=True,
                timeout=170,
            )
            with psycopg.connect(**_parameters(template)) as owner:
                organisation, lucy = owner.execute(
                    "SELECT organisation.id::text, person.user_id::text "
                    "FROM organisations_organisation organisation "
                    "JOIN people_person person ON person.organisation_id = organisation.id "
                    "JOIN accounts_user account ON account.id = person.user_id "
                    "WHERE organisation.approval_reference = 'UK.CAO.[Number]' "
                    "AND account.username = 'lucy.grant@your-organisation.example'"
                ).fetchone() or ("", "")
            yield Seeded(
                admin,
                template,
                dict(env, AIRWORTHINESS_DATABASE_OWNER_WORK="false"),
                organisation,
                lucy,
            )
        finally:
            admin.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(template))
            )


@pytest.fixture
def clone(seeded: Seeded) -> Iterator[str]:
    name = f"{seeded.template}_{secrets.token_hex(3)}"
    seeded.admin.execute(
        sql.SQL("CREATE DATABASE {} TEMPLATE {}").format(
            sql.Identifier(name), sql.Identifier(seeded.template)
        )
    )
    try:
        yield name
    finally:
        seeded.admin.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def race(seeded: Seeded, database: str, scenario: str) -> dict[str, Any]:
    done = subprocess.run(  # noqa: S603  fixed module and arguments
        [sys.executable, "-m", "tests.stores_race", scenario, seeded.organisation, seeded.lucy],
        cwd=ROOT,
        env=dict(seeded.env, AIRWORTHINESS_DATABASE_NAME=database),
        check=True,
        capture_output=True,
        text=True,
        timeout=120,
    )
    result: dict[str, Any] = json.loads(done.stdout.strip().splitlines()[-1])
    return result


def session(seeded: Seeded, database: str) -> psycopg.Connection[tuple[Any, ...]]:
    """Open an independent session as the application, for the sample's organisation."""
    connection = psycopg.connect(**_parameters(database))
    connection.execute(f"SET ROLE {APPLICATION_ROLE}")
    connection.execute(
        "SELECT set_config('airworthiness.organisation', %s, false), "
        "set_config('airworthiness.user', %s, false)",
        [seeded.organisation, seeded.lucy],
    )
    connection.commit()
    return connection


def one(connection: psycopg.Connection[tuple[Any, ...]], query: str, *values: Any) -> Any:
    row = connection.execute(query, values).fetchone()
    assert row is not None, query
    return row[0]


def test_s02_parallel_callers_post_a_disposition_exactly_once(seeded: Seeded, clone: str) -> None:
    result = race(seeded, clone, "post")
    outcomes = result["results"]
    assert all(outcome.startswith("ok:") for outcome in outcomes), outcomes
    assert len(set(outcomes)) == 1
    assert result["ledger"]["postings"]["RX-002"] == 1
    assert ["RX-002", "BAY-A", "1"] in result["ledger"]["positions"]


def test_s09_a_concurrent_overspend_commits_at_most_once(seeded: Seeded, clone: str) -> None:
    result = race(seeded, clone, "overspend")
    outcomes = sorted(result["results"])
    assert outcomes[0].startswith("ok:"), outcomes
    assert outcomes[1].startswith("refused:RefusedError:The Source Location Holds Less"), outcomes
    positions = result["ledger"]["positions"]
    assert ["RX-006", "BAY-C", "4"] in positions
    assert ["RX-006", "OIL-2", "20"] in positions


def test_s09_an_adjustment_and_a_competing_move_cannot_both_apply(
    seeded: Seeded, clone: str
) -> None:
    result = race(seeded, clone, "adjust_or_move")
    outcomes = result["results"]
    assert sum(outcome.startswith("ok:") for outcome in outcomes) == 1, outcomes
    bolts = [line for line in result["ledger"]["positions"] if line[0] == "RX-007"]
    assert bolts in ([["RX-007", "BAY-B", "46"]], [["RX-007", "BAY-A", "50"]])


def test_s09_postgres_alone_serialises_direct_movements(seeded: Seeded, clone: str) -> None:
    """Without the application: the second insert waits for the first and is then refused."""
    first, second = session(seeded, clone), session(seeded, clone)
    try:
        posting, source, destination, grant = first.execute(
            "SELECT posting.id, source.id, target.id, grant_record.id "
            "FROM logistics_stockposting posting "
            "JOIN logistics_receivingdisposition decision ON decision.id = posting.disposition_id "
            "JOIN logistics_receipt receipt ON receipt.id = decision.receipt_id "
            "CROSS JOIN logistics_storeslocation source "
            "CROSS JOIN logistics_storeslocation target "
            "JOIN logistics_storesappointment grant_record ON grant_record.action = 'Move' "
            "JOIN people_person person ON person.id = grant_record.person_id "
            "WHERE receipt.delivery_reference = 'RX-006' AND source.code = 'BAY-C' "
            "AND target.code = 'OIL-2' AND person.user_id = %s",
            [seeded.lucy],
        ).fetchone() or (None, None, None, None)
        insert = (
            "INSERT INTO logistics_stockmovement (id, organisation_id, submission, entered_at, "
            "posting_id, kind, source_id, destination_id, quantity, moved_on, evidence, "
            "count_id, recorded_on, appointment_id) VALUES (%s, %s, %s, now(), %s, 'Transfer', "
            "%s, %s, 20, '2026-11-18', 'Direct competing move', NULL, '2026-11-18', %s)"
        )
        values = [posting, source, destination, grant]
        first.execute(insert, [uuid4(), seeded.organisation, uuid4(), *values])
        outcome: dict[str, str] = {}

        def compete() -> None:
            try:
                second.execute(insert, [uuid4(), seeded.organisation, uuid4(), *values])
                second.commit()
                outcome["second"] = "committed"
            except psycopg.errors.CheckViolation as error:
                outcome["second"] = str(error).splitlines()[0]
                second.rollback()

        thread = threading.Thread(target=compete)
        thread.start()
        thread.join(timeout=1)
        assert thread.is_alive(), "The second session must wait for the first"
        first.commit()
        thread.join(timeout=10)
        assert outcome == {"second": "The source location holds less than this movement"}
        assert one(first, "SELECT logistics_stock_on_hand(%s, %s)", posting, source) == 4
        assert one(first, "SELECT logistics_stock_on_hand(%s, %s)", posting, destination) == 20
    finally:
        first.close()
        second.close()


def test_s02_postgres_alone_refuses_a_second_posting_from_a_parallel_session(
    seeded: Seeded, clone: str
) -> None:
    first, second = session(seeded, clone), session(seeded, clone)
    try:
        decision, location, grant = first.execute(
            "SELECT decision.id, location.id, grant_record.id "
            "FROM logistics_receivingdisposition decision "
            "JOIN logistics_receipt receipt ON receipt.id = decision.receipt_id "
            "CROSS JOIN logistics_storeslocation location "
            "JOIN logistics_storesappointment grant_record ON grant_record.action = 'Post' "
            "JOIN people_person person ON person.id = grant_record.person_id "
            "WHERE receipt.delivery_reference = 'RX-002' AND location.code = 'BAY-A' "
            "AND person.user_id = %s",
            [seeded.lucy],
        ).fetchone() or (None, None, None)
        evidence = uuid4()
        first.execute(
            "INSERT INTO logistics_postingevidence (id, organisation_id, submission, entered_at, "
            "disposition_id, unit, quantity, manufacturer, part_number, serial, batch, "
            "specification, shelf_life_basis, shelf_life_to, location_id, tag, assessed_on, "
            "evidence, appointment_id) VALUES (%s, %s, %s, now(), %s, 'Each', 1, '', 'PN-D', "
            "'SN-D', '', '', 'Not Applicable', NULL, %s, '', '2026-11-18', 'Direct', %s)",
            [evidence, seeded.organisation, uuid4(), decision, location, grant],
        )
        first.commit()
        insert = (
            "INSERT INTO logistics_stockposting (id, organisation_id, submission, entered_at, "
            "disposition_id, evidence_id, kind, location_rules, posted_on, appointment_id) "
            "VALUES (%s, %s, %s, now(), %s, %s, 'Stock', 'Direct', '2026-11-18', %s)"
        )
        values = [decision, evidence, grant]
        first.execute(insert, [uuid4(), seeded.organisation, uuid4(), *values])
        outcome: dict[str, str] = {}

        def compete() -> None:
            try:
                second.execute(insert, [uuid4(), seeded.organisation, uuid4(), *values])
                second.commit()
                outcome["second"] = "committed"
            except psycopg.errors.UniqueViolation:
                outcome["second"] = "refused"
                second.rollback()

        thread = threading.Thread(target=compete)
        thread.start()
        thread.join(timeout=1)
        assert thread.is_alive()
        first.commit()
        thread.join(timeout=10)
        assert outcome == {"second": "refused"}
        assert (
            one(
                first,
                "SELECT count(*) FROM logistics_stockmovement movement "
                "JOIN logistics_stockposting posting ON posting.id = movement.posting_id "
                "WHERE posting.disposition_id = %s",
                decision,
            )
            == 1
        )
    finally:
        first.close()
        second.close()
