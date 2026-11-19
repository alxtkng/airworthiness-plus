"""Airworthiness directives (REQ-060 to REQ-068, hazard H-002).

SampleData.md names no particular directive, so the directives here are
placeholders in square brackets, set against G-ABCD of the sample fleet.
Today in the sample world is 18 November 2026.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.directives import services
from airworthiness_plus.directives.models import Applicability, Compliance, Decision, Directive
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.programme import due
from airworthiness_plus.programme.models import Task, WorkDone
from airworthiness_plus.sample import build
from airworthiness_rules.intervals import Interval, Reading, State
from airworthiness_rules.programme import Flag
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    dot,
    make_sample,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture(autouse=True)
def sample_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    return fleet


@pytest.fixture
def directives(sample: Sample, fleet: dict[str, Aircraft]) -> dict[int, Directive]:
    """Four directives, and for G-ABCD: one repeating, one not applicable, one
    not yet decided, one to be done once."""
    return build.add_directives(sample, fleet)


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **data: str) -> HttpResponse:
    return client.post(path, data, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def decision_of(sample: Sample, directive: Directive, aircraft: Aircraft) -> Applicability:
    with working_for(sample.ours.id, sample.lucy.id):
        return Applicability.objects.get(directive=directive, aircraft=aircraft)


# The status of an aircraft


def test_g_abcd_directive_status(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-067, golden. Every directive recorded, with its applicability, its
    compliance and what is next.

    1: complied with at 6,350.0 hours on 20 July 2026, then every 100 hours:
       next at 6,450.0; 6,450.0 less 6,412.6 is 37.4 hours.
    2: Not Applicable, with its basis.
    3: no decision yet: Applicability to Assess.
    4: once, within 3 months of 1 October 2026: by 1 January 2027, 44 days
       (12 left in November, 31 in December, 1 in January)."""
    with working_for(sample.ours.id, sample.reader.id):
        lines = {
            line.directive.number: line
            for line in services.status(Aircraft.objects.get(pk=fleet["G-ABCD"].pk), TODAY)
        }
    one, two, three, four = (lines[f"[Directive Number {n}]"] for n in (1, 2, 3, 4))
    assert (one.state, one.next_due, one.flag) == (
        "Applicable",
        "6,450.0 Hours, 37.4 Hours",
        Flag.NONE,
    )
    assert one.compliance_count == 1
    assert one.last_compliance is not None
    assert (one.last_compliance.dated, one.last_compliance.hours) == (
        date(2026, 7, 20),
        D("6350.0"),
    )
    assert (two.state, two.next_due, two.to_assess) == ("Not Applicable", "", False)
    assert (three.state, three.to_assess) == ("Applicability to Assess", True)
    assert (four.state, four.next_due, four.flag) == (
        "Applicable",
        "1 January 2027, 44 Days",
        Flag.NONE,
    )

    body = page(signed_in(sample.reader), f"/aircraft/{fleet['G-ABCD'].id}/directives/")
    for text in (
        "<td>6,450.0 Hours, 37.4 Hours</td>",
        "<td>Not Applicable</td>",
        "<td>Propeller Model Not Fitted, Logbook Checked</td>",
        "<td>Applicability to Assess</td>",
        f"<td>{dot('To Assess')}</td>",
        "<td>Lucy Grant, 18 November 2026</td>",
        "Inspected in Accordance with Paragraph 2, 20 July 2026 at 6,350.0 Hours, "
        "[Release Reference 4]",
        "<td>1 January 2027, 44 Days</td>",
    ):
        assert text in body, text


