"""What can be done to a maintenance programme. Views check the role first, then call these."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind
from airworthiness_plus.programme.models import (
    REVIEW_POINTS,
    AnnualReview,
    Basis,
    Departure,
    InspectionCategory,
    Programme,
    Task,
    WorkDone,
)
from airworthiness_rules.dates import BeyondCalendarError, add_days, add_months
from airworthiness_rules.intervals import (
    MINIMUM_INSPECTION_PROGRAMME_INTERVAL,
    Interval,
    Reading,
    TaskKind,
)


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def set_up_programme(
    aircraft: Aircraft,
    *,
    basis: Basis,
    reference: str,
    inspection_category: str = "",
    hours_per_day: Decimal | None = None,
    cycles_per_day: Decimal | None = None,
) -> Programme:
    """Record the aircraft's one programme, or change it (REQ-040, AMC1 ML.A.302)."""
    if basis == Basis.MINIMUM_INSPECTION_PROGRAMME and not inspection_category:
        raise RefusedError("A Minimum Inspection Programme Says Which Aircraft It Is For")
    if basis != Basis.MINIMUM_INSPECTION_PROGRAMME:
        inspection_category = ""
    _check_inspections_still_agree(aircraft, basis, inspection_category)
    programme, _ = Programme.objects.update_or_create(
        aircraft=aircraft,
        defaults={
            "organisation_id": aircraft.organisation_id,
            "basis": basis,
            "inspection_category": inspection_category,
            "reference": reference,
            "hours_per_day": hours_per_day,
            "cycles_per_day": cycles_per_day,
        },
    )
    return programme


def _check_inspections_still_agree(aircraft: Aircraft, basis: Basis, category: str) -> None:
    """Refuse a change of programme that its live inspections do not agree with.

    What ``add_task`` refuses for a new inspection of the Minimum
    Inspection Programme is refused here for the ones already there, so the
    programme cannot be changed under them (ML.A.302(d)(1)).
    """
    inspections = Task.objects.filter(
        programme__aircraft=aircraft,
        kind=TaskKind.MINIMUM_INSPECTION_PROGRAMME.value,
        retired=False,
    )
    for inspection in inspections:
        if basis != Basis.MINIMUM_INSPECTION_PROGRAMME:
            raise RefusedError(
                "The Programme Has Minimum Inspection Programme Inspections: "
                "Retire Its Inspections Before Changing What It Is Based On"
            )
        _check_minimum_inspection_interval(category, inspection.interval)


def _check_minimum_inspection(programme: Programme, interval: Interval) -> None:
    """Refuse an inspection less often than ML.A.302(d)(1) requires."""
    if programme.basis != Basis.MINIMUM_INSPECTION_PROGRAMME:
        raise RefusedError(
            "A Minimum Inspection Programme Inspection Belongs to a Programme on That Basis"
        )
    _check_minimum_inspection_interval(programme.inspection_category, interval)


def _check_minimum_inspection_interval(category: str, interval: Interval) -> None:
    most = MINIMUM_INSPECTION_PROGRAMME_INTERVAL
    if interval.months is None or most.months is None or interval.months > most.months:
        raise RefusedError("ML.A.302(d)(1): The Inspection Is at Least Annual")
    aeroplane = category == InspectionCategory.AEROPLANE
    if aeroplane and (interval.hours is None or most.hours is None or interval.hours > most.hours):
        raise RefusedError("ML.A.302(d)(1)(a): The Inspection Is at Least Every 100 Hours")


def check_calendar(*intervals: Interval | None) -> None:
    """Refuse a calendar interval so long that no date can be given for it."""
    today = aircraft_services.today()
    for interval in intervals:
        if interval is None:
            continue
        try:
            if interval.months is not None:
                add_months(today, interval.months)
            if interval.days is not None:
                add_days(today, interval.days)
        except BeyondCalendarError as error:
            raise RefusedError("The Interval Runs Past 31 December 9999") from error


