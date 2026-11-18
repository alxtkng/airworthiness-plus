"""The problem log, the parallel run and the written approval (REQ-172 to REQ-174)."""

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.acceptance.models import NoteKind, Problem, ProblemNote
from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.acceptance import parallel_run_passed, parallel_run_passes_on


class RefusedError(Exception):
    """What was asked cannot be recorded. The message says why."""


def add_problem(*, organisation: Organisation, raised_by: User, problem: str) -> Problem:
    """Add an entry to the problem log, dated today."""
    if not problem.strip():
        raise RefusedError("An Entry Describes the Problem")
    return Problem.objects.create(
        organisation=organisation,
        problem=problem.strip(),
        raised_by=raised_by,
        raised_on=aircraft_services.today(),
    )


@transaction.atomic
def add_note(problem: Problem, *, kind: NoteKind, text: str, noted_by: User) -> ProblemNote:
    """Add the action, the solution or a note to an entry, dated today.

    The entry itself is never changed. A note can be added after the
    solution, for example if the problem comes back.
    """
    if not text.strip():
        raise RefusedError("A Note Says Something")
    # Two notes added at the same moment would take the same position; the
    # database refuses the second, which is then added again.
    return ProblemNote.objects.create(
        organisation_id=problem.organisation_id,
        problem=problem,
        kind=kind,
        text=text.strip(),
        noted_by=noted_by,
        noted_on=aircraft_services.today(),
        position=problem.notes.count() + 1,
    )


@dataclass(frozen=True)
class ProblemLine:
    """One entry of the problem log with what has been added to it."""

    problem: Problem
    notes: list[ProblemNote]

    @property
    def status(self) -> str:
        """Return where the entry stands: Solved once a solution is recorded."""
        kinds = {note.kind for note in self.notes}
        if NoteKind.SOLUTION in kinds:
            return "Solved"
        return "Action Taken" if NoteKind.ACTION in kinds else "Open"


def problem_log() -> list[ProblemLine]:
    """Return the problem log, entries that are not solved first, then newest first."""
    problems = Problem.objects.select_related("raised_by").prefetch_related("notes__noted_by")
    lines = [ProblemLine(problem, list(problem.notes.all())) for problem in problems]
    return sorted(lines, key=lambda line: line.status == "Solved")


def record_approval(organisation: Organisation, *, reference: str, dated: date) -> None:
    """Record the Civil Aviation Authority's written approval of the records system (REQ-174)."""
    if not reference.strip():
        raise RefusedError("An Approval Has a Reference")
    if dated > aircraft_services.today():
        raise RefusedError("An Approval Cannot Be Dated After Today")
    organisation.records_approval_reference = reference.strip()
    organisation.records_approval_dated = dated
    organisation.save(update_fields=["records_approval_reference", "records_approval_dated"])


def record_parallel_run(organisation: Organisation, *, started_on: date) -> None:
    """Record the day the organisation began running the system beside its records (REQ-173)."""
    if started_on > aircraft_services.today():
        raise RefusedError("A Parallel Run Cannot Start After Today")
    organisation.parallel_run_started_on = started_on
    organisation.save(update_fields=["parallel_run_started_on"])


@dataclass(frozen=True)
class ParallelRun:
    """Where the parallel run stands today."""

    started_on: date
    passes_on: date
    passed: bool


def parallel_run(organisation: Organisation) -> ParallelRun | None:
    """Return the parallel run and when its 6 months pass, or nothing if it has not begun."""
    started = organisation.parallel_run_started_on
    if started is None:
        return None
    return ParallelRun(
        started,
        parallel_run_passes_on(started),
        parallel_run_passed(started, aircraft_services.today()),
    )
