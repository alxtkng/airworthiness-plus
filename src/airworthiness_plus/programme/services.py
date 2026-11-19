"""What can be done to a maintenance programme. Views check the role first, then call these."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind
from airworthiness_plus.programme.models import (
    Basis,
    InspectionCategory,
    Programme,
    Task,
    WorkDone,
)
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
    programme, _ = Programme.objects.update_or_create(
        aircraft=aircraft,
        defaults={
            "organisation_id": aircraft.organisation_id,
            "basis": basis,
            "inspection_category": inspection_category
            if basis == Basis.MINIMUM_INSPECTION_PROGRAMME
            else "",
            "reference": reference,
            "hours_per_day": hours_per_day,
            "cycles_per_day": cycles_per_day,
        },
    )
    return programme


def _check_minimum_inspection(programme: Programme, interval: Interval) -> None:
    """Refuse an inspection less often than ML.A.302(d)(1) requires."""
    if programme.basis != Basis.MINIMUM_INSPECTION_PROGRAMME:
        raise RefusedError(
            "A Minimum Inspection Programme Inspection Belongs to a Programme on That Basis"
        )
    most = MINIMUM_INSPECTION_PROGRAMME_INTERVAL
    if interval.months is None or most.months is None or interval.months > most.months:
        raise RefusedError("ML.A.302(d)(1): The Inspection Is at Least Annual")
    aeroplane = programme.inspection_category == InspectionCategory.AEROPLANE
    if aeroplane and (interval.hours is None or most.hours is None or interval.hours > most.hours):
        raise RefusedError("ML.A.302(d)(1)(a): The Inspection Is at Least Every 100 Hours")


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
    """Take a task out of the programme. It and its records stay (REQ-131)."""
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


def record_release(work: WorkDone, reference: str, recorded_on: date | None = None) -> None:
    """Record that the certificate of release to service is in the records (REQ-051)."""
    if not reference:
        raise RefusedError("A Release Has a Reference")
    work.release_reference = reference
    work.release_recorded_on = recorded_on or aircraft_services.today()
    work.save(update_fields=["release_reference", "release_recorded_on"])


def record_review(programme: Programme, reviewed_on: date) -> None:
    """Record the annual review of the programme, ML.A.302(c)(9) (REQ-053)."""
    if reviewed_on > aircraft_services.today():
        raise RefusedError("A Review Cannot Be Dated After Today")
    programme.last_reviewed = reviewed_on
    programme.save(update_fields=["last_reviewed"])
