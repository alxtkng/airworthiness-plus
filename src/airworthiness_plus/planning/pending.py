"""Work packages with signed cards and a release still to be entered."""

from dataclasses import dataclass
from datetime import date

from django.db.models import Count, Max, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_rules.programme import Flag, deadline_flag
from airworthiness_rules.records import release_record_deadline


@dataclass(frozen=True)
class PendingRelease:
    package: WorkPackage
    completed_on: date
    deadline: date
    flag: Flag


def releases_waiting(today: date, aircraft: Aircraft | None = None) -> list[PendingRelease]:
    """Show readiness and the deadline based on the latest recorded completion."""
    packages = WorkPackage.objects.filter(issued_on__isnull=False, released_on__isnull=True)
    if aircraft is not None:
        packages = packages.filter(aircraft=aircraft)
    finished = (
        packages.select_related("aircraft")
        .annotate(
            completion=Max("cards__completed_on"),
            outstanding=Count(
                "cards",
                filter=Q(cards__completed_on__isnull=True)
                | Q(cards__critical=True, cards__inspected_on__isnull=True),
            ),
        )
        .filter(completion__isnull=False, outstanding=0)
        .order_by("completion", "reference")
    )
    waiting = []
    for package in finished:
        completed = package.completion
        deadline = release_record_deadline(completed)
        waiting.append(PendingRelease(package, completed, deadline, deadline_flag(today, deadline)))
    return waiting
