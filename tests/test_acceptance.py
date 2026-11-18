"""The problem log, the parallel run and the written approval (REQ-172 to REQ-174).

Today in the sample world is 18 November 2026.
"""

from datetime import date

import pytest
from django.db import DatabaseError, connection, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.acceptance import services
from airworthiness_plus.acceptance.models import NoteKind, Problem, ProblemNote
from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from tests.conftest import as_owner
from tests.support import TODAY, Sample, make_sample, signed_in

pytestmark = pytest.mark.django_db


class Day:
    def __init__(self) -> None:
        self.today = TODAY

    def __call__(self) -> date:
        return self.today


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    moving = Day()
    monkeypatch.setattr(aircraft_services, "today", moving)
    return moving


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def problem(sample: Sample) -> Problem:
    with working_for(sample.ours.id, sample.planner.id):
        return services.add_problem(
            organisation=sample.ours, raised_by=sample.planner, problem="[Problem Found]"
        )


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


# The problem log


def test_an_entry_records_the_problem_the_action_and_the_solution_with_dates_and_people(
    sample: Sample, day: Day
) -> None:
    """REQ-172. Through the pages, by three people on three days."""
    planner, lucy, reader = (
        signed_in(sample.planner),
        signed_in(sample.lucy),
        signed_in(sample.reader),
    )
    assert post(planner, "/problem-log/add/", problem="[Problem Found]").status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        problem = Problem.objects.get()
    assert "<td>Open</td>" in page(reader, "/problem-log/")
    day.today = date(2026, 11, 19)
    post(lucy, f"/problem-log/{problem.id}/notes/", kind="Action", text="[Action Taken]")
    assert "<td>Action Taken</td>" in page(reader, "/problem-log/")
    day.today = date(2026, 11, 20)
    post(planner, f"/problem-log/{problem.id}/notes/", kind="Solution", text="[Solution Found]")
    body = page(reader, "/problem-log/")
    assert "<td>18 November 2026, [Planning and Records Name]</td>" in body
    assert "<td>[Problem Found]</td>" in body
    assert "<td>Solved</td>" in body
    assert "<p>Action, 19 November 2026, Lucy Grant: [Action Taken]</p>" in body
    assert (
        "<p>Solution, 20 November 2026, [Planning and Records Name]: [Solution Found]</p>" in body
    )
    # A later note can still be added, and the entry stays Solved.
    post(lucy, f"/problem-log/{problem.id}/notes/", kind="Note", text="[Seen Again]")
    body = page(reader, "/problem-log/")
    assert "<p>Note, 20 November 2026, Lucy Grant: [Seen Again]</p>" in body
    assert (
        body.index("[Action Taken]") < body.index("[Solution Found]") < body.index("[Seen Again]")
    )
    # An entry or a note with nothing in it is not added.
    assert (
        "Describe the Problem" in post(planner, "/problem-log/add/", problem=" ").content.decode()
    )
    refused = post(planner, f"/problem-log/{problem.id}/notes/", kind="Note", text="")
    assert "Choose What to Add" in refused.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        assert (Problem.objects.count(), ProblemNote.objects.count()) == (1, 3)


def test_entries_that_are_not_solved_come_first(sample: Sample, problem: Problem) -> None:
    """REQ-172. An open problem is not lost below the solved ones."""
    with working_for(sample.ours.id, sample.planner.id):
        services.add_note(
            problem, kind=NoteKind.SOLUTION, text="[Solution]", noted_by=sample.planner
        )
        services.add_problem(
            organisation=sample.ours, raised_by=sample.planner, problem="[Second Problem]"
        )
        lines = services.problem_log()
    assert [line.status for line in lines] == ["Open", "Solved"]


def test_an_entry_and_its_notes_cannot_be_changed_or_removed(
    sample: Sample, problem: Problem
) -> None:
    """REQ-172, REQ-131. The application has no permission; the owner's change shows."""
    with working_for(sample.ours.id, sample.planner.id):
        note = services.add_note(
            problem, kind=NoteKind.ACTION, text="[Action]", noted_by=sample.planner
        )
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            Problem.objects.filter(pk=problem.pk).update(problem="[Changed]")
        with pytest.raises(DatabaseError, match="permission denied"), transaction.atomic():
            ProblemNote.objects.filter(pk=note.pk).update(text="[Changed]")
        with connection.cursor() as cursor:
            for table in ("acceptance_problem", "acceptance_problemnote"):
                with pytest.raises(DatabaseError), transaction.atomic():
                    cursor.execute(f"DELETE FROM {table}")  # noqa: S608
        # A second note cannot take the place of the first.
        with pytest.raises(DatabaseError), transaction.atomic():
            ProblemNote.objects.create(
                organisation_id=problem.organisation_id,
                problem=problem,
                kind=NoteKind.NOTE,
                text="[In Its Place]",
                noted_by=sample.planner,
                noted_on=TODAY,
                position=1,
            )
        assert [event.action for event in Event.of(problem)] == ["Created"]
    with as_owner(), connection.cursor() as cursor:
        with (
            pytest.raises(DatabaseError, match="never changed in place or deleted"),
            transaction.atomic(),
        ):
            cursor.execute("DELETE FROM acceptance_problem")


