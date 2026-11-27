"""What is due on an aircraft, with the working shown (REQ-042 to REQ-058, REQ-139).

Every figure comes from ``airworthiness_rules``. This module gathers the
inputs from the records, and puts beside each figure the rule, the inputs
and the source it was calculated from, so that nobody has to take the
figure on trust (hazard H-014).
"""

from dataclasses import dataclass
from datetime import date

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme.models import (
    Basis,
    InspectionCategory,
    Programme,
    Task,
    WorkDone,
)
from airworthiness_rules.dates import BeyondCalendarError, days_between
from airworthiness_rules.intervals import (
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE,
    MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE,
    Interval,
    Limit,
    Reading,
    State,
    TaskKind,
    Tolerance,
    Unit,
    Utilisation,
    comes_first,
    limits,
    projected_days,
    task_state,
    tolerance_outlasts_certificate,
    tolerance_used,
)
from airworthiness_rules.programme import (
    Flag,
    Thresholds,
    deadline_flag,
    limit_flag,
    pilot_owner_notification_deadline,
    pilot_owner_told_late,
    programme_review_due,
    review_certificate_lead_days,
    task_flag,
)
from airworthiness_rules.records import release_record_deadline

RULES = {
    Unit.HOURS: (
        "Due at the Hours When Last Done Plus the Interval. "
        "Remaining Is Due Hours Less Current Hours"
    ),
    Unit.CYCLES: (
        "Due at the Cycles When Last Done Plus the Interval. "
        "Remaining Is Due Cycles Less Current Cycles"
    ),
    Unit.CALENDAR: (
        "Due the Interval After the Date Last Done. Remaining Is an Exact Count of Days From Today"
    ),
}


@dataclass(frozen=True)
class ExplainedLimit:
    """One limit of a task, with how it was worked out (REQ-139)."""

    limit: Limit
    flag: Flag
    first: bool
    projected: int | None
    rule: str
    inputs: tuple[tuple[str, str], ...]
    source: str
    # AMC1 ML.A.302(d): the day the review certificate ends, when the
    # tolerance of this limit ends after it (REQ-057).
    certificate_ends_first: date | None = None

    @property
    def due_text(self) -> str:
        return formatting.point(self.limit.unit, self.limit.due)

    @property
    def title(self) -> str:
        return f"How {self.due_text} Was Calculated"

    @property
    def remaining_text(self) -> str:
        return formatting.amount(self.limit.unit, self.limit.remaining)

    @property
    def tolerance_text(self) -> str:
        if self.limit.tolerance_limit is None:
            return ""
        return formatting.point(self.limit.unit, self.limit.tolerance_limit)


@dataclass(frozen=True)
class DueLine:
    """One task of the programme and where it stands today."""

    task: Task
    limits: tuple[ExplainedLimit, ...]
    flag: Flag
    ranked: bool
    reading: Reading | None
    never_done: bool
    problem: str
    # What is said when the tolerance was used at the last inspection (REQ-056).
    tolerance_note: str = ""

    @property
    def first(self) -> tuple[ExplainedLimit, ...]:
        """Return the limit or limits expected first."""
        return tuple(limit for limit in self.limits if limit.first)

    @property
    def reached(self) -> bool:
        return any(limit.limit.remaining <= 0 for limit in self.limits)

    @property
    def needs_attention(self) -> bool:
        """Return whether the task could not be calculated.

        Such a task is never shown as not due: nobody knows where it stands
        until what is missing is recorded. Found by the independent recompute.
        """
        return bool(self.problem)

    @property
    def remaining_summary(self) -> str:
        """Return what remains of the task, or why it cannot be calculated."""
        if not self.limits:
            return self.problem
        shown = self.first if self.ranked else self.limits
        return " or ".join(limit.remaining_text for limit in shown)

    @property
    def summary(self) -> str:
        """Return the task and what remains."""
        return f"{self.task.title}, {self.remaining_summary}"


