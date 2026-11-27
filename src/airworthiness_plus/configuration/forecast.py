"""The views of one aircraft's record: its forecast and its configuration (REQ-290 to REQ-293).

Nothing is worked out here but the day a limit is expected to be reached.
Every figure is read from the service that owns it, so the forecast, the
Dashboard and the page a line links to cannot say different things.
"""

from dataclasses import dataclass
from datetime import date

from django.urls import reverse

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Basis
from airworthiness_plus.configuration import services
from airworthiness_plus.configuration.models import Position
from airworthiness_plus.defects import services as defect_services
from airworthiness_plus.interface import formatting
from airworthiness_plus.programme import due
from airworthiness_plus.programme.models import Programme
from airworthiness_plus.reviews import services as review_services
from airworthiness_rules import forecast as rules
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import TaskKind, Unit
from airworthiness_rules.programme import Flag


@dataclass(frozen=True)
class ForecastLine:
    """One thing of an aircraft that falls due, and when it is expected to."""

    item: str
    detail: str
    due: str
    remaining: str
    # The day the limit is expected to be reached, or None if it cannot be placed.
    forecast: date | None
    status: str
    page: str
    url: str
    # A line that could not be calculated comes first.
    problem: bool = False

    @property
    def forecast_text(self) -> str:
        """Return the forecast day, or why there is none."""
        if self.problem:
            return "Cannot Be Calculated"
        if self.forecast is None:
            return "Not Forecast, No Planning Utilisation"
        return formatting.long_date(self.forecast)


def _days(limits: tuple[due.ExplainedLimit, ...]) -> int | None:
    """Return whole days to the first limit, including one already reached."""
    if any(limit.limit.remaining <= 0 for limit in limits):
        return 0
    found = []
    for limit in limits:
        days = int(limit.limit.remaining) if limit.limit.unit is Unit.CALENDAR else limit.projected
        if days is None:
            return None
        found.append(days)
    return min(found) if found else None


def forecast_lines(aircraft: Aircraft, today: date) -> list[ForecastLine]:
    """Return everything of an aircraft that falls due, the soonest forecast first (REQ-290).

    The tasks of its programme, the actions of directives among them; the
    limits of its components; its deferred defects; its review
    certificate; and the annual review of its programme. What cannot be
    calculated comes first, and what cannot be placed by a day last.
    """
    lines: list[ForecastLine] = []
    programme_url = reverse("programme", args=[aircraft.id])
    valid_to = review_services.current_valid_to(aircraft)
    for line in due.due_lines(aircraft, today, valid_to):
        of_directive = line.task.kind == TaskKind.AIRWORTHINESS_DIRECTIVE.value
        page, url = (
            ("Airworthiness Directives", reverse("directive_status", args=[aircraft.id]))
            if of_directive
            else ("Maintenance Programme", programme_url)
        )
        if line.needs_attention:
            lines.append(
                ForecastLine(
                    line.task.title, line.problem, "", "", None, "", page, url, problem=True
                )
            )
            continue
        shown = line.first if line.ranked else line.limits
        lines.append(
            ForecastLine(
                line.task.title,
                line.task.source,
                " or ".join(limit.due_text for limit in shown),
                line.remaining_summary,
                rules.forecast_date(today, _days(shown)),
                line.flag.value,
                page,
                url,
            )
        )
    for component in component_services.component_lines(today, aircraft):
        if component.component.basis == Basis.NONE:
            continue
        url = reverse("component", args=[component.component.id])
        lines.append(
            ForecastLine(
                component.component.name,
                component.problem or component.limit_text,
                component.due_text,
                component.remaining_text,
                rules.forecast_date(
                    today,
                    0
                    if any(limit.remaining <= 0 for limit in component.limits)
                    else component.days,
                ),
                component.status,
                "Aircraft Configuration",
                url,
                problem=bool(component.problem),
            )
        )
    for defect in defect_services.open_lines(aircraft.organisation, today, aircraft):
        if defect.defect.limit_on is None or defect.days_left is None:
            continue
        lines.append(
            ForecastLine(
                f"Deferred Defect Limit, {defect.defect.title}",
                defect.defect.point,
                formatting.long_date(defect.defect.limit_on),
                defect.remaining_text,
                rules.forecast_date(today, defect.days_left),
                defect.status,
                "Defects",
                reverse("defect", args=[defect.defect.id]),
            )
        )
    schedule = review_services.schedule_line(aircraft, today)
    if schedule.valid_to is not None and schedule.days is not None:
        lines.append(
            ForecastLine(
                "Airworthiness Review Certificate Expires",
                "ML.A.901(a)",
                formatting.long_date(schedule.valid_to),
                formatting.amount(Unit.CALENDAR, schedule.days),
                rules.forecast_date(today, schedule.days),
                schedule.flag.value,
                "Airworthiness Review",
                reverse("aircraft_review", args=[aircraft.id]),
            )
        )
    programme = Programme.objects.filter(aircraft=aircraft).first()
    if programme is not None:
        annual = due.review_line(programme, today, due.thresholds_of(aircraft.organisation))
        if annual.due is not None:
            days = days_between(today, annual.due)
            lines.append(
                ForecastLine(
                    "Maintenance Programme Annual Review",
                    "At Least Annually, ML.A.302(c)(9)",
                    formatting.long_date(annual.due),
                    formatting.amount(Unit.CALENDAR, days)
                    if days >= 0
                    else f"{formatting.amount(Unit.CALENDAR, -days)} Overdue",
                    rules.forecast_date(today, days),
                    annual.flag.value,
                    "Maintenance Programme",
                    programme_url,
                )
            )
    return sorted(
        lines,
        key=lambda line: (
            not line.problem,
            line.forecast is None,
            line.forecast or today,
            line.item,
        ),
    )


