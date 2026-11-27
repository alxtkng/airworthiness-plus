"""What the Dashboard shows: everything due across the organisation (REQ-215 to REQ-217).

The Home board of the canvas. One panel for each section that is built,
and in it one row for each thing that is due, due soon, overdue or
waiting. A phase that builds a section adds its panel or its rows here.

Nothing is worked out here. Each row is read from the service that owns
the figure, so the Dashboard, the page it links to and the Fleet cannot
say different things. An item is shown from its lead time (REQ-212): what
is not yet Due Soon is not on the Dashboard.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.urls import reverse

from airworthiness_plus.acceptance import services as acceptance_services
from airworthiness_plus.aircraft.models import Aircraft, Regime, Stage, Status
from airworthiness_plus.directives import services as directive_services
from airworthiness_plus.imports import services as import_services
from airworthiness_plus.interface import formatting
from airworthiness_plus.maintenance_data import services as data_services
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due
from airworthiness_plus.programme.models import Programme
from airworthiness_plus.reviews import services as review_services
from airworthiness_plus.reviews.models import ReviewStaff
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import TaskKind, Unit
from airworthiness_rules.programme import Flag
from airworthiness_rules.review import COPY_TO_AUTHORITY_DAYS

NOT_SET = "Not Set"
# Where a row with no day comes: after every row that has one.
NO_DAY = 1_000_000
# What is red comes first (REQ-193): overdue, or stopping the aircraft.
RED = frozenset({Flag.OVERDUE.value, Status.UNSERVICEABLE.value})


@dataclass(frozen=True)
class Row:
    """One thing due: what it is about, what it is, when, what remains and where it is held."""

    subject: str
    item: str
    detail: str
    due: str
    remaining: str
    # The word of the status mark: Due Soon, Due, Within Tolerance, Overdue,
    # Unserviceable, To Assess, or nothing.
    status: str
    page: str
    url: str
    # Days to the day it is due, as far as known. Used only to put rows in order.
    days: int = NO_DAY
    # A row that nobody can place, such as a task that cannot be calculated, comes first.
    first: bool = False

    @property
    def order(self) -> tuple[int, int, str, str]:
        """Return where the row comes in its panel: red, then the soonest, then by name."""
        urgent = self.first or self.status in RED
        return (0 if urgent else 1, self.days, self.subject, self.item)


@dataclass(frozen=True)
class Panel:
    """One section of the sidebar and what is due in it."""

    title: str
    subject: str
    rows: tuple[Row, ...]


def _remaining(unit: Unit, remaining: Decimal | int, flag: Flag) -> str:
    """Write what remains: 3 Days, 12.4 Hours, or 1 Day Overdue once the limit is passed."""
    if remaining >= 0:
        return formatting.amount(unit, remaining)
    passed = formatting.amount(unit, -remaining)
    return f"{passed} Overdue" if flag is Flag.OVERDUE else f"{passed} Past the Limit"


def _dated(deadline: date, today: date, flag: Flag) -> tuple[str, str, int]:
    days = days_between(today, deadline)
    return formatting.long_date(deadline), _remaining(Unit.CALENDAR, days, flag), days


def _aircraft_rows(aircraft: Aircraft, today: date) -> list[Row]:
    """Return what is due on one aircraft of the Fleet."""
    registration = aircraft.registration
    record = reverse("aircraft", args=[aircraft.id])
    programme = reverse("programme", args=[aircraft.id])
    review = reverse("aircraft_review", args=[aircraft.id])
    directives = reverse("directive_status", args=[aircraft.id])
    rows = []
    if aircraft.status == Status.UNSERVICEABLE and aircraft.unserviceable_since is not None:
        rows.append(
            Row(
                registration,
                f"Unserviceable, {aircraft.unserviceable_reason}",
                "",
                f"Grounded Since {formatting.long_date(aircraft.unserviceable_since)}",
                "",
                Status.UNSERVICEABLE.value,
                "Aircraft",
                record,
                days=0,
            )
        )

    # The airworthiness review certificate, and the copies owed for it (REQ-100, REQ-111).
    schedule = review_services.schedule_line(aircraft, today)
    if schedule.valid_to is None or schedule.days is None:
        rows.append(
            Row(
                registration,
                "No Airworthiness Review Certificate Recorded",
                "",
                NOT_SET,
                "",
                "",
                "Airworthiness Review",
                review,
                first=True,
            )
        )
    elif schedule.flag is not Flag.NONE:
        rows.append(
            Row(
                registration,
                "Airworthiness Review Certificate Expires",
                "Inside the 90-Day Window, ML.A.903(d)" if schedule.in_review_window else "",
                formatting.long_date(schedule.valid_to),
                _remaining(Unit.CALENDAR, schedule.days, schedule.flag),
                schedule.flag.value,
                "Airworthiness Review",
                review,
                days=schedule.days,
            )
        )
    for copy in schedule.copies:
        text, remaining, days = _dated(copy.deadline, today, copy.flag)
        if copy.extension is not None:
            started = f"Extended {formatting.long_date(copy.extension.extended_on)}"
            item = "Copy of Extended Review Certificate to the Civil Aviation Authority"
        else:
            started = f"Issued {formatting.long_date(copy.certificate.issued_on)}"
            item = "Copy of Review Certificate to the Civil Aviation Authority"
        rows.append(
            Row(
                registration,
                item,
                f"{started}, Within {COPY_TO_AUTHORITY_DAYS} Days, ML.A.903(f)",
                text,
                remaining,
                copy.flag.value,
                "Airworthiness Review",
                review,
                days=days,
            )
        )

    # Releases not yet in the records (REQ-051).
    for work in due.work_lines(aircraft, today):
        if work.release_flag is Flag.NONE:
            continue
        text, remaining, days = _dated(work.release_deadline, today, work.release_flag)
        rows.append(
            Row(
                registration,
                "Certificate of Release to Service Not Yet in Records",
                f"{work.work.description}, {formatting.long_date(work.work.dated)}, "
                "Within 30 Days, ML.A.305(a)",
                text,
                remaining,
                work.release_flag.value,
                "Maintenance Programme",
                programme,
                days=days,
            )
        )

    # The tasks of the programme, the actions of directives among them (REQ-043, REQ-065).
    for line in due.due_lines(aircraft, today, schedule.valid_to):
        of_directive = line.task.kind == TaskKind.AIRWORTHINESS_DIRECTIVE.value
        page, url = (
            ("Airworthiness Directives", directives)
            if of_directive
            else ("Maintenance Programme", programme)
        )
        if line.needs_attention:
            rows.append(
                Row(
                    registration,
                    line.task.title,
                    line.problem,
                    "Cannot Be Calculated",
                    "",
                    "",
                    page,
                    url,
                    first=True,
                )
            )
            continue
        if line.flag is Flag.NONE:
            continue
        flags = list(Flag)
        worst = max(line.limits, key=lambda limit: flags.index(limit.flag))
        projected = worst.projected
        if worst.limit.unit is Unit.CALENDAR:
            projected = int(worst.limit.remaining)
        rows.append(
            Row(
                registration,
                line.task.title,
                line.task.source,
                worst.due_text,
                _remaining(worst.limit.unit, worst.limit.remaining, worst.flag),
                line.flag.value,
                page,
                url,
                days=projected if projected is not None else NO_DAY,
            )
        )

    # The annual review of the programme (REQ-053). An aircraft with no programme
    # set up has nothing that can fall due, so it is shown, not left clear (H-018).
    held = Programme.objects.filter(aircraft=aircraft).first()
    if held is None and aircraft.calculations_supported:
        rows.append(
            Row(
                registration,
                "No Maintenance Programme Set Up",
                "ML.A.302",
                NOT_SET,
                "",
                "",
                "Maintenance Programme",
                programme,
                first=True,
            )
        )
    if aircraft.regime == Regime.NON_PART_21:
        # Nothing is calculated for it (REQ-022), so no task of its can show as
        # due. The Dashboard says so, as its own pages do, and does not leave it
        # looking clear (independent review of 24 November 2026, finding 7).
        rows.append(
            Row(
                registration,
                "Calculations Not Yet Supported for Non-Part 21 Aircraft",
                "Tasks Are Not Calculated",
                NOT_SET,
                "",
                "",
                "Maintenance Programme",
                programme,
                first=True,
            )
        )
    if held is not None:
        annual = due.review_line(held, today, due.thresholds_of(aircraft.organisation))
        if annual.due is None:
            # Never reviewed, as far as the records say: there is no day to count
            # from, so it is shown and not left clear. The programme page says
            # Not Recorded (finding 7).
            rows.append(
                Row(
                    registration,
                    "Maintenance Programme Annual Review Not Recorded",
                    "At Least Annually, ML.A.302(c)(9)",
                    NOT_SET,
                    "",
                    "",
                    "Maintenance Programme",
                    programme,
                    first=True,
                )
            )
        elif annual.flag is not Flag.NONE:
            text, remaining, days = _dated(annual.due, today, annual.flag)
            rows.append(
                Row(
                    registration,
                    "Maintenance Programme Annual Review",
                    "At Least Annually, ML.A.302(c)(9)",
                    text,
                    remaining,
                    annual.flag.value,
                    "Maintenance Programme",
                    programme,
                    days=days,
                )
            )
    return rows


def _to_assess(aircraft: Aircraft, today: date) -> list[Row]:
    """Return the directives whose applicability to an aircraft is still to decide (REQ-062)."""
    waiting = sum(1 for line in directive_services.status(aircraft, today) if line.to_assess)
    if not waiting:
        return []
    directives = "Airworthiness Directive" if waiting == 1 else "Airworthiness Directives"
    return [
        Row(
            aircraft.registration,
            f"Applicability of {waiting} {directives} to Assess",
            "",
            NOT_SET,
            "",
            "To Assess",
            "Airworthiness Directives",
            reverse("directive_status", args=[aircraft.id]),
        )
    ]


def continuing_airworthiness(organisation: Organisation, today: date) -> Panel:
    """Return what is due on the aircraft of the organisation (REQ-216)."""
    rows: list[Row] = []
    for aircraft in Aircraft.objects.all():
        if aircraft.stage == Stage.TRANSFER_IN:
            rows.append(
                Row(
                    aircraft.registration,
                    f"Transfer In, Records {aircraft.records_received} of "
                    f"{aircraft.records_expected} Received",
                    "",
                    NOT_SET,
                    "",
                    "",
                    "Transfers",
                    reverse("transfers"),
                )
            )
        else:
            rows += _aircraft_rows(aircraft, today)
        rows += _to_assess(aircraft, today)
    return Panel("Continuing Airworthiness", "Aircraft Registration", _ordered(rows))


def people(organisation: Organisation, today: date) -> Panel:
    """Return the review staff whose recency lapses soon or has lapsed (REQ-113, REQ-217)."""
    rows = []
    page, url = "Authorisations", reverse("review_staff")
    for staff in ReviewStaff.objects.filter(left_on__isnull=True).select_related("user"):
        line = review_services.staff_line(staff, today)
        name = staff.user.full_name
        if not line.current:
            rows.append(
                Row(
                    name,
                    "Airworthiness Review Staff Recency Lapsed",
                    "Restored by 1 Review Under Supervision, AMC1 CAO.A.045(d)",
                    formatting.long_date(line.lapses) if line.lapses else NOT_SET,
                    "",
                    Flag.OVERDUE.value,
                    page,
                    url,
                    days=days_between(today, line.lapses) if line.lapses else 0,
                )
            )
        elif line.lapses is not None and line.flag is not Flag.NONE:
            text, remaining, days = _dated(line.lapses, today, line.flag)
            rows.append(
                Row(
                    name,
                    "Airworthiness Review Staff Recency Lapses",
                    f"{line.basis}, AMC1 CAO.A.045(c)",
                    text,
                    remaining,
                    line.flag.value,
                    page,
                    url,
                    days=days,
                )
            )
    return Panel("People", "Name", _ordered(rows))


def documentation(organisation: Organisation, today: date) -> Panel:
    """Return the maintenance data that is not held and current (REQ-083, REQ-084, REQ-217).

    And each type rating of an aircraft for which no data is recorded (REQ-089).
    """
    rows = []
    for line in data_services.data_lines(organisation, today):
        data_set = line.data_set
        url = reverse("data_set", args=[data_set.id])
        if line.state in ("Held and Current", "No Longer Held") and line.flag is Flag.NONE:
            continue
        if data_set.check_due is not None and line.flag is not Flag.NONE:
            text, remaining, days = _dated(data_set.check_due, today, line.flag)
            rows.append(
                Row(
                    data_set.title,
                    "Maintenance Data Amendment to Check",
                    ", ".join(data_set.applies_to),
                    text,
                    remaining,
                    line.flag.value,
                    "Maintenance Data",
                    url,
                    days=days,
                )
            )
        else:
            item = "Maintenance Data Not Held" if line.state == "Not Held" else line.state
            rows.append(
                Row(
                    data_set.title,
                    item,
                    ", ".join(data_set.applies_to),
                    NOT_SET,
                    "",
                    "",
                    "Maintenance Data",
                    url,
                )
            )
    # A type rating of an aircraft with no maintenance data recorded at all: there
    # is no document to show as not held, so the type rating is shown (finding 7).
    without: dict[str, list[Aircraft]] = {}
    for aircraft in Aircraft.objects.order_by("registration"):
        if not data_services.data_for(aircraft, today).lines:
            without.setdefault(aircraft.type_rating, []).append(aircraft)
    for type_rating, fleet in without.items():
        rows.append(
            Row(
                type_rating,
                "No Maintenance Data Recorded for This Type Rating",
                ", ".join(one.registration for one in fleet),
                NOT_SET,
                "",
                "",
                "Maintenance Data",
                reverse("aircraft_data", args=[fleet[0].id]),
            )
        )
    return Panel("Documentation", "Document", _ordered(rows))


def organisation_records(organisation: Organisation, today: date) -> Panel:
    """Return imports not yet wholly checked and entries of the problem log not solved.

    CAP 562 C-90: up to 100% of what is migrated is checked, and problems
    found are logged with their solution (REQ-171, REQ-172).
    """
    rows = []
    for report in import_services.reports():
        if report.checked < report.total:
            rows.append(
                Row(
                    f"{report.load.kind}",
                    "Imported Records to Check",
                    report.proportion,
                    NOT_SET,
                    "",
                    "To Assess",
                    "Records",
                    reverse("import_report", args=[report.load.id]),
                )
            )
    for entry in acceptance_services.problem_log():
        if entry.status != "Solved":
            rows.append(
                Row(
                    formatting.long_date(entry.problem.raised_on),
                    f"Problem Log Entry, {entry.status}",
                    entry.problem.problem,
                    NOT_SET,
                    "",
                    "",
                    "Records",
                    reverse("problem_log"),
                )
            )
    return Panel("Organisation", "Record", _ordered(rows))


def _ordered(rows: list[Row]) -> tuple[Row, ...]:
    return tuple(sorted(rows, key=lambda row: row.order))


# One panel for each section that is built, in the order of the sidebar. A
# phase that builds a section adds its panel here.
PANELS: tuple[Callable[[Organisation, date], Panel], ...] = (
    continuing_airworthiness,
    people,
    documentation,
    organisation_records,
)


def dashboard(organisation: Organisation, today: date) -> list[Panel]:
    """Return every panel of the Dashboard for ``organisation`` (REQ-215)."""
    return [panel(organisation, today) for panel in PANELS]