def thresholds_of(organisation: Organisation) -> Thresholds:
    """Return the organisation's Due Soon thresholds (REQ-055)."""
    return Thresholds(
        days=organisation.due_soon_days,
        hours=organisation.due_soon_hours,
        cycles=organisation.due_soon_cycles,
    )


def certificate_thresholds(organisation: Organisation) -> Thresholds:
    """Return the thresholds for an airworthiness review certificate (REQ-213).

    As for everything else, but for the days: an organisation may turn on an
    earlier alert for its review certificates.
    """
    return Thresholds(
        days=review_certificate_lead_days(
            organisation.due_soon_days, organisation.review_alert_days
        ),
        hours=organisation.due_soon_hours,
        cycles=organisation.due_soon_cycles,
    )


def _tolerance(task: Task, programme: Programme) -> Tolerance | None:
    """Return the tolerance for a task: only for a Minimum Inspection Programme inspection.

    And only in a programme on that basis: ML.A.302(d)(1) gives the
    tolerance to the Minimum Inspection Programme and to nothing else.
    """
    if task.task_kind is not TaskKind.MINIMUM_INSPECTION_PROGRAMME:
        return None
    if programme.basis != Basis.MINIMUM_INSPECTION_PROGRAMME:
        return None
    if programme.inspection_category == InspectionCategory.SAILPLANE:
        return MINIMUM_INSPECTION_PROGRAMME_TOLERANCE_SAILPLANE
    return MINIMUM_INSPECTION_PROGRAMME_TOLERANCE


def _interval_text(interval: Interval) -> str:
    parts = []
    if interval.hours is not None:
        parts.append(formatting.amount(Unit.HOURS, interval.hours))
    if interval.cycles is not None:
        parts.append(formatting.amount(Unit.CYCLES, interval.cycles))
    if interval.months is not None:
        parts.append(f"{interval.months} Months" if interval.months != 1 else "1 Month")
    if interval.days is not None:
        parts.append(formatting.amount(Unit.CALENDAR, interval.days))
    return " or ".join(parts) + (", Whichever Comes First" if len(parts) > 1 else "")


def _reading_text(reading: Reading, unit: Unit) -> str:
    when = formatting.long_date(reading.on)
    if unit is Unit.HOURS:
        return f"{when} at {formatting.amount(Unit.HOURS, reading.hours)}"
    if unit is Unit.CYCLES:
        return f"{when} at {formatting.amount(Unit.CYCLES, reading.cycles)}"
    return when


def _explain(
    limit: Limit,
    *,
    task: Task,
    interval: Interval,
    start: Reading,
    never_done: bool,
    counter_reading: Reading | None,
    today: date,
    utilisation: Utilisation,
    tolerance: Tolerance | None,
    projected: int | None,
    ranked: bool,
) -> tuple[tuple[tuple[str, str], ...], str]:
    """Return the inputs and the source for one limit."""
    inputs = [
        (
            "Counted From, Never Yet Done" if never_done else "Last Done",
            _reading_text(start, limit.unit),
        ),
        ("First Threshold" if never_done else "Interval", _interval_text(interval)),
    ]
    if limit.unit is Unit.CALENDAR:
        inputs.append(("Today", formatting.long_date(today)))
    elif counter_reading is not None:
        value = counter_reading.hours if limit.unit is Unit.HOURS else counter_reading.cycles
        inputs.append(
            (
                f"Current, {task.counter}",
                f"{formatting.amount(limit.unit, value)}, Entered For "
                f"{formatting.long_date(counter_reading.on)}",
            )
        )
    if limit.tolerance_limit is not None and tolerance is not None:
        size = (
            "1 Month"
            if limit.unit is Unit.CALENDAR
            else formatting.amount(Unit.HOURS, tolerance.hours or 0)
        )
        inputs.append(
            ("Tolerance", f"{size}, to {formatting.point(limit.unit, limit.tolerance_limit)}")
        )
    if limit.unit is not Unit.CALENDAR:
        rate = utilisation.hours_per_day if limit.unit is Unit.HOURS else utilisation.cycles_per_day
        if projected is not None and rate is not None and limit.remaining > 0:
            per_day = formatting.amount(limit.unit, rate)
            inputs.append(
                (
                    "Projection, for Planning Only",
                    f"{formatting.amount(limit.unit, limit.remaining)} at {per_day} a Day Is "
                    f"{formatting.amount(Unit.CALENDAR, projected)}, Rounded Down",
                )
            )
        elif not ranked:
            inputs.append(
                ("Projection", "No Planning Utilisation Recorded, So Limits Are Not Ranked")
            )
    # The action of a directive is due under the directive, not under the programme.
    of_directive = task.kind == TaskKind.AIRWORTHINESS_DIRECTIVE.value
    source = task.source if of_directive else f"{task.source}; ML.A.302"
    if limit.tolerance_limit is not None:
        source += "; Tolerance, ML.A.302(d)(1)"
    return tuple(inputs), source


