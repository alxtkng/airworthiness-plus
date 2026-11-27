"""A customer record for each owner or operator (REQ-207 to REQ-210).

Decisions.md, Canvas Build, decision 3: the free text Owned By on an
aircraft gives way to a customer record, and what was typed is kept. The
customers are those of design-system/SampleData.md, Commercial, and the
Customers board: 7, one for each aircraft.
"""

import io
import json
import re
import zipfile
from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.loader import MigrationLoader
from django.db.migrations.state import ProjectState
from django.http import HttpResponse
from django.test.utils import CaptureQueriesContext

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft import sql as aircraft_sql
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.customers import services
from airworthiness_plus.customers.models import Customer, Kind
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.sample import build
from tests.conftest import as_owner, as_owner_who_is_not_a_superuser
from tests.support import FLEET, Sample, add_sample_fleet, get, page, post, signed_in

pytestmark = pytest.mark.django_db


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    return add_sample_fleet(sample)


def rows(body: str) -> list[list[str]]:
    """Return the cells of each row of the first table of the page."""
    table = body.split("<table>", 1)[1].split("</table>", 1)[0]
    found = []
    for row in re.findall(r"<tr>\s*(<td>.*?)</tr>", table, flags=re.S):
        cells = re.findall(r"<td>(.*?)</td>", row, flags=re.S)
        found.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
    return found


def customer(sample: Sample, name: str) -> Customer:
    with working_for(sample.ours.id, sample.reader.id):
        return Customer.objects.get(name=name)


def aircraft_of(sample: Sample, registration: str) -> Aircraft:
    with working_for(sample.ours.id, sample.reader.id):
        return Aircraft.objects.select_related("customer").get(registration=registration)


# The sample

# SampleData.md, Commercial, and the Customers board. Customer Since is given
# there by month; the first day of the month is taken.
EXPECTED = [
    ["[Flying Club Name]", "Flying Club", "G-DGHI", "1 March 2025"],
    ["[Owner Name G-ABCD]", "Pilot-Owner", "G-ABCD", "1 March 2026"],
    ["[Owner Name G-EJKL]", "Pilot-Owner", "G-EJKL", "1 December 2025"],
    ["[Owner Name G-FMNO]", "Pilot-Owner", "G-FMNO", "1 May 2024"],
    ["[Owner Name G-HKLM]", "Pilot-Owner", "G-HKLM", "1 November 2026"],
    ["[Syndicate Name G-BXYZ]", "Syndicate of 6", "G-BXYZ", "1 January 2025"],
    ["[Syndicate Name G-CDEF]", "Syndicate of 4", "G-CDEF", "1 April 2024"],
]