def add_task(
    programme: Programme,
    *,
    title: str,
    kind: TaskKind,
    counter: Counter,
    source: str,
    interval: Interval,
    first: Interval | None = None,
    starts: Reading | None = None,
) -> Task:
    """Add a task to the programme (REQ-041, REQ-058, REQ-059).

    ``counter`` is what the task runs against: the airframe, an engine or a
    propeller of this aircraft. ``starts`` is where the count begins for a
    task never yet done here, and ``first`` a first threshold if it differs
    from the repeat interval.
    """
    if kind is TaskKind.AIRWORTHINESS_DIRECTIVE:
        raise RefusedError("An Airworthiness Directive Is Recorded Under Airworthiness Directives")
    check_calendar(interval, first)
    if counter.aircraft_id != programme.aircraft_id:
        raise RefusedError("The Counter Belongs to Another Aircraft")
    if kind is TaskKind.MINIMUM_INSPECTION_PROGRAMME:
        _check_minimum_inspection(programme, interval)
    return Task.objects.create(
        organisation_id=programme.organisation_id,
        programme=programme,
        title=title,
        kind=kind.value,
        counter=counter,
        source=source,
        interval_hours=interval.hours,
        interval_cycles=interval.cycles,
        interval_months=interval.months,
        interval_days=interval.days,
        first_hours=first.hours if first else None,
        first_cycles=first.cycles if first else None,
        first_months=first.months if first else None,
        first_days=first.days if first else None,
        starts_dated=starts.on if starts else None,
        starts_hours=starts.hours if starts else None,
        starts_cycles=starts.cycles if starts else None,
    )


def retire_task(task: Task) -> None:
    """Take a task out of the programme. It and its records stay (REQ-131).

    The task of an airworthiness directive is refused: it ends when the
    directive is decided Not Applicable or a terminating action is recorded
    (REQ-066), so that what is due never leaves the Fleet without a record
    of why.
    """
    if task.task_kind is TaskKind.AIRWORTHINESS_DIRECTIVE:
        raise RefusedError(
            "The Task of an Airworthiness Directive Ends Under Airworthiness Directives"
        )
    end_task(task)


def end_task(task: Task) -> None:
    """Mark a task as no longer in the programme. Callers decide whether it may end."""
    task.retired = True
    task.save(update_fields=["retired"])


@transaction.atomic
def record_work(
    aircraft: Aircraft,
    *,
    description: str,
    dated: date,
    hours: Decimal,
    cycles: int,
    task: Task | None = None,
    release_reference: str = "",
    release_recorded_on: date | None = None,
    by_pilot_owner: bool = False,
    pilot_owner_told_on: date | None = None,
) -> WorkDone:
    """Record work done: a task of the programme, or other maintenance (REQ-050).

    The hours and cycles are those of the task's counter, or of the
    airframe, when the work was completed. They cannot be above what that
    counter now reads, nor below the last time the task was done.
    """
    today = aircraft_services.today()
    if dated > today:
        raise RefusedError("Work Cannot Be Completed After Today")
    if task is not None and task.programme.aircraft_id != aircraft.id:
        raise RefusedError("The Task Belongs to Another Aircraft")
    counter = task.counter if task else aircraft.counters.filter(kind=CounterKind.AIRFRAME).first()
    current = aircraft_services.current_reading(counter) if counter else None
    if current is not None and (hours > current.hours or cycles > current.cycles):
        raise RefusedError("Above the Hours or Cycles Now Recorded for the Counter")
    if task is not None:
        last = task.work_done.order_by("dated", "hours").last()
        if last is not None and (dated < last.dated or hours < last.hours or cycles < last.cycles):
            raise RefusedError("Before the Last Time This Task Was Done")
    if release_reference and release_recorded_on is None:
        release_recorded_on = today
    if release_recorded_on is not None and not dated <= release_recorded_on <= today:
        raise RefusedError(
            "A Release Is Entered in the Records On or After the Day of the Work, "
            "and Not After Today"
        )
    return WorkDone.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        task=task,
        description=description,
        dated=dated,
        hours=hours,
        cycles=cycles,
        release_reference=release_reference,
        release_recorded_on=release_recorded_on if release_reference else None,
        by_pilot_owner=by_pilot_owner,
        pilot_owner_told_on=pilot_owner_told_on if by_pilot_owner else None,
    )