def due_line(
    task: Task,
    programme: Programme,
    today: date,
    thresholds: Thresholds,
    certificate_valid_to: date | None = None,
) -> DueLine:
    """Work out where one task stands today."""
    last = task.work_done.order_by("dated", "hours").last()
    never_done = last is None
    start = last.reading if last is not None else task.starts
    interval = task.first_interval if never_done else task.interval
    counter_reading = aircraft_services.current_reading(task.counter)

    def nothing(problem: str) -> DueLine:
        return DueLine(task, (), Flag.NONE, False, counter_reading, never_done, problem)

    if start is None:
        return nothing("No Starting Point Recorded")
    needs_counter = interval.hours is not None or interval.cycles is not None
    if needs_counter and counter_reading is None:
        return nothing(f"No Hours Recorded for {task.counter}")
    current = Reading(
        today,
        counter_reading.hours if counter_reading else start.hours,
        counter_reading.cycles if counter_reading else start.cycles,
    )
    tolerance = _tolerance(task, programme)
    try:
        found = limits(
            interval,
            start,
            current,
            kind=task.task_kind if tolerance is not None else None,
            tolerance=tolerance,
        )
    except BeyondCalendarError:
        return nothing("A Limit Falls After 31 December 9999 and Cannot Be Calculated")
    except ValueError:
        return nothing(f"Hours Entered for {task.counter} Are Older Than This Task's Last Record")

    utilisation = Utilisation(programme.hours_per_day, programme.cycles_per_day)
    first = comes_first(found, utilisation)
    ranked = (
        len(found) == 1
        or len(first) < len(found)
        or all(projected_days(limit, utilisation) is not None for limit in found)
    )
    explained = []
    for limit in found:
        projected = projected_days(limit, utilisation)
        inputs, source = _explain(
            limit,
            task=task,
            interval=interval,
            start=start,
            never_done=never_done,
            counter_reading=counter_reading,
            today=today,
            utilisation=utilisation,
            tolerance=tolerance,
            projected=projected,
            ranked=ranked,
        )
        explained.append(
            ExplainedLimit(
                limit=limit,
                flag=limit_flag(limit, thresholds),
                first=limit in first,
                projected=projected,
                rule=RULES[limit.unit],
                inputs=inputs,
                source=source,
                certificate_ends_first=certificate_valid_to
                if certificate_valid_to is not None
                and tolerance_outlasts_certificate(limit, certificate_valid_to)
                else None,
            )
        )
    return DueLine(
        task=task,
        limits=tuple(explained),
        flag=task_flag(found, thresholds),
        ranked=ranked,
        reading=counter_reading if needs_counter else None,
        never_done=never_done,
        problem="",
        tolerance_note=_tolerance_note(task, tolerance, found),
    )


ONE_TIME = "GM1 ML.A.302(c)(3) Calls the Tolerance a One-Time Extension"


