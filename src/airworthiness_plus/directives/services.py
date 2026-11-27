"""What can be done with airworthiness directives. Views check the role first."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter
from airworthiness_plus.directives.models import (
    Applicability,
    Compliance,
    Decision,
    Directive,
    Source,
)
from airworthiness_plus.interface import formatting
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.programme import due
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Programme, Task, WorkDone
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Interval, Limit, Reading, TaskKind, Unit
from airworthiness_rules.programme import Flag, Thresholds, limit_flag


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def record_directive(
    *,
    organisation: Organisation,
    number: str,
    authority: str,
    subject: str,
    effective_date: date,
    revision: str = "",
    supersedes: Directive | None = None,
) -> Directive:
    """Record a directive (REQ-060). One that it supersedes stays, marked (REQ-068)."""
    return Directive.objects.create(
        organisation=organisation,
        number=number,
        authority=authority,
        subject=subject,
        effective_date=effective_date,
        revision=revision,
        supersedes=supersedes,
    )


@dataclass(frozen=True)
class Action:
    """What an applicable directive requires by a limit: once, or repeating.

    ``starts`` is where the first limit is counted from, usually the
    effective date with the counter\'s hours and cycles on that date.
    ``first`` is the time allowed for the first compliance; ``repeat`` is
    the interval after that, absent for an action done once.
    """

    counter: Counter
    starts: Reading
    first: Interval
    repeat: Interval | None = None


@transaction.atomic
def decide(
    *,
    directive: Directive,
    aircraft: Aircraft,
    decision: Decision,
    basis: str,
    decided_by: User,
    action: Action | None = None,
) -> Applicability:
    """Record whether a directive applies to one aircraft (REQ-061 to REQ-063, REQ-065).

    One aircraft at a time, always with a basis. A decision already made
    is changed in place, and the history keeps what it was.
    """
    if not basis.strip():
        raise RefusedError("A Decision States Its Basis")
    if decision == Decision.NOT_APPLICABLE and action is not None:
        raise RefusedError("A Directive That Does Not Apply Has No Action")
    existing = Applicability.objects.filter(directive=directive, aircraft=aircraft).first()
    task = existing.task if existing else None
    if decision == Decision.NOT_APPLICABLE and task is not None:
        programme_services.end_task(task)
        task = None
    if action is not None:
        if task is not None:
            raise RefusedError("This Directive Already Has an Action for This Aircraft")
        programme = Programme.objects.filter(aircraft=aircraft).first()
        if programme is None:
            raise RefusedError("Record the Maintenance Programme of This Aircraft First")
        if action.counter.aircraft_id != aircraft.id:
            raise RefusedError("The Counter Belongs to Another Aircraft")
        programme_services.check_calendar(action.first, action.repeat)
        repeat = action.repeat or action.first
        task = Task.objects.create(
            organisation_id=aircraft.organisation_id,
            programme=programme,
            title=f"{directive}, {directive.subject}"[:200],
            kind=TaskKind.AIRWORTHINESS_DIRECTIVE.value,
            counter=action.counter,
            source=f"{directive.authority} Airworthiness Directive {directive}; ML.A.303"[:200],
            interval_hours=repeat.hours,
            interval_cycles=repeat.cycles,
            interval_months=repeat.months,
            interval_days=repeat.days,
            first_hours=action.first.hours,
            first_cycles=action.first.cycles,
            first_months=action.first.months,
            first_days=action.first.days,
            starts_dated=action.starts.on,
            starts_hours=action.starts.hours,
            starts_cycles=action.starts.cycles,
            once=action.repeat is None,
        )
    values = {
        "organisation_id": aircraft.organisation_id,
        "decision": decision,
        "basis": basis.strip(),
        "decided_by": decided_by,
        "decided_on": aircraft_services.today(),
        "task": task,
    }
    applicability, _ = Applicability.objects.update_or_create(
        directive=directive, aircraft=aircraft, defaults=values
    )
    return applicability


@transaction.atomic
def record_compliance(
    applicability: Applicability,
    *,
    method: str,
    dated: date,
    hours: Decimal,
    cycles: int,
    performed_by: Person | None = None,
    release_reference: str = "",
    release_recorded_on: date | None = None,
    historical: bool = False,
) -> Compliance:
    """Record compliance with a directive on an aircraft (REQ-064).

    The record of work holds the method, date, hours, cycles and release
    to service reference. Each compliance is a new record. For work done
    before these records began, ``release_recorded_on`` is the day the
    release went into the aircraft's records; without it the release is
    taken to be recorded today (REQ-051).
    """
    if applicability.decision != Decision.APPLICABLE:
        raise RefusedError("Compliance Is Recorded Against a Directive That Applies")
    try:
        work = programme_services.record_work(
            applicability.aircraft,
            task=applicability.task
            if (
                applicability.terminated_on is None
                or (historical and dated < applicability.terminated_on)
            )
            else None,
            description=f"{applicability.directive}: {method}"[:200],
            dated=dated,
            hours=hours,
            cycles=cycles,
            performed_by=performed_by,
            release_reference=release_reference,
            release_recorded_on=release_recorded_on,
            historical=historical,
        )
    except programme_services.RefusedError as error:
        raise RefusedError(str(error)) from error
    return Compliance.objects.create(
        organisation_id=applicability.organisation_id, applicability=applicability, work=work
    )


@transaction.atomic
def terminate(applicability: Applicability, *, action: str, on: date) -> None:
    """Record a terminating action: the repetition ends, the earlier records stay (REQ-066)."""
    if not action.strip():
        raise RefusedError("A Terminating Action Is Described")
    if on > aircraft_services.today():
        raise RefusedError("A Terminating Action Cannot Be Dated After Today")
    if applicability.task is not None:
        programme_services.end_task(applicability.task)
    applicability.terminating_action = action.strip()
    applicability.terminated_on = on
    applicability.save(update_fields=["terminating_action", "terminated_on"])


@dataclass(frozen=True)
class StatusLine:
    """One directive against one aircraft: decision, compliance and what is next (REQ-067)."""

    directive: Directive
    applicability: Applicability | None
    last_compliance: WorkDone | None
    compliance_count: int
    next_due: str
    flag: Flag
    directive_superseded: bool
    # How each limit of what is next due was worked out (REQ-139).
    limits: tuple[due.ExplainedLimit, ...] = ()

    @property
    def state(self) -> str:
        """Return the decision, or that there is none yet (REQ-062)."""
        if self.directive_superseded:
            return "Superseded"
        return self.applicability.decision if self.applicability else "Applicability to Assess"

    @property
    def to_assess(self) -> bool:
        """Return whether a decision is still owed for this aircraft."""
        return self.applicability is None and not self.directive_superseded


def status(aircraft: Aircraft, today: date) -> list[StatusLine]:
    """Return the directive status of an aircraft: every directive recorded (REQ-067).

    A directive with no decision for this aircraft is shown as
    Applicability to Assess, never left out and never assumed either way.
    """
    decisions = {
        item.directive_id: item
        for item in Applicability.objects.filter(aircraft=aircraft).select_related("task")
    }
    programme = Programme.objects.filter(aircraft=aircraft).first()
    thresholds = due.thresholds_of(aircraft.organisation)
    lines = []
    for directive in Directive.objects.all():
        applicability = decisions.get(directive.id)
        last, count, next_due, flag = None, 0, "", Flag.NONE
        limits: tuple[due.ExplainedLimit, ...] = ()
        if applicability is not None:
            works = WorkDone.objects.filter(
                pk__in=applicability.compliance.values("work_id")
            ).order_by("dated", "hours")
            last, count = works.last(), works.count()
            task = applicability.task
            if applicability.terminated_on is not None:
                next_due = "Terminated"
            elif task is not None and task.once and count:
                next_due = "Complied With"
            elif task is not None and programme is not None and aircraft.calculations_supported:
                line = due.due_line(task, programme, today, thresholds)
                flag = line.flag
                if line.needs_attention:
                    next_due = f"Cannot Be Calculated, {line.problem}"
                else:
                    limits = line.limits
                    next_due = " or ".join(
                        f"{limit.due_text}, {limit.remaining_text}" for limit in limits
                    )
        superseded = Directive.objects.filter(supersedes=directive).exists()
        lines.append(
            StatusLine(directive, applicability, last, count, next_due, flag, superseded, limits)
        )
    return lines


@transaction.atomic
def add_source(organisation: Organisation, *, name: str, covers: str, note: str = "") -> Source:
    """Record a source the organisation checks for new directives (REQ-288). Once."""
    name, covers = name.strip(), covers.strip()
    if not name or not covers:
        raise RefusedError("A Source Has a Name and Says What It Covers")
    Organisation.objects.select_for_update().get(pk=organisation.pk)
    if Source.objects.filter(name=name).exists():
        raise RefusedError("This Source Is Already Recorded")
    return Source.objects.create(
        organisation=organisation, name=name, covers=covers, note=note.strip()
    )


@transaction.atomic
def record_source_check(
    source: Source,
    *,
    checked_on: date,
    next_check_on: date | None = None,
    next_check_note: str = "",
) -> Source:
    """Record that a source was checked, and when it is next checked (REQ-288).

    The next check is a day, or words such as Each Amendment, and not
    both. A check is not before the last one, and the same check sent
    twice is recorded once.
    """
    words = next_check_note.strip()
    source = Source.objects.select_for_update().get(pk=source.pk)
    if checked_on > aircraft_services.today():
        raise RefusedError("A Check Is Not After Today")
    if (next_check_on is None) == (not words):
        raise RefusedError("Give the Day of the Next Check, or Say When It Is, and Not Both")
    if next_check_on is not None and next_check_on < checked_on:
        raise RefusedError("The Next Check Is Not Before This One")
    if source.last_checked_on is not None:
        if checked_on < source.last_checked_on:
            raise RefusedError("A Check Is Not Before the Last One")
        same = (source.last_checked_on, source.next_check_on, source.next_check_note)
        if same == (checked_on, next_check_on, words):
            raise RefusedError("This Check Is Already Recorded")
    source.last_checked_on = checked_on
    source.next_check_on = next_check_on
    source.next_check_note = words
    source.save(update_fields=["last_checked_on", "next_check_on", "next_check_note"])
    return source


@dataclass(frozen=True)
class SourceLine:
    """One source, with when its next check is due and how it stands."""

    source: Source
    flag: Flag
    days: int | None

    @property
    def next_text(self) -> str:
        """Return the next check: a day, words, or that it has never been checked."""
        source = self.source
        if source.next_check_on is not None:
            return formatting.long_date(source.next_check_on)
        return source.next_check_note or "Not Checked"

    @property
    def status(self) -> str:
        """Return the word of the status mark. A source never checked is to assess."""
        if self.source.last_checked_on is None:
            return "To Assess"
        return self.flag.value


def source_lines(organisation: Organisation, today: date) -> list[SourceLine]:
    """Return every source: one never checked first, then the nearest check (REQ-289)."""
    thresholds = Thresholds(days=organisation.due_soon_days)
    lines = []
    for source in Source.objects.all():
        flag, days = Flag.NONE, None
        if source.next_check_on is not None:
            days = days_between(today, source.next_check_on)
            flag = limit_flag(Limit(Unit.CALENDAR, source.next_check_on, days), thresholds)
        lines.append(SourceLine(source, flag, days))
    return sorted(
        lines,
        key=lambda line: (
            line.source.last_checked_on is not None,
            line.days is None,
            line.days or 0,
            line.source.name,
        ),
    )
