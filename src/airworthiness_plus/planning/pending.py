"""Work packages with signed cards and a release still to be entered."""

from dataclasses import dataclass
from datetime import date

from django.db.models import Min, Q

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
    """Show readiness and the deadline based on the earliest signed completion."""
    packages = WorkPackage.objects.filter(issued_on__isnull=False, released_on__isnull=True)
    if aircraft is not None:
        packages = packages.filter(aircraft=aircraft)
    finished = (
        packages.select_related("aircraft")
        .annotate(
            completion=Min(
                "cards__completed_on",
                filter=Q(cards__critical=False) | Q(cards__inspected_on__isnull=False),
            ),
        )
        .filter(completion__isnull=False)
        .order_by("completion", "reference")
    )
    waiting = []
    for package in finished:
        completed = package.completion
        deadline = release_record_deadline(completed)
        waiting.append(PendingRelease(package, completed, deadline, deadline_flag(today, deadline)))
    return waiting