def test_there_is_no_default_applicability(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-062, hazard H-002. A directive is to be assessed for every aircraft
    until someone decides, and the page offers no decision in advance."""
    with working_for(sample.ours.id, sample.reader.id):
        for registration in ("G-BXYZ", "G-FMNO", "G-HKLM"):
            lines = services.status(Aircraft.objects.get(pk=fleet[registration].pk), TODAY)
            assert [line.state for line in lines] == ["Applicability to Assess"] * 4
            assert all(line.to_assess for line in lines)
    form = page(
        signed_in(sample.lucy),
        f"/aircraft/{fleet['G-BXYZ'].id}/directives/{directives[1].id}/decide/",
    )
    assert '<option value="" selected>Choose</option>' in form
    assert 'value="Not Applicable" selected' not in form
    assert 'value="Applicable" selected' not in form


def test_a_decision_needs_a_choice_and_a_basis(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-061, REQ-063. On the page, in the service and in the database."""
    client = signed_in(sample.lucy)
    path = f"/aircraft/{fleet['G-BXYZ'].id}/directives/{directives[2].id}/decide/"
    assert post(client, path, decision="", basis="Not Fitted").status_code == 200
    assert post(client, path, decision="Not Applicable", basis="").status_code == 200
    assert post(client, path, decision="Not Applicable", basis="   ").status_code == 200
    with working_for(sample.ours.id, sample.lucy.id):
        assert not Applicability.objects.filter(aircraft=fleet["G-BXYZ"]).exists()
        with pytest.raises(services.RefusedError, match="Basis"):
            services.decide(
                directive=directives[2],
                aircraft=fleet["G-BXYZ"],
                decision=Decision.NOT_APPLICABLE,
                basis=" ",
                decided_by=sample.lucy,
            )
        with pytest.raises(IntegrityError, match="basis"), transaction.atomic():
            Applicability.objects.create(
                organisation=sample.ours,
                directive=directives[2],
                aircraft=fleet["G-BXYZ"],
                decision=Decision.NOT_APPLICABLE,
                basis="",
                decided_by=sample.lucy,
                decided_on=TODAY,
            )
    done = post(client, path, decision="Not Applicable", basis="Propeller Model Not Fitted")
    assert done.status_code == 302
    made = decision_of(sample, directives[2], fleet["G-BXYZ"])
    assert (made.decision, made.decided_by_id, made.decided_on) == (
        "Not Applicable",
        sample.lucy.id,
        TODAY,
    )


def test_not_applicable_cannot_be_set_for_several_aircraft_at_once(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-063, hazard H-002. One statement that would mark two aircraft Not
    Applicable is refused by the database, for the application and for the owner."""
    insert = (
        "INSERT INTO directives_applicability (id, organisation_id, directive_id, aircraft_id, "
        "decision, basis, decided_by_id, decided_on, terminating_action) VALUES "
        "(%s, %s, %s, %s, 'Not Applicable', 'Bulk', %s, '2026-11-18', ''), "
        "(%s, %s, %s, %s, 'Not Applicable', 'Bulk', %s, '2026-11-18', '')"
    )
    values = [
        value
        for registration in ("G-BXYZ", "G-FMNO")
        for value in (
            uuid.uuid4(),
            sample.ours.id,
            directives[3].id,
            fleet[registration].id,
            sample.lucy.id,
        )
    ]
    with working_for(sample.ours.id, sample.lucy.id):
        with (
            pytest.raises(DatabaseError, match="one aircraft at a time"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(insert, values)
        # Two aircraft marked Applicable, then one statement to flip them both.
        for registration in ("G-BXYZ", "G-FMNO"):
            services.decide(
                directive=directives[3],
                aircraft=fleet[registration],
                decision=Decision.APPLICABLE,
                basis="Seat Rail Part Number Fitted",
                decided_by=sample.lucy,
            )
        with pytest.raises(DatabaseError, match="one aircraft at a time"), transaction.atomic():
            Applicability.objects.filter(directive=directives[3]).update(
                decision=Decision.NOT_APPLICABLE
            )
    with as_owner(), working_for(sample.ours.id):
        with (
            pytest.raises(DatabaseError, match="one aircraft at a time"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "UPDATE directives_applicability SET decision = 'Not Applicable' "
                "WHERE directive_id = %s",
                [directives[3].id],
            )
    with working_for(sample.ours.id, sample.lucy.id):
        assert set(
            Applicability.objects.filter(directive=directives[3]).values_list("decision", flat=True)
        ) == {"Applicable"}


def test_a_changed_decision_is_in_the_history(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-061, REQ-130. Not Applicable changed to Applicable: who, when, and what it was."""
    made = decision_of(sample, directives[2], fleet["G-ABCD"])
    with working_for(sample.ours.id, sample.lucy.id):
        services.decide(
            directive=directives[2],
            aircraft=fleet["G-ABCD"],
            decision=Decision.APPLICABLE,
            basis="Propeller Changed on 10 November 2026",
            decided_by=sample.lucy,
        )
        created, changed = Event.of(made)
    assert changed.changed == ["basis", "decision"]
    assert changed.before_json is not None
    assert '"decision": "Not Applicable"' in changed.before_json
    assert "Propeller Model Not Fitted" in changed.before_json
    assert (created.actor_name, changed.actor_name) == ("Lucy Grant", "Lucy Grant")


# Repeating and once-only actions


def test_a_directive_has_no_tolerance(
    sample: Sample,
    fleet: dict[str, Aircraft],
    directives: dict[int, Directive],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REQ-049, REQ-065, ML.A.303. Due at 6,450.0: at 6,450.1, a week later, it is
    Overdue, with nothing in between. The action is a task of the programme
    (ML.A.302(c)(4))."""
    abcd = fleet["G-ABCD"]
    made = decision_of(sample, directives[1], abcd)
    later = date(2026, 11, 25)
    monkeypatch.setattr(aircraft_services, "today", lambda: later)
    with working_for(sample.ours.id, sample.planner.id):
        assert made.task is not None
        assert made.task.kind == "Airworthiness Directive"
        counter = abcd.counters.get(kind=CounterKind.AIRFRAME)
        aircraft_services.enter_utilisation(counter, Reading(later, D("6450.1"), 0))
        lines = {
            line.task.id: line for line in due.due_lines(Aircraft.objects.get(pk=abcd.pk), later)
        }
        line = lines[made.task.id]
    (limit,) = line.limits
    assert limit.limit.tolerance_limit is None
    assert limit.limit.state is State.OVERDUE
    assert line.flag is Flag.OVERDUE
    assert "ML.A.303" in limit.source
    body = page(signed_in(sample.reader), f"/aircraft/{abcd.id}/programme/")
    assert "[Directive Number 1], [Fuel Selector Valve Inspection]" in body
    form = page(signed_in(sample.lucy), f"/aircraft/{abcd.id}/programme/tasks/add/")
    assert '<option value="Airworthiness Directive">' not in form
    assert '<option value="Programme Task">' in form


def test_an_action_done_once_is_finished_when_complied_with(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-064, REQ-065. Complied with on 18 November 2026: nothing further is due."""
    abcd = fleet["G-ABCD"]
    made = decision_of(sample, directives[4], abcd)
    client = signed_in(sample.planner)
    done = post(
        client,
        f"/directive-decisions/{made.id}/comply/",
        method="Placard Installed",
        dated="2026-11-18",
        hours="6412.6",
        cycles="0",
        release_reference="[Release Reference 5]",
    )
    assert done.status_code == 302
    body = page(client, f"/aircraft/{abcd.id}/directives/")
    assert "<td>Complied With</td>" in body
    assert "Placard Installed, 18 November 2026 at 6,412.6 Hours, [Release Reference 5]" in body
    assert (
        "[Placard Installation]"
        not in page(client, f"/aircraft/{abcd.id}/programme/").split("<h2>Work Done</h2>")[0]
    )


def test_a_terminating_action_ends_the_repetition_and_keeps_the_records(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-066. Two inspections, then the valve is replaced: nothing more is due,
    and both inspections stay in the record."""
    abcd = fleet["G-ABCD"]
    made = decision_of(sample, directives[1], abcd)
    with working_for(sample.ours.id, sample.planner.id):
        services.record_compliance(
            made, method="Inspected Again", dated=date(2026, 11, 10), hours=D("6405.0"), cycles=0
        )
    client = signed_in(sample.lucy)
    ended = post(
        client,
        f"/directive-decisions/{made.id}/terminate/",
        action="Fuel Selector Valve Replaced with Improved Part",
        on="2026-11-18",
    )
    assert ended.status_code == 302
    body = page(client, f"/aircraft/{abcd.id}/directives/")
    assert "Terminated, Fuel Selector Valve Replaced with Improved Part, 18 November 2026" in body
    assert "2 Records" in body
    with working_for(sample.ours.id, sample.lucy.id):
        made.refresh_from_db()
        assert made.task is not None
        assert Task.objects.get(pk=made.task.pk).retired
        assert Compliance.objects.filter(applicability=made).count() == 2
        assert WorkDone.objects.filter(task=made.task).count() == 2
        lines = due.due_lines(Aircraft.objects.get(pk=abcd.pk), TODAY)
        assert made.task.id not in {line.task.id for line in lines}
        # Compliance records cannot be changed or removed.
        with (
            pytest.raises(DatabaseError, match="permission denied"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute("UPDATE directives_compliance SET work_id = work_id")


def test_an_action_needs_the_programme_and_a_counter_of_the_aircraft(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-065, ML.A.302(c)(4). G-EJKL has no programme recorded yet."""
    with working_for(sample.ours.id, sample.lucy.id):
        ejkl = fleet["G-EJKL"]
        action = services.Action(
            counter=ejkl.counters.get(kind=CounterKind.AIRFRAME),
            starts=Reading(date(2026, 11, 2), D("11200.0"), 0),
            first=Interval(hours=D("25")),
        )
        with pytest.raises(services.RefusedError, match="Programme"):
            services.decide(
                directive=directives[3],
                aircraft=ejkl,
                decision=Decision.APPLICABLE,
                basis="Seat Rail Part Number Fitted",
                decided_by=sample.lucy,
                action=action,
            )
        with pytest.raises(services.RefusedError, match="Another Aircraft"):
            services.decide(
                directive=directives[3],
                aircraft=fleet["G-BXYZ"],
                decision=Decision.APPLICABLE,
                basis="Seat Rail Part Number Fitted",
                decided_by=sample.lucy,
                action=action,
            )
        with pytest.raises(services.RefusedError, match="Has No Action"):
            services.decide(
                directive=directives[3],
                aircraft=fleet["G-BXYZ"],
                decision=Decision.NOT_APPLICABLE,
                basis="Not Fitted",
                decided_by=sample.lucy,
                action=action,
            )
        assert not Applicability.objects.filter(directive=directives[3]).exists()


def test_an_action_is_recorded_through_the_page(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-065. G-BXYZ: within 25 hours of 3,300.0 on 2 November 2026, then every
    50 hours. First due 3,325.0; 3,325.0 less 3,318.0 is 7.0 hours: Due Soon."""
    bxyz = fleet["G-BXYZ"]
    client = signed_in(sample.lucy)
    with working_for(sample.ours.id, sample.lucy.id):
        counter = bxyz.counters.get(kind=CounterKind.AIRFRAME)
    path = f"/aircraft/{bxyz.id}/directives/{directives[3].id}/decide/"
    fields = {
        "decision": "Applicable",
        "basis": "Seat Rail Part Number Fitted",
        "first_hours": "25",
        "repeat_hours": "50",
    }
    missing = post(client, path, **fields)
    assert "An Action Names Its Counter and Where It Is Counted From" in missing.content.decode()
    made = post(
        client,
        path,
        **fields,
        counter=str(counter.id),
        starts_dated="2026-11-02",
        starts_hours="3300.0",
        starts_cycles="0",
    )
    assert made.status_code == 302
    body = page(client, f"/aircraft/{bxyz.id}/directives/")
    assert "<td>3,325.0 Hours, 7.0 Hours</td>" in body
    assert f"<td>{dot('Due Soon')}</td>" in body


# The list of directives


def test_a_superseded_directive_stays_and_names_its_successor(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-060, REQ-068. The revision is assessed afresh; the old decision stays."""
    client = signed_in(sample.planner)
    added = post(
        client,
        "/directives/add/",
        number="[Directive Number 2]",
        authority="Civil Aviation Authority",
        subject="[Propeller Hub Inspection]",
        effective_date="2026-11-16",
        revision="Revision 1",
        supersedes=str(directives[2].id),
    )
    assert added.status_code == 302
    body = page(client, "/directives/")
    assert "<td>Superseded by [Directive Number 2] Revision 1</td>" in body
    assert body.count("<td>Current</td>") == 4
    again = post(
        client,
        "/directives/add/",
        number="[Directive Number 2]",
        authority="Civil Aviation Authority",
        subject="[Propeller Hub Inspection]",
        effective_date="2026-11-16",
        revision="Revision 1",
    )
    assert "This Directive and Revision Are Already Recorded" in again.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        lines = {
            str(line.directive): line
            for line in services.status(Aircraft.objects.get(pk=fleet["G-ABCD"].pk), TODAY)
        }
    assert lines["[Directive Number 2]"].state == "Superseded"
    assert lines["[Directive Number 2]"].applicability is not None
    assert lines["[Directive Number 2] Revision 1"].state == "Applicability to Assess"
    assert Directive.objects.count() == 0  # nothing without an organisation set


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(aircraft: Aircraft, directive: Directive, made: Applicability):  # type: ignore[no-untyped-def]
    decide = f"/aircraft/{aircraft.id}/directives/{directive.id}/decide/"
    comply = f"/directive-decisions/{made.id}/comply/"
    end = f"/directive-decisions/{made.id}/terminate/"
    return [
        ("GET", f"/aircraft/{aircraft.id}/directives/", Action.VIEW_RECORDS),
        ("GET", decide, Action.DECIDE_DIRECTIVE_APPLICABILITY),
        ("POST", decide, Action.DECIDE_DIRECTIVE_APPLICABILITY),
        ("GET", comply, Action.RECORD_DIRECTIVE_COMPLIANCE),
        ("POST", comply, Action.RECORD_DIRECTIVE_COMPLIANCE),
        ("GET", end, Action.DECIDE_DIRECTIVE_APPLICABILITY),
        ("POST", end, Action.DECIDE_DIRECTIVE_APPLICABILITY),
    ]


GENERAL = [
    ("GET", "/directives/", Action.VIEW_RECORDS),
    ("GET", "/directives/add/", Action.RECORD_AIRWORTHINESS_DIRECTIVE),
    ("POST", "/directives/add/", Action.RECORD_AIRWORTHINESS_DIRECTIVE),
]


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


def test_another_organisations_directives_are_not_found_or_shown(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    made = decision_of(sample, directives[1], fleet["G-ABCD"])
    for method, path, _ in addresses(fleet["G-ABCD"], directives[1], made):
        assert call(stranger, method, path).status_code == 404, f"{method} {path}"
    assert "[Directive Number 1]" not in page(stranger, "/directives/")
    with as_owner():
        assert Applicability.objects.get(pk=made.pk).terminated_on is None


@pytest.mark.parametrize(
    "role",
    ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"],
)
def test_every_directive_page_follows_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive], role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Only the Continuing
    Airworthiness Manager decides applicability; Planning and Records may record
    a directive and compliance; the refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    made = decision_of(sample, directives[1], fleet["G-ABCD"])
    refusals = 0
    for method, path, action in [*addresses(fleet["G-ABCD"], directives[1], made), *GENERAL]:
        status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status in (200, 302), f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    expected = {
        "Administrator": 8,
        "Airworthiness Review Staff": 8,
        "Planning and Records": 4,
        "Read Only": 8,
    }
    assert refusals == expected[role]


def test_directive_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, fleet: dict[str, Aircraft], directives: dict[int, Directive]
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    made = decision_of(sample, directives[1], fleet["G-ABCD"])
    pages = [*addresses(fleet["G-ABCD"], directives[1], made), *GENERAL]
    anonymous = Client()
    for method, path, _ in pages:
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in pages:
        if method == "POST":
            assert post(forged, path).status_code == 403, path
