"""Get package demand, roster availability and work due outside a package."""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID

from django.urls import reverse

from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.configuration.forecast import expected_days
from airworthiness_plus.contracts.models import WorkOrder
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.programme import due
from airworthiness_plus.reviews.services import current_valid_to
from airworthiness_plus.staffing import roster
from airworthiness_plus.staffing.roster_models import Settings
from airworthiness_plus.staffing.roster_rules import week_of, workload
from airworthiness_rules.forecast import forecast_date
from airworthiness_rules.programme import Flag


@dataclass(frozen=True)
class WeekLoad:
    week: date
    packages: list[WorkPackage]
    package_hours: Decimal
    other_hours: Decimal
    available: Decimal
    percent: int | None
    warns: bool

    @property
    def status(self) -> str:
        if self.percent is None:
            return "No Roster Capacity"
        return "At or Over Warning Margin" if self.warns else "Within Margin"


@dataclass(frozen=True)
class Unplanned:
    aircraft: Aircraft
    title: str
    limit: str
    forecast: date | None
    address: str
    detail: str = ""


def weekly_loads(first: date, weeks: int, settings: Settings) -> list[WeekLoad]:
    """Allocate planned hours once to each package's planned start week."""
    end = first + timedelta(days=7 * weeks)
    packages: dict[date, list[WorkPackage]] = defaultdict(list)
    for package in WorkPackage.objects.filter(
        starts_on__gte=first, starts_on__lt=end
    ).prefetch_related("cards"):
        packages[week_of(package.starts_on)].append(package)
    rows = []
    for index in range(weeks):
        week = first + timedelta(days=index * 7)
        hours = sum(
            (
                card.planned_hours + card.inspection_hours
                for package in packages[week]
                for card in package.cards.all()
            ),
            Decimal("0.0"),
        )
        minutes = sum(
            line.minutes
            for line in roster.check_shifts(week, settings)
            if line.shift.maintenance and "Staff Absence" not in line.flags
        )
        available = Decimal(minutes) / 60
        percent, warns = workload(
            hours, settings.other_hours_weekly, available, settings.load_margin_percent
        )
        rows.append(
            WeekLoad(
                week, packages[week], hours, settings.other_hours_weekly, available, percent, warns
            )
        )
    return rows


def work_not_planned(today: date, end: date) -> list[Unplanned]:
    """Find outstanding tasks, defects and orders using their own evidence and due rules."""
    active = WorkPackage.objects.filter(released_on__isnull=True)
    orders = set(active.filter(order_id__isnull=False).values_list("order_id", flat=True))
    defects = set(active.filter(defect_id__isnull=False).values_list("defect_id", flat=True))
    cards = WorkCard.objects.filter(package__released_on__isnull=True)
    tasks: set[UUID | None] = set(cards.values_list("task_id", flat=True))
    tasks.update(cards.values_list("directive__task_id", flat=True))
    candidates = []
    for aircraft in Aircraft.objects.filter(stage=Stage.FLEET):
        for line in due.due_lines(aircraft, today, current_valid_to(aircraft)):
            if line.task.id in tasks:
                continue
            days = expected_days(line.first if line.ranked else line.limits)
            forecast = forecast_date(today, days)
            if (
                line.needs_attention
                or line.flag is not Flag.NONE
                or (forecast is not None and forecast < end)
            ):
                candidates.append(
                    Unplanned(
                        aircraft,
                        line.task.title,
                        line.remaining_summary,
                        forecast,
                        reverse("programme", args=[aircraft.pk]),
                        line.problem,
                    )
                )
    for defect in Defect.objects.filter(closed_on__isnull=True).select_related("aircraft"):
        if defect.pk not in defects and (defect.limit_on is None or defect.limit_on < end):
            candidates.append(
                Unplanned(
                    defect.aircraft,
                    defect.title,
                    "",
                    defect.limit_on,
                    reverse("defect", args=[defect.pk]),
                    str(defect.decision),
                )
            )
    for order in WorkOrder.objects.filter(closed_on__isnull=True).select_related("aircraft"):
        if order.pk not in orders:
            candidates.append(
                Unplanned(
                    order.aircraft,
                    order.work,
                    "",
                    None,
                    reverse("contracts"),
                    "Work Order Agreed",
                )
            )
    return sorted(
        candidates,
        key=lambda line: (line.forecast or date.max, line.aircraft.registration, line.title),
    )
