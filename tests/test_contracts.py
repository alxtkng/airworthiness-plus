"""Contracts with owners and the work orders placed under them (REQ-240 to REQ-249).

The Contracts board, with the sample of design-system/SampleData.md. Today
in the sample is 18 November 2026. Appendix I to Part-ML was read in the
UK text on 27 November 2026 (Decisions.md, Regulation Facts in Use).

By hand: a contract that became null on 4 November 2026 has the owner tell
the Civil Aviation Authority within 2 weeks, counted as 14 days: by
18 November 2026.
"""

from datetime import date
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts import services
from airworthiness_plus.contracts.models import Contract, EndReason, OrderedBy, Scope, WorkOrder
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import build, phase1
from airworthiness_rules import contracts as rules
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, make_sample, signed_in
from tests.test_defects import Day, get, page, post, tables

pytestmark = pytest.mark.django_db


@pytest.fixture
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    chosen = Day()
    monkeypatch.setattr(aircraft_services, "today", lambda: chosen.today)
    return chosen


@pytest.fixture
def sample(day: Day) -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = build.add_fleet(sample)
    build.add_other_work(sample, fleet)
    return fleet


@pytest.fixture
def contracts(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Contract]:
    added = phase1.add_contracts(sample.ours, sample.lucy, fleet)
    return {contract.registration: contract for contract in added}


def draw_up(sample: Sample, aircraft: Aircraft, **values: Any) -> Contract:
    given: dict[str, Any] = {
        "scope": Scope.ALL,
        "type_of_operation": "[Type of Operation]",
        "owner_address": "[Owner Address]",
        "signed_on": date(2026, 11, 2),
    }
    given.update(values)
    with working_for(sample.ours.id, sample.lucy.id):
        return services.draw_up_contract(aircraft, **given)


FORM = {
    "scope": "All Continuing Airworthiness Management Tasks",
    "type_of_operation": "[Type of Operation]",
    "owner_address": "[Owner Address]",
    "signed_on": "2026-11-02",
}

# The rule


def test_the_owner_tells_the_authority_within_2_weeks() -> None:
    """REQ-243, Appendix I to Part-ML. Golden: 4 November 2026 and 14 days is 18 November."""
    assert rules.owner_notice_deadline(date(2026, 11, 4)) == date(2026, 11, 18)
    # Across the end of a month and of a year, and a leap day.
    assert rules.owner_notice_deadline(date(2026, 12, 25)) == date(2027, 1, 8)
    assert rules.owner_notice_deadline(date(2028, 2, 20)) == date(2028, 3, 5)


def test_when_a_contract_is_in_force() -> None:
    """REQ-244. From the day signed up to and including the day it ended."""
    signed, ended = date(2026, 3, 2), date(2026, 11, 4)
    assert not rules.in_force(signed, None, date(2026, 3, 1))
    assert rules.in_force(signed, None, signed)
    assert rules.in_force(signed, None, date(2030, 1, 1))
    assert rules.in_force(signed, ended, ended)
    assert not rules.in_force(signed, ended, date(2026, 11, 5))
    with pytest.raises(ValueError, match="does not end before"):
        rules.in_force(signed, date(2026, 3, 1), signed)


@given(
    ended=st.dates(min_value=date(2000, 1, 1), max_value=date(2100, 1, 1)),
    length=st.integers(0, 4000),
    offset=st.integers(-50, 4100),
)
def test_the_deadline_and_the_period_in_force_hold_for_any_day(
    ended: date, length: int, offset: int
) -> None:
    """REQ-243, REQ-244. Property: the deadline is exactly 14 days on, the same day of
    the week; a contract is in force on exactly the days from signing to ending."""
    deadline = rules.owner_notice_deadline(ended)
    assert (deadline - ended).days == 14 and deadline.weekday() == ended.weekday()
    signed = date.fromordinal(ended.toordinal() - length)
    day = date.fromordinal(signed.toordinal() + offset)
    assert rules.in_force(signed, ended, day) == (0 <= offset <= length)
    assert rules.in_force(signed, None, day) == (offset >= 0)