def _tolerance_note(task: Task, tolerance: Tolerance | None, found: tuple[Limit, ...]) -> str:
    """Return what to say when the tolerance was used at the last inspection.

    Nothing is refused. A use is shown, and a use at two inspections in a
    row, done or about to be, is shown with what the guidance says of it.
    """
    if tolerance is None:
        return ""
    done = list(task.work_done.order_by("dated", "hours"))
    used: list[bool] = []
    previous = task.starts
    for position, work in enumerate(done):
        interval = task.first_interval if position == 0 else task.interval
        try:
            used.append(
                previous is not None
                and tolerance_used(
                    interval, previous, work.reading, kind=task.task_kind, tolerance=tolerance
                )
            )
        except ValueError:
            used.append(False)
        previous = work.reading
    if not used or not used[-1]:
        return ""
    last = formatting.long_date(done[-1].dated)
    if len(used) > 1 and used[-2]:
        return f"Tolerance Used at the Last Two Inspections, the Latest on {last}. {ONE_TIME}"
    if task_state(found) is State.WITHIN_TOLERANCE:
        return (
            f"Within Tolerance Again: the Tolerance Was Used at the Last Inspection, {last}. "
            f"{ONE_TIME}"
        )
    return f"Tolerance Used at the Last Inspection, {last}"


def due_lines(
    aircraft: Aircraft, today: date, certificate_valid_to: date | None = None
) -> list[DueLine]:
    """Return every task of the aircraft's programme and where it stands.

    Nothing is calculated for a Transfer In or a Non-Part 21 aircraft
    (REQ-022, REQ-027), or for an aircraft with no programme.
    """
    programme = Programme.objects.filter(aircraft=aircraft).first()
    if programme is None or not aircraft.calculations_supported:
        return []
    thresholds = thresholds_of(aircraft.organisation)
    return [
        due_line(task, programme, today, thresholds, certificate_valid_to)
        for task in programme.tasks.filter(retired=False).select_related("counter")
        if not (task.once and task.work_done.exists())
    ]


def next_due(lines: list[DueLine]) -> tuple[list[DueLine], bool]:
    """Return the task or tasks expected first, and whether every task could be ranked.

    A task with a limit already reached comes first, whatever the planning
    figures say. Otherwise tasks are ranked by the projected day of their
    first limit; a task that cannot be projected is not ranked, and the
    second value says so.
    """
    worked = [line for line in lines if line.limits]
    urgent = [line for line in lines if line.needs_attention or line.reached]
    if urgent:
        return urgent, True
    if len(lines) == 1 and worked:
        # One task: there is nothing to rank it against.
        return worked, True
    days: dict[int, int] = {}
    for index, line in enumerate(worked):
        projections = [limit.projected for limit in line.first]
        if line.ranked and all(projection is not None for projection in projections):
            days[index] = min(projection for projection in projections if projection is not None)
    if not days:
        return [], not worked
    soonest = min(days.values())
    complete = len(days) == len(worked) and len(worked) == len(lines)
    return [worked[index] for index, value in days.items() if value == soonest], complete


@dataclass(frozen=True)
class WorkLine:
    """One piece of work done, with the deadlines that follow from it (REQ-051, REQ-052)."""

    work: WorkDone
    release_deadline: date
    release_flag: Flag
    release_late: bool
    told_late: bool

    @property
    def workings(self) -> tuple[Working, ...]:
        """Return how each deadline that follows from the work was reached (REQ-139)."""
        work = self.work
        release = [("Completed", formatting.long_date(work.dated)), ("Days Allowed", "30")]
        if work.release_recorded_on is not None:
            release.append(
                ("Release Entered in the Records", formatting.long_date(work.release_recorded_on))
            )
        found = [
            Working(
                title=f"How the Release by {formatting.long_date(self.release_deadline)} "
                "Was Calculated",
                figure=formatting.long_date(self.release_deadline),
                rule=(
                    "The Certificate of Release to Service Is Entered in the Records No Later "
                    "Than 30 Days After the Work Is Completed"
                ),
                inputs=tuple(release),
                source="ML.A.305(a)",
            )
        ]
        if work.by_pilot_owner:
            told_by = pilot_owner_notification_deadline(work.dated)
            told = [("Completed", formatting.long_date(work.dated)), ("Days Allowed", "30")]
            if work.pilot_owner_told_on is not None:
                told.append(("Organisation Told", formatting.long_date(work.pilot_owner_told_on)))
            found.append(
                Working(
                    title=f"How Told by {formatting.long_date(told_by)} Was Calculated",
                    figure=formatting.long_date(told_by),
                    rule=(
                        "The Pilot-Owner Tells the Organisation No Later Than 30 Days After "
                        "Completing the Task"
                    ),
                    inputs=tuple(told),
                    source="Appendices I and II to Part-ML",
                )
            )
        return tuple(found)