# The organisation page


def test_the_parallel_run_shows_when_six_months_have_passed(sample: Sample, day: Day) -> None:
    """REQ-173. 18 May 2026 and six months: 18 November 2026."""
    administrator = signed_in(sample.administrator)
    body = page(administrator, "/organisation/")
    assert "<dt>Parallel Run Started</dt><dd>Not Started</dd>" in body
    assert "<dt>Approval</dt><dd>Part-CAO, UK.CAO.[Number]</dd>" in body
    day.today = date(2026, 11, 17)
    refused = post(administrator, "/organisation/parallel-run/", started_on="2026-11-18")
    assert "A Parallel Run Cannot Start After Today" in refused.content.decode()
    assert (
        post(administrator, "/organisation/parallel-run/", started_on="2026-05-18").status_code
        == 302
    )
    body = page(signed_in(sample.reader), "/organisation/")
    assert "<dt>Parallel Run Started</dt><dd>18 May 2026</dd>" in body
    assert "<dt>6 Months</dt><dd>Pass on 18 November 2026</dd>" in body
    day.today = date(2026, 11, 18)
    body = page(signed_in(sample.reader), "/organisation/")
    assert "<dt>6 Months</dt><dd>Passed on 18 November 2026</dd>" in body


def test_the_written_approval_is_recorded_with_its_reference_and_date(sample: Sample) -> None:
    """REQ-174. The reference and the date go together, and the change is in the history."""
    administrator = signed_in(sample.administrator)
    assert "<dt>Approval Reference</dt><dd>Not Recorded</dd>" in page(
        administrator, "/organisation/"
    )
    refused = post(administrator, "/organisation/approval/", reference="[Reference]")
    assert "Give the Approval Reference and Its Date" in refused.content.decode()
    late = post(
        administrator, "/organisation/approval/", reference="[Reference]", dated="2026-11-19"
    )
    assert "An Approval Cannot Be Dated After Today" in late.content.decode()
    done = post(
        administrator,
        "/organisation/approval/",
        reference="[Approval Letter Reference]",
        dated="2026-10-01",
    )
    assert done.status_code == 302
    body = page(signed_in(sample.reader), "/organisation/")
    assert "<dt>Approval Reference</dt><dd>[Approval Letter Reference]</dd>" in body
    assert "<dt>Approval Dated</dt><dd>1 October 2026</dd>" in body
    with working_for(sample.ours.id, sample.administrator.id):
        organisation = Organisation.objects.get()
        last = Event.of(organisation).order_by("-sequence")[0]
        assert last.changed == ["records_approval_dated", "records_approval_reference"]
        assert last.actor_id == sample.administrator.id
        with pytest.raises(DatabaseError), transaction.atomic():
            Organisation.objects.filter(pk=organisation.pk).update(records_approval_dated=None)


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(problem: Problem):  # type: ignore[no-untyped-def]
    return [
        ("GET", "/problem-log/", Action.VIEW_RECORDS),
        ("POST", "/problem-log/add/", Action.ADD_TO_PROBLEM_LOG),
        ("POST", f"/problem-log/{problem.id}/notes/", Action.ADD_TO_PROBLEM_LOG),
        ("GET", "/organisation/", Action.VIEW_RECORDS),
        ("POST", "/organisation/approval/", Action.CHANGE_ORGANISATION_RECORD),
        ("POST", "/organisation/parallel-run/", Action.CHANGE_ORGANISATION_RECORD),
    ]


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


def test_another_organisations_problem_log_and_record_are_not_shown_or_changed(
    sample: Sample, problem: Problem
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    assert "[Problem Found]" not in page(stranger, "/problem-log/")
    response = post(stranger, f"/problem-log/{problem.id}/notes/", kind="Note", text="[Theirs]")
    assert response.status_code == 404
    body = page(stranger, "/organisation/")
    assert "[Other Organisation]" in body
    assert "[Your Organisation]" not in body
    post(stranger, "/organisation/parallel-run/", started_on="2026-01-01")
    with as_owner():
        assert ProblemNote.objects.count() == 0
        assert Organisation.objects.get(pk=sample.ours.pk).parallel_run_started_on is None
        assert Organisation.objects.get(pk=sample.other.pk).parallel_run_started_on == date(
            2026, 1, 1
        )


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_the_acceptance_pages_follow_the_role_matrix(
    sample: Sample, problem: Problem, role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in addresses(problem):
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
        "Administrator": 0,
        "Airworthiness Review Staff": 2,
        "Planning and Records": 2,
        "Read Only": 4,
    }
    assert refusals == expected[role]


def test_the_acceptance_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, problem: Problem
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    anonymous = Client()
    for method, path, _ in addresses(problem):
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.administrator, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in addresses(problem):
        if method == "POST":
            assert post(forged, path).status_code == 403, path