# The sample

CONTRACTS = [
    ["G-BXYZ", "[Syndicate Name G-BXYZ]", "All Continuing Airworthiness Management Tasks",
     "15 January 2025", "Active", ""],
    ["G-CDEF", "[Syndicate Name G-CDEF]", "All Continuing Airworthiness Management Tasks",
     "8 April 2024", "Active", ""],
    ["G-DGHI", "[Flying Club Name]", "All Continuing Airworthiness Management Tasks",
     "4 March 2025", "Active", ""],
    ["G-HKLM", "[Owner Name G-HKLM]", "All Continuing Airworthiness Management Tasks",
     "9 November 2026", "Records Transfer", "14 of 18 Received"],
    ["G-ABCD", "[Owner Name G-ABCD]", "Maintenance Programme Review and Airworthiness Review",
     "2 March 2026", "Active", ""],
]  # fmt: skip

ORDERS = [
    ["G-ABCD", "Landing Light Replacement", "[Owner Name G-ABCD]", "12 November 2026", "Open",
     "Signed 2 March 2026"],
    ["G-DGHI", "Stabilator Trim Cable Rectification", "Continuing Airworthiness Manager",
     "14 November 2026", "Open", "Signed 4 March 2025"],
    ["G-FMNO", "50-Hour Check", "[Owner Name G-FMNO]", "16 November 2026", "Open",
     "No Contract, Work Order Only"],
]  # fmt: skip


def test_the_contracts_page_of_the_sample(sample: Sample, contracts: dict[str, Contract]) -> None:
    """REQ-240, REQ-244, REQ-246. Golden, from the Contracts board: five contracts,
    those for every task first, and three work orders in the order they were agreed."""
    body = page(signed_in(sample.reader), "/contracts/")
    listed, orders = tables(body)
    assert [row[:6] for row in listed] == CONTRACTS
    assert [row[:6] for row in orders] == ORDERS
    assert "<li>Continuing Airworthiness</li>" in body
    assert '<li><a href="/contracts/" aria-current="location">Contracts</a></li>' in body
    assert "Within 2 Weeks if a Contract Ends Through Non-Conformity</p>" in body
    one = page(signed_in(sample.reader), f"/contracts/{contracts['G-DGHI'].id}/")
    for said in (
        "<h1>Contract, G-DGHI</h1>",
        "<dt>Type Rating</dt><dd>Piper PA-28 Series (Lycoming)</dd>",
        "<dt>Owner</dt><dd>[Flying Club Name]</dd>",
        "<dt>Owner&#8217;s Address</dt><dd>[Owner Address G-DGHI]</dd>",
        "<dt>Organisation</dt><dd>[Your Organisation]</dd>",
        "<dt>Organisation&#8217;s Address</dt><dd>[Organisation Address]</dd>",
        "<dt>Approval Reference</dt><dd>UK.CAO.[Number]</dd>",
        "<dt>Type of Operation</dt><dd>[Type of Operation]</dd>",
        "<dt>Status</dt><dd>Active</dd>",
        "<td>Stabilator Trim Cable Rectification</td>",
    ):
        assert said in one, said
    # The customer's page lists the contract.
    with working_for(sample.ours.id, sample.reader.id):
        club = Customer.objects.get(name="[Flying Club Name]")
    assert f'<a href="/contracts/{contracts["G-DGHI"].id}/">G-DGHI</a>' in page(
        signed_in(sample.reader), f"/customers/{club.id}/"
    )


# Drawing up a contract