def work_lines(aircraft: Aircraft, today: date) -> list[WorkLine]:
    """Return the work done on the aircraft, newest first, with what is outstanding."""
    lines = []
    for work in (
        WorkDone.objects.filter(aircraft=aircraft)
        .select_related("certificate")
        .order_by("-dated", "-hours")
    ):
        deadline = release_record_deadline(work.dated)
        outstanding = not work.release_reference
        told_late = (
            work.by_pilot_owner
            and work.pilot_owner_told_on is not None
            and pilot_owner_told_late(work.dated, work.pilot_owner_told_on)
        )
        lines.append(
            WorkLine(
                work=work,
                release_deadline=deadline,
                release_flag=deadline_flag(today, deadline) if outstanding else Flag.NONE,
                release_late=work.release_recorded_on is not None
                and work.release_recorded_on > deadline,
                told_late=told_late,
            )
        )
    return lines


@dataclass(frozen=True)
class ReviewLine:
    """When the programme was last reviewed and when the next review is due (REQ-053)."""

    last_reviewed: date | None
    due: date | None
    flag: Flag


def review_line(programme: Programme, today: date, thresholds: Thresholds) -> ReviewLine:
    """Return where the annual review of the programme stands, ML.A.302(c)(9)."""
    if programme.last_reviewed is None:
        return ReviewLine(None, None, Flag.NONE)
    due = programme_review_due(programme.last_reviewed)
    flag = limit_flag(Limit(Unit.CALENDAR, due, days_between(today, due)), thresholds)
    return ReviewLine(programme.last_reviewed, due, flag)


@dataclass(frozen=True)
class ProgrammeLine:
    """One aircraft of the Fleet, its programme and where the annual review stands."""

    aircraft: Aircraft
    programme: Programme | None
    tasks: int
    review: ReviewLine | None
    today: date
    # Departures from the manufacturer's instructions that are in force (REQ-284).
    departures: int = 0
    # The progress of an annual review in progress: 4 of 6 Complete (REQ-286).
    in_progress: str = ""

    @property
    def remaining(self) -> str:
        """Return what remains to the annual review: 358 Days, or 1 Day Overdue."""
        if self.review is None or self.review.due is None:
            return ""
        days = days_between(self.today, self.review.due)
        if days < 0:
            return f"{formatting.amount(Unit.CALENDAR, -days)} Overdue"
        return formatting.amount(Unit.CALENDAR, days)


def programme_lines(today: date) -> list[ProgrammeLine]:
    """Return every aircraft of the Fleet with its programme, by Aircraft Registration (REQ-283).

    An aircraft with no programme set up is listed and says so: it has
    nothing that can fall due (hazard H-018).
    """
    lines = []
    for aircraft in Aircraft.objects.filter(stage=Stage.FLEET).order_by("registration"):
        programme = Programme.objects.filter(aircraft=aircraft).first()
        if programme is None:
            lines.append(ProgrammeLine(aircraft, None, 0, None, today))
            continue
        review = review_line(programme, today, thresholds_of(aircraft.organisation))
        tasks = programme.tasks.filter(retired=False).count()
        departures = programme.departures.filter(withdrawn_on__isnull=True).count()
        opened = programme.annual_reviews.filter(completed_on__isnull=True).first()
        progress = f"Open, {opened.progress}" if opened is not None else ""
        lines.append(ProgrammeLine(aircraft, programme, tasks, review, today, departures, progress))
    return lines