def next_days(lines: list[ForecastLine], today: date) -> list[ForecastLine]:
    """Return the lines forecast within the next 120 days, and those that cannot be calculated."""
    return [line for line in lines if line.problem or rules.within_window(today, line.forecast)]


# The configuration view

FILTERS = (
    ("", "All"),
    ("life-limited", "Life-Limited"),
    ("required", "Required"),
    ("needs-attention", "Needs Attention"),
    ("not-recorded", "Not Recorded"),
)


@dataclass(frozen=True)
class PositionLine:
    """One position of an aircraft, with the component fitted there and how it stands."""

    position: Position
    component: component_services.ComponentLine | None

    @property
    def life_limited(self) -> bool:
        """Return whether a component with a limit is fitted here."""
        return self.component is not None and self.component.component.basis != Basis.NONE

    @property
    def status(self) -> str:
        """Show a stale fitting separately from the recorded position details."""
        if self.position.component_id is not None and self.component is None:
            return "Component No Longer Fitted"
        return self.position.status

    @property
    def needs_attention(self) -> bool:
        """Return whether something of the position waits: not recorded, or a limit near."""
        position = self.position
        if position.tracked and not position.recorded:
            return True
        if self.status in ("Needs a Recorded Change", "Component No Longer Fitted"):
            return True
        found = self.component
        return found is not None and bool(found.problem or found.flag is not Flag.NONE)

    @property
    def limit_text(self) -> str:
        """Return the limit of what is fitted, if it has one."""
        return self.component.limit_text if self.life_limited and self.component else ""

    @property
    def remaining_text(self) -> str:
        """Return what remains of what is fitted, or why it cannot be worked out."""
        found = self.component
        if not self.life_limited or found is None:
            return ""
        return found.problem or found.remaining_text

    def shown_for(self, chosen: str) -> bool:
        """Return whether the position belongs to a filter of the Aircraft board."""
        return {
            "": True,
            "life-limited": self.life_limited,
            "required": self.position.required,
            "needs-attention": self.needs_attention,
            "not-recorded": not self.position.recorded,
        }[chosen]


def position_lines(aircraft: Aircraft, today: date) -> list[PositionLine]:
    """Return every position of an aircraft, by product and chapter (REQ-292)."""
    lines = []
    for position in Position.objects.filter(aircraft=aircraft).select_related(
        "component", "change"
    ):
        lines.append(PositionLine(position, services.fitted_component(position, today)))
    return sorted(
        lines, key=lambda line: (line.position.product, line.position.chapter, line.position.name)
    )