def test_a_contract_is_drawn_up_on_the_page_and_is_in_the_history(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-240. By the Continuing Airworthiness Manager, for the aircraft's owner."""
    lucy = signed_in(sample.lucy)
    response = post(lucy, "/contracts/draw-up/", aircraft=str(fleet["G-EJKL"].id), **FORM)
    assert response.status_code == 302, response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        contract = Contract.objects.get()
        entries = list(Event.of(contract))
    assert response["Location"] == f"/contracts/{contract.id}/"
    assert (contract.owner_name, contract.registration, contract.customer_id) == (
        "[Owner Name G-EJKL]",
        "G-EJKL",
        fleet["G-EJKL"].customer_id,
    )
    assert [(entry.action, entry.actor_name) for entry in entries] == [("Created", "Lucy Grant")]
    assert chain.problems(entries) == []


@pytest.mark.parametrize(
    ("values", "reason"),
    [
        ({"scope": "Limited Tasks"}, "Limited Tasks Names Them"),
        ({"tasks": "[Tasks]"}, "Named Only for a Contract Limited to Them"),
        ({"scope": "[Anything]"}, "Select a valid choice"),
        ({"type_of_operation": " "}, "This field is required"),
        ({"owner_address": " "}, "This field is required"),
        ({"signed_on": "2026-11-19"}, "Not Signed After Today"),
    ],
)
def test_what_cannot_be_true_of_a_contract_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], values: dict[str, str], reason: str
) -> None:
    """REQ-240, Appendix I to Part-ML: the type of operation and the owner's address
    are stated; the tasks are every task, or limited tasks that are named."""
    lucy = signed_in(sample.lucy)
    response = post(
        lucy, "/contracts/draw-up/", aircraft=str(fleet["G-EJKL"].id), **{**FORM, **values}
    )
    assert response.status_code == 200
    assert reason in response.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert Contract.objects.count() == 0