def test_the_customers_page_lists_the_7_customers_of_the_sample(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-207, REQ-210. Golden, from the Customers board: 7 Customers, 7 Aircraft."""
    body = page(signed_in(sample.reader), "/customers/")
    assert rows(body) == EXPECTED
    assert "<p>7 Customers, 7 Aircraft</p>" in body
    assert '<li><a href="/customers/" aria-current="location">Customers</a></li>' in body
    assert "<li>Commercial</li>" in body


def test_owned_by_on_the_fleet_is_what_the_sample_gives(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-208. SampleData.md, Fleet, Owned By: the kind of owner, as before."""
    for registration, _, owned_by, _ in FLEET:
        assert aircraft_of(sample, registration).owner == owned_by, registration
    hklm = aircraft_of(sample, "G-HKLM")
    assert (hklm.customer.name, hklm.owner) == ("[Owner Name G-HKLM]", "Pilot-Owner")
    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-BXYZ'].id}/")
    assert "<dt>Owned By</dt><dd>Syndicate of 6</dd>" in body
    bxyz = customer(sample, "[Syndicate Name G-BXYZ]")
    assert (
        f'<dt>Customer</dt><dd><a href="/customers/{bxyz.id}/">[Syndicate Name G-BXYZ]</a></dd>'
        in body
    )


def test_a_customer_with_no_kind_recorded_is_shown_by_name(sample: Sample) -> None:
    """REQ-208. What was typed as Owned By before customers were records is still shown."""
    with working_for(sample.ours.id, sample.lucy.id):
        typed = services.add_customer(organisation=sample.ours, name="Pilot-Owner")
        assert (typed.kind, typed.description, typed.owned_by) == ("", "", "Pilot-Owner")
        club = services.add_customer(
            organisation=sample.ours, name="[Flying Club Name]", kind=Kind.FLYING_CLUB
        )
        assert (club.description, club.owned_by) == ("Flying Club", "Flying Club")
        syndicate = services.add_customer(
            organisation=sample.ours, name="[Syndicate Name]", kind=Kind.SYNDICATE, members=6
        )
        assert syndicate.owned_by == "Syndicate of 6"
        unnumbered = services.add_customer(
            organisation=sample.ours, name="[Other Syndicate Name]", kind=Kind.SYNDICATE
        )
        assert unnumbered.owned_by == "Syndicate"


# Adding and changing a customer


def test_a_customer_is_added_and_changed_and_both_are_in_the_history(sample: Sample) -> None:
    """REQ-207, REQ-210. By Planning and Records or the Continuing Airworthiness Manager."""
    planner = signed_in(sample.planner)
    response = post(
        planner,
        "/customers/add/",
        name="  [Operator Name]  ",
        kind="Operator",
        customer_since="2026-11-02",
    )
    assert response.status_code == 302
    added = customer(sample, "[Operator Name]")
    assert response["Location"] == f"/customers/{added.id}/"
    assert (added.kind, added.members, added.customer_since) == (
        "Operator",
        None,
        date(2026, 11, 2),
    )
    body = page(planner, f"/customers/{added.id}/")
    assert "<h1>[Operator Name]</h1>\n<p>Operator</p>" in body
    assert "<dt>Customer Since</dt><dd>2 November 2026</dd>" in body
    changed = post(
        signed_in(sample.lucy),
        f"/customers/{added.id}/change/",
        name="[Operator Name]",
        kind="Syndicate",
        members="3",
        customer_since="2026-11-02",
    )
    assert changed.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        again = Customer.objects.get(pk=added.pk)
        entries = list(Event.of(again))
    assert again.owned_by == "Syndicate of 3"
    assert [(entry.action, entry.actor_name, entry.changed) for entry in entries] == [
        ("Created", "[Planning and Records Name]", []),
        ("Changed", "Lucy Grant", ["kind", "members"]),
    ]
    assert chain.problems(entries) == []


@pytest.mark.parametrize("role", ["administrator", "reviewer", "reader"])
def test_other_roles_see_customers_and_do_not_change_them(sample: Sample, role: str) -> None:
    """REQ-006. Refused on the server, and each refusal is in the access log."""
    with working_for(sample.ours.id, sample.lucy.id):
        one = services.add_customer(organisation=sample.ours, name="[Owner Name]")
    client = signed_in(getattr(sample, role))
    assert get(client, "/customers/").status_code == 200
    assert get(client, f"/customers/{one.id}/").status_code == 200
    assert get(client, "/customers/add/").status_code == 403
    assert post(client, "/customers/add/", name="[Another]").status_code == 403
    assert post(client, f"/customers/{one.id}/change/", name="[Another]").status_code == 403
    assert customer(sample, "[Owner Name]").name == "[Owner Name]"
    with as_owner():
        refused = AccessEntry.objects.filter(kind="Action Refused", detail="Add or Change Customer")
        assert refused.count() == 3


def test_what_cannot_be_true_of_a_customer_is_refused(sample: Sample) -> None:
    """REQ-207. Members are those of a syndicate; a customer has a name; the kind is known."""
    lucy = signed_in(sample.lucy)
    refused = post(lucy, "/customers/add/", name="[Owner Name]", kind="Pilot-Owner", members="2")
    assert refused.status_code == 200
    assert "Only a Syndicate Has Members" in refused.content.decode()
    assert "This field is required" in post(lucy, "/customers/add/", name=" ").content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        assert Customer.objects.count() == 0
        one = services.add_customer(organisation=sample.ours, name="[Owner Name]")
        for values, constraint in (
            ({"name": ""}, "customer_has_a_name_and_a_known_kind"),
            ({"kind": "Airline"}, "customer_has_a_name_and_a_known_kind"),
            ({"kind": "Pilot-Owner", "members": 2}, "customer_members_are_of_a_syndicate"),
            ({"kind": "Syndicate", "members": 0}, "customer_members_are_of_a_syndicate"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Customer.objects.filter(pk=one.pk).update(**values)


# The owner of an aircraft


def test_an_aircraft_is_added_for_a_customer_already_recorded_or_a_new_one(
    sample: Sample,
) -> None:
    """REQ-208. Chosen from the customers, or named: one of that name is used if there is one."""
    lucy = signed_in(sample.lucy)
    with working_for(sample.ours.id, sample.lucy.id):
        club = services.add_customer(
            organisation=sample.ours, name="[Flying Club Name]", kind=Kind.FLYING_CLUB
        )

    def add(registration: str, **owner: str) -> HttpResponse:
        return post(
            lucy,
            "/aircraft/add/",
            registration=registration,
            type_rating="[Type Rating]",
            regime="Part 21",
            **owner,
        )

    assert add("G-ONEA", customer=str(club.id)).status_code == 302
    assert add("G-TWOA", owner="[New Owner Name]").status_code == 302
    assert add("G-THRE", owner="[Flying Club Name]").status_code == 302
    assert aircraft_of(sample, "G-ONEA").customer == club
    assert aircraft_of(sample, "G-THRE").customer == club
    new = aircraft_of(sample, "G-TWOA").customer
    assert (new.name, new.kind) == ("[New Owner Name]", "")
    with working_for(sample.ours.id, sample.reader.id):
        assert Customer.objects.count() == 2
    # Neither, or both, is refused: an aircraft has one owner.
    neither = add("G-FOUR")
    both = add("G-FIVE", customer=str(club.id), owner="[Someone Else]")
    for response in (neither, both):
        assert response.status_code == 200
        assert "Choose a Customer or Name a New One" in response.content.decode()
    # A name two customers share does not say which is meant.
    with working_for(sample.ours.id, sample.lucy.id):
        services.add_customer(organisation=sample.ours, name="[New Owner Name]")
    unclear = add("G-SIXA", owner="[New Owner Name]")
    assert unclear.status_code == 200
    assert "More Than One Customer Is Named [New Owner Name]" in unclear.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert sorted(Aircraft.objects.values_list("registration", flat=True)) == [
            "G-ONEA",
            "G-THRE",
            "G-TWOA",
        ]


def test_the_owner_of_an_aircraft_is_changed_and_the_history_keeps_who_it_was(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-208. G-EJKL is sold to the flying club: the record before and after is kept."""
    club = customer(sample, "[Flying Club Name]")
    before = aircraft_of(sample, "G-EJKL").customer
    response = post(
        signed_in(sample.planner), f"/aircraft/{fleet['G-EJKL'].id}/owner/", customer=str(club.id)
    )
    assert response.status_code == 302
    after = aircraft_of(sample, "G-EJKL")
    assert (after.customer, after.owner) == (club, "Flying Club")
    with working_for(sample.ours.id, sample.reader.id):
        entry = Event.of(after).last()
    assert entry is not None
    assert (entry.changed, entry.actor_name) == (["customer_id"], "[Planning and Records Name]")
    assert entry.before_json is not None and str(before.id) in entry.before_json
    assert entry.after_json is not None and str(club.id) in entry.after_json
    listed = {row[0]: row[2] for row in rows(page(signed_in(sample.reader), "/customers/"))}
    assert listed["[Flying Club Name]"] == "G-DGHI, G-EJKL"
    assert listed["[Owner Name G-EJKL]"] == ""
    # Read Only may not, and the Administrator does not change aircraft records.
    for user in (sample.reader, sample.administrator):
        refused = post(
            signed_in(user), f"/aircraft/{fleet['G-ABCD'].id}/owner/", customer=str(club.id)
        )
        assert refused.status_code == 403
    assert aircraft_of(sample, "G-ABCD").customer.name == "[Owner Name G-ABCD]"


def test_an_aircraft_always_has_a_customer_of_its_own_organisation(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-002, REQ-208. The database refuses none, and one of another organisation."""
    with working_for(sample.other.id, sample.stranger.id):
        theirs = services.add_customer(organisation=sample.other, name="[Their Owner Name]")
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(IntegrityError, match="customer_id"), transaction.atomic():
            Aircraft.objects.filter(pk=fleet["G-ABCD"].pk).update(customer=None)
        with (
            pytest.raises(Exception, match="refers only to records of its own organisation"),
            transaction.atomic(),
        ):
            Aircraft.objects.filter(pk=fleet["G-ABCD"].pk).update(customer=theirs.pk)
    lucy = signed_in(sample.lucy)
    # Said on the page, with nothing changed (finding 14 of 24 November 2026).
    for chosen, reason in (
        (str(theirs.id), "Select a valid choice"),
        ("", "This field is required"),
        ("not-a-customer", "is not a valid"),
    ):
        refused = post(lucy, f"/aircraft/{fleet['G-ABCD'].id}/owner/", customer=chosen)
        assert refused.status_code == 200, chosen
        owner = refused.content.decode().split("<h2>Owner of G-ABCD</h2>", 1)[1]
        said = owner.split('<span role="alert">', 1)[1].split("</span>", 1)[0]
        assert reason in said, chosen
    assert aircraft_of(sample, "G-ABCD").customer.name == "[Owner Name G-ABCD]"
    added = post(
        lucy,
        "/aircraft/add/",
        registration="G-SEVN",
        type_rating="[Type Rating]",
        regime="Part 21",
        customer=str(theirs.id),
    )
    assert added.status_code == 200
    assert "Select a valid choice" in added.content.decode()


def test_another_organisations_customers_are_not_found_or_shown(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-003."""
    stranger = signed_in(sample.stranger)
    club = customer(sample, "[Flying Club Name]")
    assert get(stranger, f"/customers/{club.id}/").status_code == 404
    assert post(stranger, f"/customers/{club.id}/change/", name="X").status_code == 404
    body = page(stranger, "/customers/")
    assert "[Flying Club Name]" not in body
    assert "<p>0 Customers, 0 Aircraft</p>" in body
    assert "[Flying Club Name]" not in page(stranger, "/aircraft/add/")


def test_the_export_of_an_aircraft_holds_its_customer_and_no_other(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134, REQ-208. The owner is part of the aircraft's record."""
    with working_for(sample.ours.id, sample.lucy.id):
        export = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-BXYZ"])
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        customers = json.loads(archive.read("records/customers_customer.json"))
    assert [(one["name"], one["kind"], one["members"]) for one in customers] == [
        ("[Syndicate Name G-BXYZ]", "Syndicate", 6)
    ]


def test_the_export_of_an_aircraft_holds_every_customer_that_has_owned_it(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134, REQ-208; independent review of 24 November 2026, finding 12. G-EJKL is
    sold to the flying club and then to the syndicate of G-BXYZ. Its history names
    each earlier owner by an identifier alone: the export holds all three customers,
    so the names can be read, and no customer that never owned it."""
    club = customer(sample, "[Flying Club Name]")
    syndicate = customer(sample, "[Syndicate Name G-BXYZ]")
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft_services.change_owner(Aircraft.objects.get(pk=fleet["G-EJKL"].pk), club)
        aircraft_services.change_owner(Aircraft.objects.get(pk=fleet["G-EJKL"].pk), syndicate)
        ejkl = Aircraft.objects.get(pk=fleet["G-EJKL"].pk)
        export = build_export(sample.ours, by=sample.lucy, aircraft=ejkl)
    with zipfile.ZipFile(io.BytesIO(export.content)) as archive:
        customers = json.loads(archive.read("records/customers_customer.json"))
        history = json.loads(archive.read("history/aircraft_aircraft.json"))
    assert sorted(one["name"] for one in customers) == [
        "[Flying Club Name]",
        "[Owner Name G-EJKL]",
        "[Syndicate Name G-BXYZ]",
    ]
    # Every customer the aircraft's history names can be read in the export.
    named = {one["id"] for one in customers}
    owners = set()
    for entry in history:
        owners.add(json.loads(entry["after"])["customer_id"])
    assert owners == named and len(owners) == 3


# Aircraft from before customers were records


def test_what_was_typed_as_owned_by_becomes_the_customers_name(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-209. The migration's own statements, run on aircraft as they were before.

    The aircraft are put back as they were: a column of free text, and no
    customer. One customer is made for each different text in an
    organisation, named exactly as it was typed, and each aircraft is given
    the customer of its text. Nothing else of the aircraft changes.
    """
    typed = {
        "G-DGHI": "Flying Club",
        "G-EJKL": "Pilot-Owner",
        "G-ABCD": "Pilot-Owner",
        "G-BXYZ": "Syndicate of 6",
        "G-FMNO": "Pilot-Owner",
        "G-CDEF": "Syndicate of 4",
        "G-HKLM": "[Owner Name]",
    }
    ours = str(sample.ours.id)
    with working_for(sample.other.id, sample.stranger.id):
        aircraft_services.add_aircraft(
            organisation=sample.other, registration="G-OTHR", type_rating="[Type]", owner="X"
        )
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        cursor.execute("SELECT count(*) FROM customers_customer WHERE organisation_id = %s", [ours])
        (before,) = cursor.fetchone()
        cursor.execute("ALTER TABLE aircraft_aircraft ADD COLUMN owner varchar(200)")
        cursor.execute("ALTER TABLE aircraft_aircraft ALTER COLUMN customer_id DROP NOT NULL")
        cursor.execute("ALTER TABLE aircraft_aircraft DISABLE TRIGGER history_write")
        for registration, text in (*typed.items(), ("G-OTHR", "Pilot-Owner")):
            organisation = str(sample.other.id) if registration == "G-OTHR" else ours
            cursor.execute(
                "SELECT set_config('airworthiness.organisation', %s, true)", [organisation]
            )
            cursor.execute(
                "UPDATE aircraft_aircraft SET owner = %s, customer_id = NULL "
                "WHERE registration = %s AND organisation_id = %s",
                [text, registration, organisation],
            )
            assert cursor.rowcount == 1
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("SET CONSTRAINTS ALL DEFERRED")
        cursor.execute("ALTER TABLE aircraft_aircraft ENABLE TRIGGER history_write")
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")

        # The migration, in its order (aircraft 0003).
        cursor.execute(aircraft_sql.OWNERS_TO_CUSTOMERS_BEGIN)
        cursor.execute(for_each_organisation(aircraft_sql.CUSTOMER_FOR_EACH_OWNER))
        cursor.execute("ALTER TABLE aircraft_aircraft DROP COLUMN owner")
        cursor.execute(for_each_organisation(aircraft_sql.AIRCRAFT_TAKE_THEIR_CUSTOMER))
        cursor.execute(aircraft_sql.OWNERS_TO_CUSTOMERS_END)
        cursor.execute("ALTER TABLE aircraft_aircraft ALTER COLUMN customer_id SET NOT NULL")

        cursor.execute(
            "SELECT a.registration, c.name, c.kind FROM aircraft_aircraft a "
            "JOIN customers_customer c ON c.id = a.customer_id AND c.organisation_id = %s "
            "WHERE a.organisation_id = %s",
            [ours, ours],
        )
        assert {row[0]: row[1] for row in cursor.fetchall()} == typed
        cursor.execute(
            "SELECT count(*), count(DISTINCT name) FROM customers_customer "
            "WHERE organisation_id = %s AND id IN (SELECT customer_id FROM aircraft_aircraft)",
            [ours],
        )
        # Five different texts for seven aircraft: five customers, beside those there before.
        assert cursor.fetchone() == (5, 5)
        cursor.execute("SELECT count(*) FROM customers_customer WHERE organisation_id = %s", [ours])
        assert cursor.fetchone() == (before + 5,)
        # The other organisation's Pilot-Owner is its own customer, not ours.
        cursor.execute(
            "SELECT c.name, c.organisation_id::text FROM aircraft_aircraft a "
            "JOIN customers_customer c ON c.id = a.customer_id WHERE a.registration = 'G-OTHR'"
        )
        assert cursor.fetchall() == [("Pilot-Owner", str(sample.other.id))]
        # Each aircraft's history says the customer was given, by the database role.
        cursor.execute(
            "SELECT e.changed, e.actor_name LIKE 'Database Role %%', e.after_json LIKE '%%owner%%' "
            "FROM history_event e JOIN aircraft_aircraft a ON a.id = e.record_id "
            "WHERE a.registration = 'G-ABCD' AND e.organisation_id = %s "
            "ORDER BY e.sequence DESC LIMIT 1",
            [ours],
        )
        assert cursor.fetchall() == [(["customer_id"], True, False)]
        cursor.execute("SELECT count(*) FROM pg_class WHERE relname LIKE 'aircraft_%%_migration'")
        assert cursor.fetchone() == (0,)
        cursor.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'organisations_organisation'"
        )
        assert cursor.fetchone() == (True,)
    with working_for(sample.ours.id, sample.reader.id):
        assert chain.problems(list(Event.objects.all())) == []
        abcd = Aircraft.objects.select_related("customer").get(registration="G-ABCD")
        ejkl = Aircraft.objects.get(registration="G-EJKL")
        assert abcd.customer_id == ejkl.customer_id
        assert abcd.owner == "Pilot-Owner"


def put_back_as_typed(cursor: Any, typed: dict[str, str | None], organisation: str) -> None:
    """Put the aircraft back as they were before customers: a column of text, no customer."""
    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    cursor.execute("ALTER TABLE aircraft_aircraft ADD COLUMN owner varchar(200)")
    cursor.execute("ALTER TABLE aircraft_aircraft ALTER COLUMN customer_id DROP NOT NULL")
    cursor.execute("ALTER TABLE aircraft_aircraft DISABLE TRIGGER history_write")
    cursor.execute("SELECT set_config('airworthiness.organisation', %s, true)", [organisation])
    for registration, text in typed.items():
        cursor.execute(
            "UPDATE aircraft_aircraft SET owner = %s, customer_id = NULL "
            "WHERE registration = %s AND organisation_id = %s",
            [text, registration, organisation],
        )
        assert cursor.rowcount == 1
    cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
    cursor.execute("SET CONSTRAINTS ALL DEFERRED")
    cursor.execute("ALTER TABLE aircraft_aircraft ENABLE TRIGGER history_write")
    cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")


def run_the_migration(cursor: Any) -> None:
    """The statements of aircraft 0003, in its order."""
    cursor.execute(aircraft_sql.OWNERS_TO_CUSTOMERS_BEGIN)
    cursor.execute(for_each_organisation(aircraft_sql.CUSTOMER_FOR_EACH_OWNER))
    cursor.execute("ALTER TABLE aircraft_aircraft DROP COLUMN owner")
    cursor.execute(for_each_organisation(aircraft_sql.AIRCRAFT_TAKE_THEIR_CUSTOMER))
    cursor.execute(aircraft_sql.OWNERS_TO_CUSTOMERS_END)
    cursor.execute("ALTER TABLE aircraft_aircraft ALTER COLUMN customer_id SET NOT NULL")


# Texts that differ only in the spaces around them, one with none, and one not typed at all.
UNTIDY: dict[str, str | None] = {
    "G-DGHI": "Flying Club",
    "G-EJKL": " Pilot-Owner",
    "G-ABCD": "Pilot-Owner  ",
    "G-BXYZ": "Pilot-Owner",
    "G-FMNO": "   ",
    "G-CDEF": "",
    "G-HKLM": None,
}


def owners_after(sample: Sample) -> dict[str, tuple[str, object]]:
    with working_for(sample.ours.id, sample.reader.id):
        return {
            one.registration: (one.customer.name, one.customer_id)
            for one in Aircraft.objects.select_related("customer")
        }


def test_owner_text_is_trimmed_before_customers_are_made(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-209; independent review of 24 November 2026, finding 13. Texts that differ
    only in the spaces around them made two customers of one name. They now make
    one. An aircraft with no text, or only spaces, is given the one customer
    named Not Recorded."""
    with working_for(sample.ours.id, sample.reader.id):
        before = Customer.objects.count()
    with as_owner(), connection.cursor() as cursor:
        put_back_as_typed(cursor, UNTIDY, str(sample.ours.id))
        run_the_migration(cursor)
    after = owners_after(sample)
    assert {registration: name for registration, (name, _) in after.items()} == {
        "G-DGHI": "Flying Club",
        "G-EJKL": "Pilot-Owner",
        "G-ABCD": "Pilot-Owner",
        "G-BXYZ": "Pilot-Owner",
        "G-FMNO": "Not Recorded",
        "G-CDEF": "Not Recorded",
        "G-HKLM": "Not Recorded",
    }
    # One customer for each different text: 3 for the 7 aircraft.
    assert len({customer for _, customer in after.values()}) == 3
    assert after["G-EJKL"][1] == after["G-ABCD"][1] == after["G-BXYZ"][1]
    with working_for(sample.ours.id, sample.reader.id):
        assert Customer.objects.filter(name="Pilot-Owner").count() == 1
        assert Customer.objects.filter(name="Not Recorded").count() == 1
        # No customer is made that no aircraft is given, and no name keeps its spaces.
        assert Customer.objects.count() == before + 3
        assert all(name == name.strip() for name in Customer.objects.values_list("name", flat=True))
        assert chain.problems(list(Event.objects.all())) == []


def test_the_migration_runs_as_an_owner_of_the_tables_who_is_not_a_superuser(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """Aircraft 0003 as the server runs it: by an owner of the tables with no other
    power, whom row-level security holds as it holds the application (ADR-0002).
    Every other test of it runs as a superuser, whom it never holds."""
    with as_owner(), connection.cursor() as cursor:
        put_back_as_typed(cursor, UNTIDY, str(sample.ours.id))
    with as_owner_who_is_not_a_superuser(), connection.cursor() as cursor:
        cursor.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user")
        assert cursor.fetchone() == (False,)
        cursor.execute("SELECT count(*) FROM aircraft_aircraft")
        assert cursor.fetchone() == (0,)  # held by row-level security
        run_the_migration(cursor)
        cursor.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'organisations_organisation'"
        )
        assert cursor.fetchone() == (True,)
    after = owners_after(sample)
    assert len({customer for _, customer in after.values()}) == 3
    assert after["G-ABCD"][0] == "Pilot-Owner" and after["G-HKLM"][0] == "Not Recorded"
    with working_for(sample.ours.id, sample.reader.id):
        entry = Event.of(Aircraft.objects.get(registration="G-ABCD")).last()
        assert entry is not None
        assert entry.changed == ["customer_id"]
        assert entry.actor_name.startswith("Database Role ")
        assert chain.problems(list(Event.objects.all())) == []


def test_the_migration_says_plainly_that_it_cannot_be_reversed() -> None:
    """Finding 13. Going back failed part way, on the column of text that is no longer
    there. Django now refuses the whole migration before it changes anything, and
    the refusal says why."""
    migration = MigrationLoader(None).get_migration("aircraft", "0003_owned_by_a_customer")
    assert not migration.operations[0].reversible
    with pytest.raises(IrreversibleError, match="cannot be put back"):
        # Refused when the operations are first read: nothing is asked of the database.
        migration.unapply(ProjectState(), None)  # type: ignore[arg-type]


def test_a_customer_named_twice_at_once_is_made_once(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-208; independent review of 24 November 2026, finding 14. Naming a new owner
    read and then wrote with no lock, so the same form sent twice at once made
    two customers of one name. The work now takes the organisation's row before
    it looks, so the second waits for the first and is given its customer."""
    with working_for(sample.ours.id, sample.lucy.id):
        with CaptureQueriesContext(connection) as sent:
            made = services.named(sample.ours, "[New Owner Name]")
        statements = [query["sql"] for query in sent.captured_queries]
        lock = next(
            index
            for index, statement in enumerate(statements)
            if "FOR UPDATE" in statement and "organisations_organisation" in statement
        )
        look = next(
            index for index, statement in enumerate(statements) if "customers_customer" in statement
        )
        assert lock < look
        assert services.named(sample.ours, " [New Owner Name] ") == made
        assert Customer.objects.filter(name="[New Owner Name]").count() == 1


def test_the_sample_names_a_customer_for_every_aircraft() -> None:
    """REQ-207. SampleData.md: 7 customers, one for each aircraft, each named apart."""
    assert set(build.CUSTOMERS) == {registration for registration, *_ in FLEET} | {"G-HKLM"}
    names = [name for name, *_ in build.CUSTOMERS.values()]
    assert len(set(names)) == len(names) == 7


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_the_customer_pages_offer_only_what_the_role_may_do(sample: Sample, role: str) -> None:
    """REQ-006; independent review of 24 November 2026, finding 8. Add a Customer and the
    form that changes a record are shown to the roles that may use them, and to
    nobody the server would refuse. The check on the server stays the control."""
    user = getattr(sample, role)
    client = signed_in(user)
    with working_for(sample.ours.id, sample.lucy.id):
        customer = services.add_customer(organisation=sample.ours, name="[Owner Name G-ABCD]")
    may = user.may(Action.ADD_OR_CHANGE_CUSTOMER)
    assert may == (role in ("lucy", "planner"))
    listed = client.get("/customers/", secure=True).content.decode().split("<main", 1)[1]
    one = client.get(f"/customers/{customer.id}/", secure=True).content.decode()
    one = one.split("<main", 1)[1]
    assert ('href="/customers/add/"' in listed) == may
    assert ("<form" in one) == may
    assert "<dt>Customer</dt><dd>[Owner Name G-ABCD]</dd>" in one
    refused = client.post(
        f"/customers/{customer.id}/change/", {"name": "[Another Name]"}, secure=True
    )
    assert refused.status_code == (302 if may else 403)
