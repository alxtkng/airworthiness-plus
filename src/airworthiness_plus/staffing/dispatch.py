"""Dispatch scheduling, conflict checks and remaining work."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef, Q, QuerySet

from airworthiness_plus.accounts.models import User
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.staffing import roster
from airworthiness_plus.staffing.dispatch_models import DispatchAssignment, DispatchWindow
from airworthiness_plus.staffing.roster_models import Shift
from airworthiness_plus.staffing.roster_rules import active_minutes, gap_minutes, week_of
from airworthiness_plus.staffing.services import RefusedError


def current_assignments() -> QuerySet[DispatchAssignment]:
    return DispatchAssignment.objects.filter(
        ~Exists(DispatchAssignment.objects.filter(supersedes_id=OuterRef("pk")))
    )


def shift_label(shift: Shift) -> str:
    start = shift.starts_at.astimezone(roster.LONDON).strftime("%d %b %H:%M")
    return f"{shift.person} · {shift.shift_name}, {shift.area} · {start}"


@transaction.atomic
def assign(
    *,
    actor: User,
    card: WorkCard,
    shift: Shift,
    starts_at: datetime,
    ends_at: datetime,
    reason: str,
    previous: DispatchAssignment | None = None,
) -> DispatchAssignment:
    organisation = actor.organisation_id
    Organisation.objects.select_for_update(no_key=True).only("pk").get(pk=organisation)
    if card.organisation_id != organisation or shift.organisation_id != organisation:
        raise RefusedError("Choose a Work Card and Shift in This Organisation")
    shift = Shift.objects.get(pk=shift.pk)
    package = WorkPackage.objects.select_for_update(no_key=True).get(pk=card.package_id)
    card = WorkCard.objects.get(pk=card.pk)
    if not shift.maintenance:
        raise RefusedError("Choose a Maintenance Shift")
    _check_window(shift, starts_at, ends_at)
    if not reason.strip() or card.signed or package.released_on is not None:
        raise RefusedError("Choose Unfinished Work and Give a Planning or Change Reason")
    current = current_assignments().filter(organisation_id=organisation, card=card).first()
    if current != previous:
        raise RefusedError("The Assignment Has Changed. Return to Dispatch and Review It.")
    return DispatchAssignment.objects.create(
        organisation_id=organisation,
        card=card,
        shift=shift,
        starts_at=starts_at,
        ends_at=ends_at,
        reason=reason.strip(),
        supersedes=previous,
    )


def _check_window(shift: Shift, starts_at: datetime, ends_at: datetime) -> None:
    if shift.withdrawn_on or not shift.starts_at <= starts_at < ends_at <= shift.ends_at:
        raise RefusedError("Enter Times Within the Active Roster Shift")


@transaction.atomic
def add_window(
    *,
    actor: User,
    starts_at: datetime,
    ends_at: datetime,
    note: str,
    shift: Shift | None = None,
    package: WorkPackage | None = None,
) -> DispatchWindow:
    organisation = actor.organisation_id
    Organisation.objects.select_for_update(no_key=True).only("pk").get(pk=organisation)
    scope = shift or package
    if scope is None or scope.organisation_id != organisation or (shift and package):
        raise RefusedError("Choose a Shift or Work Package in This Organisation")
    if ends_at <= starts_at or not note.strip():
        raise RefusedError("Enter an End After the Start and Give a Window Note")
    if shift is not None:
        _check_window(Shift.objects.get(pk=shift.pk), starts_at, ends_at)
    return DispatchWindow.objects.create(
        organisation_id=organisation,
        shift=shift,
        package=package,
        starts_at=starts_at,
        ends_at=ends_at,
        note=note.strip(),
    )


def remaining(card: WorkCard) -> str:
    if card.completed_on is None:
        return (
            "Maintenance and independent inspection outstanding"
            if card.critical
            else ("Maintenance outstanding")
        )
    if card.critical and card.inspected_on is None:
        return "Independent inspection outstanding"
    return "Complete"


def _overlap(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < other_end and other_start < end


def _warnings(
    assignment: DispatchAssignment,
    assignments: list[DispatchAssignment],
    breaks: list[DispatchWindow],
    turnarounds: list[DispatchWindow],
    fatigue: tuple[str, ...],
    critical_first_half: bool,
) -> list[str]:
    start, end = assignment.starts_at, assignment.ends_at
    warnings = list(fatigue)
    shift = assignment.shift
    if critical_first_half and assignment.card.critical and assignment.card.completed_on is None:
        working_minutes = active_minutes(shift.starts_at, shift.ends_at, shift.break_minutes)
        if 2 * gap_minutes(shift.starts_at, start) >= working_minutes:
            warnings.append("Critical maintenance assigned after the first half of the shift")
    if shift.withdrawn_on:
        warnings.append("Roster shift withdrawn")
    if any(_overlap(start, end, item.starts_at, item.ends_at) for item in breaks):
        warnings.append("Overlaps a recorded break")
    for item in assignments:
        if item != assignment and _overlap(start, end, item.starts_at, item.ends_at):
            warnings.append(f"Overlaps assignment {item.card.package} · {item.card}")
    if turnarounds and not any(
        item.starts_at <= start and end <= item.ends_at for item in turnarounds
    ):
        warnings.append("Outside the recorded turnaround windows")
    return warnings


@dataclass(frozen=True)
class Event:
    label: str
    starts_at: datetime
    ends_at: datetime


@dataclass(frozen=True)
class Day:
    shifts: list[Shift]
    assignments: list[tuple[DispatchAssignment, list[str], str]]
    history: list[DispatchAssignment]
    windows: list[DispatchWindow]
    slots: list[datetime]
    timeline: list[tuple[Event, list[bool]]]


def _day_timings(day: date) -> tuple[datetime, datetime]:
    return (
        roster.midnight(day).astimezone(UTC),
        roster.midnight(day + timedelta(days=1)).astimezone(UTC),
    )


def _day_slots(start: datetime, end: datetime) -> list[datetime]:
    return [
        start + timedelta(hours=offset) for offset in range(0, gap_minutes(start, end) // 60, 2)
    ]


def day_board(day: date, organisation: Organisation) -> Day:
    start, end = _day_timings(day)
    during_day = Q(starts_at__lt=end, ends_at__gt=start)
    shifts = list(
        Shift.objects.filter(
            during_day, organisation=organisation, withdrawn_on__isnull=True
        ).select_related("person")
    )
    current = current_assignments().filter(organisation=organisation)
    active = list(current.filter(during_day).select_related("shift__person", "card__package"))
    # Include conflicts beyond midnight for rows whose assignments touch the selected day.
    window_start = min([start, *(item.starts_at for item in active)])
    window_end = max([end, *(item.ends_at for item in active)])
    vicinity = Q(starts_at__lt=window_end, ends_at__gt=window_start)
    by_person = defaultdict(list)
    for item in current.filter(
        vicinity, shift__person_id__in=[row.shift.person_id for row in active]
    ).select_related("shift", "card__package"):
        by_person[item.shift.person_id].append(item)
    windows = list(
        DispatchWindow.objects.filter(
            Q(vicinity, shift__withdrawn_on__isnull=True)
            | Q(package_id__in={item.card.package_id for item in active}),
            organisation=organisation,
        ).select_related("shift__person", "package")
    )
    breaks: dict[object, list[DispatchWindow]] = defaultdict(list)
    turnarounds: dict[object, list[DispatchWindow]] = defaultdict(list)
    for window in windows:
        if window.shift is not None:
            breaks[window.shift.person_id].append(window)
        else:
            turnarounds[window.package_id].append(window)
    settings = roster.settings_for(organisation)
    weeks = {
        week_of(day),
        *(week_of(roster.local_day(item.starts_at)) for item in active),
        *(week_of(roster.local_day(item.ends_at - timedelta(microseconds=1))) for item in active),
    }
    fatigue: dict[object, tuple[str, ...]] = {}
    for week in sorted(weeks):
        for line in roster.check_shifts(week, settings):
            fatigue[line.shift.pk] = tuple(
                dict.fromkeys(fatigue.get(line.shift.pk, ()) + line.flags)
            )
    rows = [
        (
            item,
            _warnings(
                item,
                by_person[item.shift.person_id],
                breaks[item.shift.person_id],
                turnarounds[item.card.package_id],
                fatigue.get(item.shift_id, ()),
                settings.critical_first_half,
            ),
            remaining(item.card),
        )
        for item in active
    ]
    history = list(
        DispatchAssignment.objects.filter(
            Q(during_day) | Q(card_id__in={item.card_id for item in active}),
            organisation=organisation,
            replacement__isnull=False,
        ).select_related("shift__person", "card__package", "replacement__shift__person")
    )
    day_windows = [item for item in windows if _overlap(start, end, item.starts_at, item.ends_at)]
    events = (
        [
            Event(f"Shift · {shift.person} · {shift.shift_name}", shift.starts_at, shift.ends_at)
            for shift in shifts
        ]
        + [
            Event(f"Assignment · {item.card.package} · {item.card}", item.starts_at, item.ends_at)
            for item in active
        ]
        + [
            Event(
                f"Break · {item.shift.person}"
                if item.shift is not None
                else f"Turnaround · {item.package}",
                item.starts_at,
                item.ends_at,
            )
            for item in day_windows
        ]
    )
    slots = _day_slots(start, end)
    timeline = [
        (
            event,
            [
                _overlap(slot, min(slot + timedelta(hours=2), end), event.starts_at, event.ends_at)
                for slot in slots
            ],
        )
        for event in sorted(events, key=lambda item: (item.starts_at, item.ends_at, item.label))
    ]
    return Day(shifts, rows, history, day_windows, slots, timeline)