def test_an_aircraft_has_one_contract_in_force(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-240. A second is refused, by the service under a lock on the aircraft and
    by the database; once the first has ended another may be signed, not before it ended."""
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.lucy.id), CaptureQueriesContext(connection) as sent:
        first = draw_up(sample, ejkl)
    statements = [query["sql"] for query in sent.captured_queries]
    lock = next(
        index
        for index, statement in enumerate(statements)
        if "FOR UPDATE" in statement and "aircraft_aircraft" in statement
    )
    look = next(i for i, statement in enumerate(statements) if "contracts_contract" in statement)
    assert lock < look
    again = post(signed_in(sample.lucy), "/contracts/draw-up/", aircraft=str(ejkl.id), **FORM)
    assert "This Aircraft Already Has a Contract in Force" in again.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        with (
            pytest.raises(IntegrityError, match="contract_one_in_force_for_each_aircraft"),
            transaction.atomic(),
        ):
            Contract.objects.create(
                organisation=sample.ours,
                aircraft=ejkl,
                customer_id=ejkl.customer_id,
                scope=Scope.ALL,
                type_of_operation="[Operation]",
                owner_address="[Address]",
                signed_on=TODAY,
            )
        services.end_contract(first, ended_on=date(2026, 11, 10), end_reason=EndReason.OTHER)
        with pytest.raises(services.RefusedError, match="Before the Last One Ended"):
            services.draw_up_contract(
                ejkl,
                scope=Scope.ALL,
                type_of_operation="[Operation]",
                owner_address="[Address]",
                signed_on=date(2026, 11, 9),
            )
    second = draw_up(sample, ejkl, signed_on=date(2026, 11, 10))
    assert second.pk != first.pk


def test_a_contract_keeps_what_it_said_when_it_was_recorded(
    sample: Sample, contracts: dict[str, Contract], fleet: dict[str, Aircraft]
) -> None:
    """REQ-241. The owner is renamed, the aircraft is sold and re-registered details
    change, the organisation moves: the contract still says what it said. The database
    wrote those values, whatever was sent, and refuses any change to them."""
    contract = contracts["G-DGHI"]
    with working_for(sample.ours.id, sample.lucy.id):
        club = Customer.objects.get(name="[Flying Club Name]")
        customer_services.change_customer(
            club, name="[Renamed Club]", kind=club.kind, members=None, customer_since=None
        )
        other = Customer.objects.get(name="[Owner Name G-EJKL]")
        aircraft_services.change_owner(Aircraft.objects.get(pk=fleet["G-DGHI"].pk), other)
        aircraft_services.record_details(
            Aircraft.objects.get(pk=fleet["G-DGHI"].pk),
            serial_number="[New Serial]",
            manufacturer="",
            designation="",
        )
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.change_details(
            Organisation.objects.get(pk=sample.ours.pk), name="[New Name]", address="[New Address]"
        )
    body = page(signed_in(sample.reader), f"/contracts/{contract.id}/")
    assert "<dt>Owner</dt><dd>[Flying Club Name]</dd>" in body
    assert "<dt>Organisation</dt><dd>[Your Organisation]</dd>" in body
    for later in ("[Renamed Club]", "[New Name]", "[New Address]", "[New Serial]", "G-EJKL"):
        assert later not in body.split("<main", 1)[1], later
    with working_for(sample.ours.id, sample.lucy.id):
        ejkl = Aircraft.objects.get(pk=fleet["G-EJKL"].pk)
        made = Contract.objects.create(
            organisation=sample.ours,
            aircraft=ejkl,
            customer_id=ejkl.customer_id,
            scope=Scope.ALL,
            type_of_operation="[Operation]",
            owner_address="[Address]",
            signed_on=TODAY,
            registration="G-FAKE",
            owner_name="[Somebody Else]",
            organisation_name="[Another Organisation]",
            organisation_approval_reference="UK.CAO.[Other]",
        )
        made.refresh_from_db()
        assert (
            made.registration,
            made.owner_name,
            made.organisation_name,
            made.organisation_approval_reference,
        ) == ("G-EJKL", "[Owner Name G-EJKL]", "[New Name]", "UK.CAO.[Number]")
        for change in (
            {"owner_name": "[Altered]"},
            {"registration": "G-ALTR"},
            {"type_rating": "[Altered]"},
            {"serial_number": "[Altered]"},
            {"organisation_name": "[Altered]"},
            {"organisation_address": "[Altered]"},
            {"organisation_approval_reference": "[Altered]"},
            {"owner_address": "[Altered]"},
            {"type_of_operation": "[Altered]"},
            {"signed_on": date(2020, 1, 1)},
            {"scope": Scope.LIMITED, "tasks": "[Altered]"},
            {"customer": other},
            {"aircraft": ejkl},
        ):
            with (
                pytest.raises(IntegrityError, match="contract says is never altered"),
                transaction.atomic(),
            ):
                Contract.objects.filter(pk=contract.pk).update(**change)


# Ending a contract


def test_a_contract_that_ends_through_non_conformity(
    sample: Sample, contracts: dict[str, Contract], day: Day
) -> None:
    """REQ-242, REQ-243, REQ-247, Appendix I to Part-ML. Ended on 4 November 2026: the
    owner tells the Civil Aviation Authority by 18 November, and the page says how
    that was worked out. The organisation tells it too; until that day is recorded
    the contract is on the Dashboard. Each is recorded once."""
    lucy = signed_in(sample.lucy)
    contract = contracts["G-BXYZ"]
    path = f"/contracts/{contract.id}/"
    ended = post(
        lucy, path + "end/", ended_on="2026-11-04", end_reason="Non-Conformity With the Contract"
    )
    assert ended.status_code == 302
    body = page(lucy, path)
    assert (
        "<dt>Status</dt><dd>Ended, Non-Conformity With the Contract, 4 November 2026</dd>" in body
    )
    assert "<dt>Owner Tells the Civil Aviation Authority By</dt><dd>18 November 2026</dd>" in body
    assert "<dd>Within 2 Weeks of the Termination of the Contract, Counted as 14 Days</dd>" in body
    assert f"<dd>{dot('To Assess')}</dd>" in body

    def on_dashboard() -> list[list[str]]:
        with working_for(sample.ours.id, sample.reader.id):
            panel = dashboard_services.continuing_airworthiness(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [
            [row.subject, row.item, row.detail, row.due, row.status]
            for row in panel.rows
            if row.page == "Contracts"
        ]

    assert on_dashboard() == [
        [
            "G-BXYZ",
            "Contract Ended, Civil Aviation Authority to Be Told",
            "Non-Conformity With the Contract, 4 November 2026, Appendix I to Part-ML",
            "Not Set",
            "To Assess",
        ]
    ]
    again = post(lucy, path + "end/", ended_on="2026-11-05", end_reason="Other")
    assert "This Contract Has Already Ended" in again.content.decode()
    for told, reason in (
        ("2026-11-03", "Not Told Before the Contract Ended"),
        ("2026-11-19", "Not Told After Today"),
    ):
        refused = post(lucy, path + "authority-told/", told_on=told)
        assert refused.status_code == 200 and reason in refused.content.decode()
    assert post(lucy, path + "authority-told/", told_on="2026-11-06").status_code == 302
    twice = post(lucy, path + "authority-told/", told_on="2026-11-07")
    assert "Is Already Recorded" in twice.content.decode()
    assert on_dashboard() == []
    body = page(lucy, path)
    assert (
        "<dt>Civil Aviation Authority Told by the Organisation</dt><dd>6 November 2026</dd>" in body
    )
    assert "<form" not in body.split("<main", 1)[1]
    with working_for(sample.ours.id, sample.lucy.id):
        kept = Contract.objects.get(pk=contract.pk)
        assert (kept.ended_on, kept.authority_told_on) == (date(2026, 11, 4), date(2026, 11, 6))
        for change in (
            {"ended_on": date(2026, 11, 5)},
            {"end_reason": EndReason.OTHER},
            {"authority_told_on": date(2026, 11, 7)},
            {"ended_on": None, "end_reason": "", "authority_told_on": None},
        ):
            with pytest.raises(IntegrityError, match="recorded once"), transaction.atomic():
                Contract.objects.filter(pk=contract.pk).update(**change)
        assert [entry.changed for entry in Event.of(kept)] == [
            [],
            ["end_reason", "ended_on"],
            ["authority_told_on"],
        ]


def test_what_cannot_be_true_of_an_ending_is_refused(
    sample: Sample, contracts: dict[str, Contract]
) -> None:
    """REQ-242. Not after today, not before it was signed, with a reason; a contract
    that ended for another reason has nothing to tell and no day for the owner."""
    lucy = signed_in(sample.lucy)
    contract = contracts["G-ABCD"]  # signed 2 March 2026
    path = f"/contracts/{contract.id}/"
    for values, reason in (
        ({"ended_on": "2026-11-19", "end_reason": "Other"}, "Does Not End After Today"),
        ({"ended_on": "2026-03-01", "end_reason": "Other"}, "Does Not End Before It Was Signed"),
        ({"ended_on": "2026-11-04", "end_reason": "[Anything]"}, "Select a valid choice"),
        ({"ended_on": "2026-11-04"}, "This field is required"),
    ):
        refused = post(lucy, path + "end/", **values)
        assert refused.status_code == 200 and reason in refused.content.decode(), values
    not_ended = post(lucy, path + "authority-told/", told_on="2026-11-06")
    assert "This Contract Has Not Ended" in not_ended.content.decode()
    assert post(lucy, path + "end/", ended_on="2026-11-04", end_reason="Other").status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        line = services.ContractLine(Contract.objects.get(pk=contract.pk))
        assert (line.status, line.to_tell, line.owner_deadline, line.working) == (
            "Ended",
            False,
            None,
            None,
        )
    # The database holds the same, whatever the application sends.
    with working_for(sample.ours.id, sample.lucy.id):
        ejkl = Aircraft.objects.get(registration="G-EJKL")
        good: dict[str, Any] = {
            "organisation": sample.ours,
            "aircraft": ejkl,
            "customer_id": ejkl.customer_id,
            "scope": Scope.ALL,
            "type_of_operation": "[Operation]",
            "owner_address": "[Address]",
            "signed_on": date(2026, 11, 2),
        }
        for constraint, change in (
            ("contract_ended_has_a_reason", {"end_reason": "Other"}),
            ("contract_ended_has_a_reason", {"ended_on": TODAY}),
            ("contract_ended_has_a_reason", {"ended_on": TODAY, "end_reason": "[Any]"}),
            ("contract_ended_has_a_reason", {"authority_told_on": TODAY}),
            ("contract_ended_has_a_reason", {"ended_on": date(2026, 11, 1), "end_reason": "Other"}),
            (
                "contract_ended_has_a_reason",
                {"ended_on": TODAY, "end_reason": "Other", "authority_told_on": date(2026, 11, 17)},
            ),
            ("contract_says_its_tasks", {"type_of_operation": ""}),
            ("contract_says_its_tasks", {"owner_address": ""}),
            ("contract_says_its_tasks", {"scope": Scope.LIMITED}),
            ("contract_says_its_tasks", {"tasks": "[Tasks]"}),
            ("contract_says_its_tasks", {"scope": "[Any]"}),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Contract.objects.create(**{**good, **change})
        assert Contract.objects.filter(aircraft=ejkl).count() == 0


# Work orders


def test_a_work_order_sits_under_the_contract_in_force_when_it_was_agreed(
    sample: Sample, contracts: dict[str, Contract], fleet: dict[str, Aircraft]
) -> None:
    """REQ-244. G-ABCD's contract was signed on 2 March 2026: an order agreed on
    1 March has no contract, one agreed on 2 March has. It keeps the owner's name."""
    planner = signed_in(sample.planner)
    abcd = str(fleet["G-ABCD"].id)
    for agreed in ("2026-03-01", "2026-03-02"):
        added = post(
            planner,
            "/contracts/work-orders/add/",
            aircraft=abcd,
            work="[Work]",
            ordered_by="Owner",
            agreed_on=agreed,
        )
        assert added.status_code == 302, added.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        before, after = WorkOrder.objects.filter(work="[Work]").order_by("agreed_on")
        assert (before.contract, after.contract) == (None, contracts["G-ABCD"])
        assert after.owner_name == "[Owner Name G-ABCD]"
        owner = Customer.objects.get(name="[Owner Name G-ABCD]")
        customer_services.change_customer(
            owner, name="[Renamed Owner]", kind=owner.kind, members=None, customer_since=None
        )
        after.refresh_from_db()
        assert after.ordered_by_text == "[Owner Name G-ABCD]"
        for change in (
            {"owner_name": "[Altered]"},
            {"work": "[Altered]"},
            {"agreed_on": TODAY},
            {"ordered_by": OrderedBy.MANAGER},
            {"contract": None},
        ):
            with (
                pytest.raises(IntegrityError, match="work order says is never altered"),
                transaction.atomic(),
            ):
                WorkOrder.objects.filter(pk=after.pk).update(**change)
    # The same order sent twice is recorded once; one agreed after today is refused.
    twice = post(
        planner,
        "/contracts/work-orders/add/",
        aircraft=abcd,
        work=" [Work] ",
        ordered_by="Owner",
        agreed_on="2026-03-02",
    )
    assert "This Work Order Is Already Recorded and Open" in twice.content.decode()
    late = post(
        planner,
        "/contracts/work-orders/add/",
        aircraft=abcd,
        work="[Other Work]",
        ordered_by="Owner",
        agreed_on="2026-11-19",
    )
    assert "Not Agreed After Today" in late.content.decode()


def test_a_work_order_is_closed_once(
    sample: Sample, contracts: dict[str, Contract], fleet: dict[str, Aircraft]
) -> None:
    """REQ-245. Completed, with the work done on the same aircraft, or withdrawn."""
    planner = signed_in(sample.planner)
    with working_for(sample.ours.id, sample.reader.id):
        light = WorkOrder.objects.get(work="Landing Light Replacement")
        check = WorkOrder.objects.get(work="50-Hour Check")
        tyre = fleet["G-ABCD"].work_done.get()
    path = f"/contracts/work-orders/{light.id}/close/"
    assert "Close the Work Order, G-ABCD, Landing Light Replacement" in page(planner, path)
    for values, reason in (
        ({"closed_on": "2026-11-19", "outcome": "Completed"}, "Not Closed After Today"),
        ({"closed_on": "2026-11-11", "outcome": "Completed"}, "Not Closed Before It Was Agreed"),
        ({"closed_on": "2026-11-18", "outcome": "[Any]"}, "Select a valid choice"),
        (
            {"closed_on": "2026-11-18", "outcome": "Withdrawn", "work_done": str(tyre.id)},
            "Work Done Goes With a Completed Work Order",
        ),
    ):
        refused = post(planner, path, **values)
        assert refused.status_code == 200 and reason in refused.content.decode(), values
    other = post(
        planner,
        f"/contracts/work-orders/{check.id}/close/",
        closed_on="2026-11-18",
        outcome="Completed",
        work_done=str(tyre.id),
    )
    assert "Select a valid choice" in other.content.decode()
    done = post(planner, path, closed_on="2026-11-18", outcome="Completed", work_done=str(tyre.id))
    assert done.status_code == 302
    again = post(planner, path, closed_on="2026-11-18", outcome="Withdrawn")
    assert "This Work Order Is Already Closed" in again.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        closed = WorkOrder.objects.get(pk=light.pk)
        assert (closed.closed_on, closed.outcome, closed.work_done) == (TODAY, "Completed", tyre)
        with pytest.raises(IntegrityError, match="closed once"), transaction.atomic():
            WorkOrder.objects.filter(pk=light.pk).update(outcome="Withdrawn", work_done=None)
        for change in (
            {"closed_on": TODAY},
            {"outcome": "Completed"},
            {"closed_on": TODAY, "outcome": "[Any]"},
            {"closed_on": date(2026, 11, 15), "outcome": "Completed"},
            {"closed_on": TODAY, "outcome": "Withdrawn", "work_done": tyre},
        ):
            with (
                pytest.raises(IntegrityError, match="work_order_closed_has_an_outcome"),
                transaction.atomic(),
            ):
                WorkOrder.objects.filter(pk=check.pk).update(**change)
        with pytest.raises(services.RefusedError, match="Belongs to Another Aircraft"):
            services.close_work_order(check, closed_on=TODAY, outcome="Completed", work_done=tyre)
    (_, orders) = tables(page(planner, "/contracts/"))
    # Open orders first, then the closed one.
    assert [row[1] for row in orders] == [
        "Stabilator Trim Cable Rectification",
        "50-Hour Check",
        "Landing Light Replacement",
    ]
    assert orders[2][4:8] == ["Completed", "Signed 2 March 2026", "18 November 2026",
                              "Right Main Tyre Replaced"]  # fmt: skip


# Who may


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_draw_up_a_contract_and_record_a_work_order(
    sample: Sample, contracts: dict[str, Contract], fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, REQ-248. The Continuing Airworthiness Manager draws up and ends a
    contract; the manager and Planning and Records record and close a work order.
    Every role reads. A link or form is shown only to a role that may use it."""
    client = signed_in(getattr(sample, role))
    manager, records = role == "lucy", role in ("lucy", "planner")
    with working_for(sample.ours.id, sample.reader.id):
        order = WorkOrder.objects.get(work="50-Hour Check")
    contract = contracts["G-CDEF"]
    listed = page(client, "/contracts/").split("<main", 1)[1]
    one = page(client, f"/contracts/{contract.id}/").split("<main", 1)[1]
    assert ('href="/contracts/draw-up/"' in listed) == manager
    assert ('href="/contracts/work-orders/add/"' in listed) == records
    assert (f'href="/contracts/work-orders/{order.id}/close/"' in listed) == records
    assert ("<form" in one) == manager
    ejkl = str(fleet["G-EJKL"].id)
    assert get(client, "/contracts/draw-up/").status_code == (200 if manager else 403)
    drawn = post(client, "/contracts/draw-up/", aircraft=ejkl, **FORM)
    assert drawn.status_code == (302 if manager else 403)
    ended = post(client, f"/contracts/{contract.id}/end/", ended_on="2026-11-04",
                 end_reason="Denounced by Either Party")  # fmt: skip
    assert ended.status_code == (302 if manager else 403)
    told = post(client, f"/contracts/{contract.id}/authority-told/", told_on="2026-11-05")
    assert told.status_code == (302 if manager else 403)
    added = post(client, "/contracts/work-orders/add/", aircraft=ejkl, work="[Work]",
                 ordered_by="Owner", agreed_on="2026-11-17")  # fmt: skip
    assert added.status_code == (302 if records else 403)
    closed = post(client, f"/contracts/work-orders/{order.id}/close/", closed_on="2026-11-18",
                  outcome="Withdrawn")  # fmt: skip
    assert closed.status_code == (302 if records else 403)
    with working_for(sample.ours.id, sample.reader.id):
        assert (Contract.objects.get(pk=contract.pk).ended_on is not None) == manager
        assert (WorkOrder.objects.get(pk=order.pk).closed_on is not None) == records
    with as_owner():
        refused = AccessEntry.objects.filter(kind="Action Refused")
        expected = [] if manager else ["Draw Up or End Contract"] * 4
        expected += [] if records else ["Record Work Order"] * 2
        assert sorted(refused.values_list("detail", flat=True)) == expected


def test_another_organisations_contracts_are_not_found_or_shown(
    sample: Sample, contracts: dict[str, Contract], fleet: dict[str, Aircraft]
) -> None:
    """REQ-002, REQ-003."""
    stranger = signed_in(sample.stranger)
    contract = contracts["G-DGHI"]
    with working_for(sample.ours.id, sample.reader.id):
        order = WorkOrder.objects.get(work="50-Hour Check")
    assert get(stranger, f"/contracts/{contract.id}/").status_code == 404
    assert post(stranger, f"/contracts/{contract.id}/end/", ended_on="2026-11-04",
                end_reason="Other").status_code == 404  # fmt: skip
    assert get(stranger, f"/contracts/work-orders/{order.id}/close/").status_code == 404
    body = page(stranger, "/contracts/")
    assert "G-DGHI" not in body and "Flying Club" not in body and "50-Hour" not in body
    refused = post(stranger, "/contracts/draw-up/", aircraft=str(fleet["G-EJKL"].id), **FORM)
    assert "Select a valid choice" in refused.content.decode()
    with working_for(sample.other.id, sample.stranger.id):
        theirs = aircraft_services.add_aircraft(
            organisation=sample.other, registration="G-OTHR", type_rating="[Type]", owner="X"
        )
        for values in (
            {"aircraft": fleet["G-EJKL"], "customer_id": theirs.customer_id},
            {"aircraft": theirs, "customer_id": fleet["G-EJKL"].customer_id},
        ):
            with (
                pytest.raises(Exception, match="refers only to records of its own organisation"),
                transaction.atomic(),
            ):
                Contract.objects.create(
                    organisation=sample.other,
                    scope=Scope.ALL,
                    type_of_operation="[Operation]",
                    owner_address="[Address]",
                    signed_on=TODAY,
                    **values,
                )
        with (
            pytest.raises(Exception, match="refers only to records of its own organisation"),
            transaction.atomic(),
        ):
            WorkOrder.objects.create(
                organisation=sample.other,
                aircraft=theirs,
                contract=contract,
                work="[Work]",
                ordered_by=OrderedBy.OWNER,
                agreed_on=TODAY,
            )