@transaction.atomic
def record_release(work: WorkDone, reference: str, recorded_on: date | None = None) -> None:
    """Record that the certificate of release to service is in the records (REQ-051)."""
    if not reference:
        raise RefusedError("A Release Has a Reference")
    saved = WorkDone.objects.select_for_update().get(pk=work.pk)
    if saved.release_reference:
        raise RefusedError("A Release Is Already Recorded for This Work")
    recorded_on = recorded_on or aircraft_services.today()
    if not saved.dated <= recorded_on <= aircraft_services.today():
        raise RefusedError("A Release Is Entered Between the Day of the Work and Today")
    work.release_reference = reference
    work.release_recorded_on = recorded_on
    work.save(update_fields=["release_reference", "release_recorded_on"])


@transaction.atomic
def record_review(programme: Programme, reviewed_on: date) -> None:
    """Record the annual review of the programme, ML.A.302(c)(9) (REQ-053)."""
    if reviewed_on > aircraft_services.today():
        raise RefusedError("A Review Cannot Be Dated After Today")
    latest = Programme.objects.select_for_update().get(pk=programme.pk).last_reviewed
    if latest is not None and reviewed_on < latest:
        raise RefusedError("A Review Is Not Dated Before the Last Review Recorded")
    programme.last_reviewed = reviewed_on
    programme.save(update_fields=["last_reviewed"])


@transaction.atomic
def add_departure(
    programme: Programme,
    *,
    task: str,
    manufacturer: str,
    programme_says: str,
    compensating_measures: str,
    justification: str,
    recorded_on: date,
    owner_copy_sent_on: date | None = None,
) -> Departure:
    """Record a departure from the design approval holder's recommendations (REQ-284).

    ML.A.302(c)(8): the organisation keeps the justification for each. A
    departure for the same task that is still in force is refused, so the
    same form sent twice is recorded once.
    """
    today = aircraft_services.today()
    values = {
        "task": task.strip(),
        "manufacturer": manufacturer.strip(),
        "programme_says": programme_says.strip(),
        "compensating_measures": compensating_measures.strip(),
        "justification": justification.strip(),
    }
    if not all(values.values()):
        raise RefusedError(
            "A Departure Says the Task, What the Manufacturer Recommends, What the Programme "
            "Says, the Compensating Measures and the Justification, ML.A.302(c)(8)"
        )
    if recorded_on > today:
        raise RefusedError("A Departure Is Not Recorded After Today")
    if owner_copy_sent_on is not None and not recorded_on <= owner_copy_sent_on <= today:
        raise RefusedError(
            "The Owner Copy Is Sent on or After the Day Recorded, and Not After Today"
        )
    programme = Programme.objects.select_for_update().get(pk=programme.pk)
    if Departure.objects.filter(
        programme=programme, task=values["task"], withdrawn_on__isnull=True
    ).exists():
        raise RefusedError("A Departure for This Task Is Already Recorded")
    return Departure.objects.create(
        organisation_id=programme.organisation_id,
        programme=programme,
        recorded_on=recorded_on,
        owner_copy_sent_on=owner_copy_sent_on,
        **values,
    )


def _dated_once(departure: Departure, field: str, on: date, already: str) -> Departure:
    departure = Departure.objects.select_for_update().get(pk=departure.pk)
    if getattr(departure, field) is not None:
        raise RefusedError(already)
    if on > aircraft_services.today():
        raise RefusedError("The Day Is Not After Today")
    if on < departure.recorded_on:
        raise RefusedError("The Day Is Not Before the Departure Was Recorded")
    setattr(departure, field, on)
    departure.save(update_fields=[field])
    return departure


