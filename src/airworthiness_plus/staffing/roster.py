"""Roster writes and the fatigue checks for a published week."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from itertools import pairwise
from zoneinfo import ZoneInfo

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation, Privilege
from airworthiness_plus.people.models import Employment, Person
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.staffing.models import Absence
from airworthiness_plus.staffing.roster_models import (
    Handover,
    PublishedRoster,
    PublishedShift,
    Settings,
    Shift,
)
from airworthiness_plus.staffing.roster_rules import (
    active_minutes,
    employed_share,
    gap_minutes,
    minutes_in_window,
    week_of,
)
from airworthiness_plus.staffing.services import RefusedError

LONDON = ZoneInfo("Europe/London")


def local_day(stamp: datetime) -> date:
    return stamp.astimezone(LONDON).date()


def midnight(day: date) -> datetime:
    return datetime.combine(day, time.min, LONDON)


def settings_for(organisation: Organisation) -> Settings:
    return Settings.objects.filter(organisation=organisation).first() or Settings(
        organisation=organisation
    )


def shifts_between(start: date, end: date) -> list[Shift]:
    return list(
        Shift.objects.filter(
            starts_at__gte=midnight(start),
            starts_at__lt=midnight(end + timedelta(days=1)),
            withdrawn_on__isnull=True,
        )
        .select_related("person", "approval")
        .order_by("starts_at", "pk")
    )


@transaction.atomic
def add_shift(
    *,
    actor: User,
    approval: Approval,
    person: Person,
    area: str,
    shift_name: str,
    starts_at: datetime,
    ends_at: datetime,
    break_minutes: int,
    other_minutes: int,
    maintenance: bool = False,
    critical_at: datetime | None = None,
    mitigation: str = "",
    permission: str = "",
) -> Shift:
    Organisation.objects.select_for_update(no_key=True).only("id").get(pk=actor.organisation_id)
    person = Person.objects.select_for_update(no_key=True).get(pk=person.pk)
    start_day = local_day(starts_at)
    end_day = local_day(ends_at - timedelta(microseconds=1))
    if (
        person.organisation_id != actor.organisation_id
        or approval.organisation_id != actor.organisation_id
        or not (approval.held_on(start_day) and approval.held_on(end_day))
    ):
        raise RefusedError("Choose Staff and an Approval of This Organisation")
    if (person.joined_on and start_day < person.joined_on) or (
        person.left_on and end_day > person.left_on
    ):
        raise RefusedError("The Person Must Be With the Organisation Throughout the Shift")
    if maintenance and not (
        approval.approval == ApprovalType.PART_145
        or (
            approval.approval == ApprovalType.PART_CAO
            and Privilege.MAINTENANCE in actor.organisation.privileges
        )
    ):
        raise RefusedError("The Shift Needs an Approval Covering Maintenance")
    minutes = gap_minutes(starts_at, ends_at)
    if not 0 <= break_minutes < minutes <= 1440 or not 0 <= other_minutes <= 1440:
        raise RefusedError("Enter a Shift of Up to 24 Hours With a Shorter Break")
    if critical_at is not None and not starts_at <= critical_at < ends_at:
        raise RefusedError("The Critical Task Time Belongs Within the Shift")
    if not area.strip() or not shift_name.strip():
        raise RefusedError("Give the Area and Shift")
    if Shift.objects.filter(
        person=person,
        withdrawn_on__isnull=True,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
    ).exists():
        raise RefusedError("This Person Already Has a Shift at That Time")
    return Shift.objects.create(
        organisation_id=actor.organisation_id,
        approval=approval,
        person=person,
        area=area.strip(),
        shift_name=shift_name.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        break_minutes=break_minutes,
        other_minutes=other_minutes,
        maintenance=maintenance,
        critical_at=critical_at,
        mitigation=mitigation.strip(),
        permission=permission.strip(),
    )


@transaction.atomic
def withdraw_shift(shift: Shift, *, actor: User, reason: str) -> None:
    Organisation.objects.select_for_update(no_key=True).only("id").get(pk=actor.organisation_id)
    shift = Shift.objects.select_for_update().get(pk=shift.pk)
    reason = reason.strip()
    if shift.organisation_id != actor.organisation_id or shift.withdrawn_on or not reason:
        raise RefusedError("Give a Reason for Withdrawing an Active Shift")
    shift.withdrawn_on = aircraft_services.today()
    shift.withdrawal_reason = reason
    shift.save(update_fields=["withdrawn_on", "withdrawal_reason"])


@transaction.atomic
def publish(*, actor: User, week: date, note: str) -> PublishedRoster:
    Organisation.objects.select_for_update().only("id").get(pk=actor.organisation_id)
    if week != week_of(week) or not note.strip():
        raise RefusedError("Choose the Monday of the Roster Week and Record the Agreement")
    previous = PublishedRoster.objects.filter(week=week, replacement__isnull=True).first()
    publication = PublishedRoster.objects.create(
        organisation_id=actor.organisation_id,
        week=week,
        published_on=aircraft_services.today(),
        published_by=actor,
        note=note.strip(),
        supersedes=previous,
    )

    PublishedShift.objects.bulk_create(
        [
            PublishedShift(
                organisation_id=actor.organisation_id, publication=publication, shift=shift
            )
            for shift in shifts_between(week, week + timedelta(days=6))
        ]
    )
    return publication


@transaction.atomic
def record_handover(
    *,
    actor: User,
    package: WorkPackage | None,
    outgoing: Person,
    incoming: Person,
    handed_at: datetime,
    stage: str,
    parts: str,
    card: WorkCard | None = None,
) -> Handover:
    if outgoing.pk == incoming.pk or not stage.strip() or not parts.strip():
        raise RefusedError("Name Two People and Record the Stage, Work, Parts and Warnings")
    if handed_at > timezone.now():
        raise RefusedError("A Handover Cannot Be Dated After Now")
    organisation = actor.organisation_id
    if (
        outgoing.organisation_id != organisation
        or incoming.organisation_id != organisation
        or (package is not None and package.organisation_id != organisation)
        or (card is not None and card.organisation_id != organisation)
    ):
        raise RefusedError("The Handover Belongs to This Organisation")
    if card is not None:
        if package is not None and card.package_id != package.pk:
            raise RefusedError("Choose a Work Card in the Handover Work Package")
        package = card.package
    shifts = list(
        Shift.objects.filter(
            person__in=[incoming, outgoing],
            starts_at__lte=handed_at,
            ends_at__gte=handed_at,
            withdrawn_on__isnull=True,
        )
    )
    ends = [shift.ends_at for shift in shifts]
    starts = [shift.starts_at for shift in shifts]
    overlap = max(0, gap_minutes(max(starts), min(ends))) if len(shifts) == 2 else None
    settings = settings_for(actor.organisation)
    return Handover.objects.create(
        organisation_id=organisation,
        package=package,
        card=card,
        outgoing=outgoing,
        incoming=incoming,
        handed_at=handed_at,
        stage=stage.strip(),
        parts=parts.strip(),
        overlap=overlap,
        overlap_target=settings.overlap_minutes,
    )


@transaction.atomic
def acknowledge(handover: Handover, actor: User) -> None:
    handover = Handover.objects.select_for_update().get(pk=handover.pk)
    if handover.incoming.user_id != actor.id or handover.acknowledged_at is not None:
        raise RefusedError("The Incoming Person Acknowledges the Handover Once")
    handover.acknowledged_at = timezone.now()
    handover.actor = actor
    handover.save(update_fields=["acknowledged_at", "actor"])


@dataclass(frozen=True)
class CheckedShift:
    shift: Shift
    minutes: int
    minutes_this_week: int
    rest: int | None
    weekly_minutes: int
    flags: tuple[str, ...]

    @property
    def available(self) -> bool:
        return not any(
            flag in self.flags
            for flag in ("Staff Absence", "Staff Unavailable", "Approval Unavailable")
        )

    @property
    def hours(self) -> Decimal:
        return (Decimal(self.minutes) / 60).quantize(Decimal("0.01"))


@dataclass(frozen=True)
class Crew:
    date: date
    area: str
    name: str
    starts: datetime
    ends: datetime
    employed: int
    contracted: int
    percent: int | None
    below_half: bool
    permissions: tuple[str, ...]


def check_shifts(week: date, settings: Settings) -> list[CheckedShift]:
    sunday = week + timedelta(days=6)
    previous_day = week - timedelta(days=1)
    # A shift that starts the day before the rest window can end inside it.
    preceding = 1 + max(1, (settings.minimum_rest_minutes + 1439) // 1440)
    shifts = shifts_between(week - timedelta(days=preceding), sunday)
    week_start, week_end = midnight(week), midnight(sunday + timedelta(days=1))
    totals: dict[object, int] = defaultdict(int)
    minutes: dict[object, int] = {}
    for shift in shifts:
        if shift.ends_at <= week_start:
            continue
        minutes[shift.pk] = minutes_in_window(
            shift.starts_at, shift.ends_at, shift.break_minutes, week_start, week_end
        )
        totals[shift.person_id] += minutes[shift.pk]
        if shift.starts_at >= week_start:
            totals[shift.person_id] += shift.other_minutes
    absences: dict[object, list[Absence]] = defaultdict(list)
    for absence in Absence.objects.filter(
        starts_on__lte=sunday + timedelta(days=1), ends_on__gte=previous_day
    ):
        absences[absence.person_id].append(absence)
    latest: dict[object, datetime] = {}
    checked: list[CheckedShift] = []
    for shift in shifts:
        on = local_day(shift.starts_at)
        prior = latest.get(shift.person_id)
        latest[shift.person_id] = shift.ends_at
        if shift.pk not in minutes:
            continue
        rest = gap_minutes(prior, shift.starts_at) if prior is not None else None
        active = active_minutes(shift.starts_at, shift.ends_at, shift.break_minutes)
        flags = []
        end_day = local_day(shift.ends_at - timedelta(microseconds=1))
        if (shift.person.joined_on and on < shift.person.joined_on) or (
            shift.person.left_on and end_day > shift.person.left_on
        ):
            flags.append("Staff Unavailable")
        if not (shift.approval.held_on(on) and shift.approval.held_on(end_day)):
            flags.append("Approval Unavailable")
        if active > settings.maximum_shift_minutes:
            flags.append("Long Shift")
        if rest is not None and rest < settings.minimum_rest_minutes:
            flags.append("Short Rest")
        if totals[shift.person_id] > settings.maximum_week_minutes:
            flags.append("Weekly Limit Exceeded")
        if (
            settings.critical_first_half
            and shift.critical_at is not None
            and 2 * gap_minutes(shift.starts_at, shift.critical_at) >= active
        ):
            flags.append("Critical Task After the First Half")
        if any(
            absence.starts_on <= local_day(shift.ends_at - timedelta(microseconds=1))
            and absence.ends_on >= on
            for absence in absences[shift.person_id]
        ):
            flags.append("Staff Absence")
        checked.append(
            CheckedShift(
                shift, active, minutes[shift.pk], rest, totals[shift.person_id], tuple(flags)
            )
        )
    return checked


def crews(shifts: list[CheckedShift]) -> list[Crew]:
    groups: dict[tuple[date, str, str], list[CheckedShift]] = defaultdict(list)
    for line in shifts:
        shift = line.shift
        if shift.approval.approval == ApprovalType.PART_145 and shift.maintenance:
            key = local_day(shift.starts_at), shift.area.casefold(), shift.shift_name.casefold()
            groups[key].append(line)
    result = []
    for (day, _, _), group in sorted(groups.items()):
        boundaries = sorted(
            {stamp for line in group for stamp in (line.shift.starts_at, line.shift.ends_at)}
        )
        for start, end in pairwise(boundaries):
            scheduled = [
                line for line in group if line.shift.starts_at <= start < line.shift.ends_at
            ]
            if not scheduled:
                continue
            people = [line.shift for line in scheduled if line.available]
            employed = sum(shift.person.employment == Employment.EMPLOYED for shift in people)
            contracted = sum(shift.person.employment == Employment.CONTRACTED for shift in people)
            percent, below = employed_share(employed, contracted)
            permission = tuple(sorted({shift.permission for shift in people if shift.permission}))
            first = scheduled[0].shift
            result.append(
                Crew(
                    day,
                    first.area,
                    first.shift_name,
                    start,
                    end,
                    employed,
                    contracted,
                    percent,
                    below,
                    permission,
                )
            )
    return result


def handovers_for(week: date) -> list[Handover]:
    return list(
        Handover.objects.filter(
            Q(handed_at__gte=midnight(week), handed_at__lt=midnight(week + timedelta(days=7)))
            | Q(acknowledged_at__isnull=True)
        ).select_related("incoming", "outgoing", "package", "card", "actor")
    )