@transaction.atomic
def departure_copy_sent(departure: Departure, sent_on: date) -> Departure:
    """Record the day a copy of a departure went to the owner, once (REQ-285)."""
    return _dated_once(
        departure, "owner_copy_sent_on", sent_on, "The Owner Copy Is Already Recorded as Sent"
    )


@transaction.atomic
def withdraw_departure(departure: Departure, withdrawn_on: date) -> Departure:
    """Record that a departure no longer stands, once (REQ-285). It stays in the record."""
    return _dated_once(departure, "withdrawn_on", withdrawn_on, "This Departure Is Withdrawn")


def departures_in_force(programme: Programme) -> list[Departure]:
    """Return the departures of a programme that have not been withdrawn."""
    return list(Departure.objects.filter(programme=programme, withdrawn_on__isnull=True))


def open_annual_review(programme: Programme) -> AnnualReview | None:
    """Return the annual review of a programme that is in progress, if there is one."""
    return AnnualReview.objects.filter(programme=programme, completed_on__isnull=True).first()


@transaction.atomic
def start_annual_review(programme: Programme, opened_on: date | None = None) -> AnnualReview:
    """Open the annual review of a programme (REQ-286). One at a time."""
    today = aircraft_services.today()
    opened_on = opened_on or today
    if opened_on > today:
        raise RefusedError("A Review Is Not Opened After Today")
    programme = Programme.objects.select_for_update().get(pk=programme.pk)
    if open_annual_review(programme) is not None:
        raise RefusedError("An Annual Review Is Already in Progress")
    return AnnualReview.objects.create(
        organisation_id=programme.organisation_id, programme=programme, opened_on=opened_on
    )


@transaction.atomic
def note_annual_review(review: AnnualReview, **points: object) -> AnnualReview:
    """Record what was found on each point of an annual review in progress (REQ-286).

    ``points`` holds, for each point given, its note and whether it is
    complete. A point that is complete says what was found.
    """
    review = AnnualReview.objects.select_for_update().get(pk=review.pk)
    if review.completed_on is not None:
        raise RefusedError("A Completed Annual Review Is Never Altered")
    changed = []
    for name, label, _ in REVIEW_POINTS:
        note = str(points.get(f"{name}_note", getattr(review, f"{name}_note")) or "").strip()
        done = bool(points.get(f"{name}_done", getattr(review, f"{name}_done")))
        if done and not note:
            raise RefusedError(f"{label}: A Point That Is Complete Says What Was Found")
        for field, value in ((f"{name}_note", note), (f"{name}_done", done)):
            if getattr(review, field) != value:
                setattr(review, field, value)
                changed.append(field)
    if changed:
        review.save(update_fields=changed)
    return review


@transaction.atomic
def complete_annual_review(review: AnnualReview, *, by: User, completed_on: date) -> AnnualReview:
    """Complete the annual review, and record the programme as reviewed (REQ-287).

    Ours: not while a point is still open. Once: a second submit is refused.
    """
    review = AnnualReview.objects.select_for_update().get(pk=review.pk)
    if review.completed_on is not None:
        raise RefusedError("This Annual Review Is Already Completed")
    waiting = [label for _, label, _, _, done in review.points if not done]
    if waiting:
        raise RefusedError("Not Complete: " + "; ".join(waiting))
    if completed_on < review.opened_on:
        raise RefusedError("A Review Is Not Completed Before It Was Opened")
    programme = Programme.objects.select_for_update().get(pk=review.programme_id)
    if programme.last_reviewed is not None and completed_on < programme.last_reviewed:
        raise RefusedError("A Review Is Not Completed Before the Last Review Recorded")
    record_review(programme, completed_on)
    review.completed_on = completed_on
    review.completed_by = by
    review.save(update_fields=["completed_on", "completed_by"])
    # The name of whoever completed it is written by the database, as it stands.
    review.refresh_from_db(fields=["completed_by_name"])
    return review
