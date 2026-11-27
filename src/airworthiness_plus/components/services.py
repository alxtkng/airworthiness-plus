"""What can be done with components. Views check the role first, then call these.

ML.A.503 and ML.A.305(e), read in the UK text on 27 November 2026
(Decisions.md, Regulation Facts in Use): a service-life-limited component
does not exceed its approved life, expressed in calendar time, flight
hours, landings or cycles, and its records hold where it has been fitted
and its accumulated time.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.components.models import LIFE, Basis, Component, Installation
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due
from airworthiness_plus.programme.models import Programme
from airworthiness_rules import components as rules
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Reading, Unit, Utilisation, projected_days
from airworthiness_rules.programme import Flag, limit_flag

NOT_KNOWN = 1_000_000


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def airframe(aircraft: Aircraft) -> Reading | None:
    """Return the current airframe hours and cycles of an aircraft, if any are entered."""
    counter = aircraft.counters.filter(kind=CounterKind.AIRFRAME).first()
    return aircraft_services.current_reading(counter) if counter is not None else None


def _limit_values(
    basis: Basis | str,
    *,
    limit_hours: Decimal | None,
    limit_cycles: int | None,
    limit_months: int | None,
    limit_date: date | None,
    date_label: str,
    review_hours: Decimal | None,
    last_review_hours: Decimal | None,
    last_review_on: date | None,
) -> dict[str, object]:
    """Check the values of a limit against its kind, and return those that belong to it."""
    if basis not in Basis.values:
        raise RefusedError("Choose What the Limit Is")
    basis = Basis(basis)
    life = (limit_hours, limit_cycles, limit_months)
    dated = limit_date is not None or bool(date_label)
    reviewed = (review_hours, last_review_hours, last_review_on)
    values: dict[str, object] = {
        "basis": basis,
        "limit_hours": None,
        "limit_cycles": None,
        "limit_months": None,
        "limit_date": None,
        "date_label": "",
        "review_hours": None,
        "last_review_hours": None,
        "last_review_on": None,
    }
    if basis in LIFE:
        if all(value is None for value in life):
            raise RefusedError("A Life Limit Is in Hours, Cycles or Months, ML.A.503")
        if dated or any(value is not None for value in reviewed):
            raise RefusedError("A Life Limit Has No Date on the Component and No Review")
        if limit_hours is not None and not 0 < limit_hours <= rules.MOST_LIMIT_HOURS:
            raise RefusedError("A Limit in Hours Is Above 0 and at Most 99,999.9")
        if limit_cycles is not None and not 1 <= limit_cycles <= rules.MOST_LIMIT_CYCLES:
            raise RefusedError("A Limit in Cycles Is From 1 to 999,999")
        if limit_months is not None and not 1 <= limit_months <= rules.MOST_LIMIT_MONTHS:
            raise RefusedError("A Limit in Months Is From 1 to 1,200")
        values.update(limit_hours=limit_hours, limit_cycles=limit_cycles, limit_months=limit_months)
    elif basis is Basis.DATE:
        if limit_date is None or not date_label:
            raise RefusedError("Give the Date on the Component and Say What It Is")
        if any(value is not None for value in (*life, *reviewed)):
            raise RefusedError("A Date on the Component Has No Other Limit")
        values.update(limit_date=limit_date, date_label=date_label)
    elif basis is Basis.ON_CONDITION:
        if any(value is None for value in reviewed):
            raise RefusedError(
                "On Condition Says How Often It Is Reviewed, and the Airframe Hours "
                "and the Day of the Last Review"
            )
        assert review_hours is not None and last_review_hours is not None  # noqa: S101
        assert last_review_on is not None  # noqa: S101
        if dated or any(value is not None for value in life):
            raise RefusedError("On Condition Has No Other Limit")
        if not 0 < review_hours <= rules.MOST_REVIEW_HOURS:
            raise RefusedError("A Review Interval Is Above 0 and at Most 9,999.9 Hours")
        if not 0 <= last_review_hours <= rules.MOST_HOURS:
            raise RefusedError("Airframe Hours Are From 0 to 999,999.9")
        if last_review_on > aircraft_services.today():
            raise RefusedError("A Review Is Not After Today")
        values.update(
            review_hours=review_hours,
            last_review_hours=last_review_hours,
            last_review_on=last_review_on,
        )
    elif dated or any(value is not None for value in (*life, *reviewed)):
        raise RefusedError("No Limit Recorded Has No Limit")
    return values


@transaction.atomic
def add_component(
    organisation: Organisation,
    *,
    name: str,
    basis: Basis | str,
    part_number: str = "",
    serial_number: str = "",
    source: str = "",
    limit_hours: Decimal | None = None,
    limit_cycles: int | None = None,
    limit_months: int | None = None,
    limit_date: date | None = None,
    date_label: str = "",
    review_hours: Decimal | None = None,
    last_review_hours: Decimal | None = None,
    last_review_on: date | None = None,
) -> Component:
    """Add a component with its limit (REQ-230).

    One at a time for an organisation: the same form sent twice waits for
    the first and is refused. A component with a serial number is recorded
    once; one with none is refused while another of the same name and part
    number has never been fitted.
    """
    name, part_number, serial_number = name.strip(), part_number.strip(), serial_number.strip()
    if not name:
        raise RefusedError("A Component Has a Name")
    values = _limit_values(
        basis,
        limit_hours=limit_hours,
        limit_cycles=limit_cycles,
        limit_months=limit_months,
        limit_date=limit_date,
        date_label=date_label.strip(),
        review_hours=review_hours,
        last_review_hours=last_review_hours,
        last_review_on=last_review_on,
    )
    Organisation.objects.select_for_update().get(pk=organisation.pk)
    same = Component.objects.filter(name=name, part_number=part_number, serial_number=serial_number)
    if serial_number and same.exists():
        raise RefusedError("This Component Is Already Recorded")
    if not serial_number and same.filter(installations__isnull=True).exists():
        raise RefusedError("This Component Is Already Recorded and Not Yet Fitted")
    return Component.objects.create(
        organisation=organisation,
        name=name,
        part_number=part_number,
        serial_number=serial_number,
        source=source.strip(),
        **values,
    )


@transaction.atomic
def change_limit(component: Component, *, source: str = "", **limit: object) -> Component:
    """Record another limit for a component (REQ-230). The history keeps the earlier one."""
    component = Component.objects.select_for_update().get(pk=component.pk)
    values = _limit_values(**limit)  # type: ignore[arg-type]
    values["source"] = source.strip()
    if all(getattr(component, field) == value for field, value in values.items()):
        raise RefusedError("This Limit Is Already Recorded")
    for field, value in values.items():
        setattr(component, field, value)
    component.save(update_fields=list(values))
    return component


def current_installation(component: Component) -> Installation | None:
    """Return where the component is fitted now, if it is fitted."""
    return Installation.objects.filter(component=component, removed_on__isnull=True).first()


def last_installation(component: Component) -> Installation | None:
    """Return the latest fitting of the component, removed or not."""
    return Installation.objects.filter(component=component).order_by("-fitted_on", "-id").first()


@transaction.atomic
def fit_component(
    component: Component,
    aircraft: Aircraft,
    *,
    position: str,
    fitted_on: date,
    airframe_hours_fitted: Decimal,
    hours_at_fitting: Decimal,
    airframe_cycles_fitted: int = 0,
    cycles_at_fitting: int = 0,
    life_from: date | None = None,
    release_document: str = "",
) -> Installation:
    """Record that a component was fitted to an aircraft (REQ-231; ML.A.305(e)).

    A component is fitted in one place at a time: a second fitting, or the
    same form sent twice, is refused. The airframe hours when it was fitted
    are not above the hours the aircraft has now.
    """
    today = aircraft_services.today()
    position = position.strip()
    if not position:
        raise RefusedError("A Fitting Names Its Position")
    if fitted_on > today:
        raise RefusedError("A Component Is Not Fitted After Today")
    if life_from is not None and life_from > fitted_on:
        raise RefusedError("A Component Is Not New or Overhauled After It Was Fitted")
    _check_counts(airframe_hours_fitted, airframe_cycles_fitted)
    _check_counts(hours_at_fitting, cycles_at_fitting)
    component = Component.objects.select_for_update().get(pk=component.pk)
    if current_installation(component) is not None:
        raise RefusedError("This Component Is Already Fitted")
    last = last_installation(component)
    if last is not None and last.removed_on is not None and fitted_on < last.removed_on:
        raise RefusedError("A Component Is Not Fitted Before It Was Last Removed")
    now = airframe(aircraft)
    if now is not None and (
        airframe_hours_fitted > now.hours or airframe_cycles_fitted > now.cycles
    ):
        raise RefusedError("The Airframe Had Not More Hours or Cycles Then Than It Has Now")
    fitting = Installation.objects.create(
        organisation_id=component.organisation_id,
        component=component,
        aircraft=aircraft,
        position=position,
        fitted_on=fitted_on,
        airframe_hours_fitted=airframe_hours_fitted,
        airframe_cycles_fitted=airframe_cycles_fitted,
        hours_at_fitting=hours_at_fitting,
        cycles_at_fitting=cycles_at_fitting,
        life_from=life_from,
        release_document=release_document.strip(),
    )
    # The Aircraft Registration is written by the database, as it stands (REQ-235).
    fitting.refresh_from_db(fields=["aircraft_registration"])
    return fitting


def _check_counts(hours: Decimal, cycles: int) -> None:
    if not 0 <= hours <= rules.MOST_HOURS:
        raise RefusedError("Hours Are From 0 to 999,999.9")
    if not 0 <= cycles <= rules.MOST_CYCLES:
        raise RefusedError("Cycles Are From 0 to 9,999,999")


@transaction.atomic
def record_life_from(fitting: Installation, life_from: date) -> Installation:
    """Record the day a component was new or last overhauled, where it was not known.

    Given once: the database refuses a change to a day already recorded.
    """
    fitting = Installation.objects.select_for_update().get(pk=fitting.pk)
    if fitting.life_from is not None:
        raise RefusedError("The Day Is Already Recorded")
    if fitting.removed_on is not None:
        raise RefusedError("A Fitting That Has Been Removed Is Never Altered")
    if life_from > fitting.fitted_on:
        raise RefusedError("A Component Is Not New or Overhauled After It Was Fitted")
    fitting.life_from = life_from
    fitting.save(update_fields=["life_from"])
    return fitting


@transaction.atomic
def remove_component(
    fitting: Installation,
    *,
    removed_on: date,
    airframe_hours_removed: Decimal,
    removal_reason: str,
    airframe_cycles_removed: int | None = None,
    sent_to: str = "",
    due_back_on: date | None = None,
) -> Installation:
    """Record that a component was removed (REQ-231; ML.A.305(e), ML.A.503).

    Once: a second removal, or the same form sent twice, is refused.
    """
    today = aircraft_services.today()
    fitting = Installation.objects.select_for_update().get(pk=fitting.pk)
    if fitting.removed_on is not None:
        raise RefusedError("This Component Is Already Removed")
    reason = removal_reason.strip()
    if not reason:
        raise RefusedError("A Removal Says Why")
    if removed_on > today:
        raise RefusedError("A Component Is Not Removed After Today")
    if removed_on < fitting.fitted_on:
        raise RefusedError("A Component Is Not Removed Before It Was Fitted")
    cycles = (
        fitting.airframe_cycles_fitted
        if airframe_cycles_removed is None
        else (airframe_cycles_removed)
    )
    _check_counts(airframe_hours_removed, cycles)
    if airframe_hours_removed < fitting.airframe_hours_fitted or (
        cycles < fitting.airframe_cycles_fitted
    ):
        raise RefusedError("The Airframe Had Not Fewer Hours or Cycles Than When It Was Fitted")
    now = airframe(fitting.aircraft)
    if now is not None and (airframe_hours_removed > now.hours or cycles > now.cycles):
        raise RefusedError("The Airframe Had Not More Hours or Cycles Then Than It Has Now")
    if due_back_on is not None and due_back_on < removed_on:
        raise RefusedError("A Component Is Not Due Back Before It Was Removed")
    fitting.removed_on = removed_on
    fitting.airframe_hours_removed = airframe_hours_removed
    fitting.airframe_cycles_removed = cycles
    fitting.removal_reason = reason
    fitting.sent_to = sent_to.strip()
    fitting.due_back_on = due_back_on
    fitting.save(
        update_fields=[
            "removed_on",
            "airframe_hours_removed",
            "airframe_cycles_removed",
            "removal_reason",
            "sent_to",
            "due_back_on",
        ]
    )
    return fitting


@transaction.atomic
def record_review(component: Component, *, airframe_hours: Decimal, reviewed_on: date) -> Component:
    """Record a review of a component kept on condition (REQ-233).

    Not before the last review, in hours or by day, and not above the
    hours the aircraft has now. The same review sent twice is refused.
    """
    component = Component.objects.select_for_update().get(pk=component.pk)
    if component.basis != Basis.ON_CONDITION:
        raise RefusedError("Only a Component Kept on Condition Is Reviewed")
    assert component.last_review_hours is not None  # noqa: S101
    assert component.last_review_on is not None  # noqa: S101
    if reviewed_on > aircraft_services.today():
        raise RefusedError("A Review Is Not After Today")
    if not 0 <= airframe_hours <= rules.MOST_HOURS:
        raise RefusedError("Airframe Hours Are From 0 to 999,999.9")
    if (airframe_hours, reviewed_on) == (component.last_review_hours, component.last_review_on):
        raise RefusedError("This Review Is Already Recorded")
    if airframe_hours < component.last_review_hours or reviewed_on < component.last_review_on:
        raise RefusedError("A Review Is Not Before the Last Review")
    fitting = current_installation(component)
    now = airframe(fitting.aircraft) if fitting is not None else None
    if now is not None and airframe_hours > now.hours:
        raise RefusedError("The Airframe Had Not More Hours Then Than It Has Now")
    component.last_review_hours = airframe_hours
    component.last_review_on = reviewed_on
    component.save(update_fields=["last_review_hours", "last_review_on"])
    return component


@dataclass(frozen=True)
class ComponentLine:
    """One component: where it is, its time since new or overhaul, and what remains."""

    component: Component
    fitting: Installation | None
    # Hours and cycles since new or overhaul: today if fitted, when removed if not.
    hours: Decimal | None
    cycles: int | None
    limits: tuple[Limit, ...]
    flag: Flag
    # Why nothing could be worked out, if it could not.
    problem: str
    # Days to the nearest limit, as far as it can be placed. Used to put the lines in order.
    days: int | None
    due_in_six_months: bool
    working: Working | None

    @property
    def fitted(self) -> bool:
        """Return whether the component is fitted to an aircraft."""
        return self.fitting is not None and self.fitting.removed_on is None

    @property
    def fitted_to(self) -> str:
        """Return the aircraft, or Off-Wing."""
        if self.fitted and self.fitting is not None:
            return self.fitting.aircraft_registration
        return "Off-Wing"

    @property
    def fitted_note(self) -> str:
        """Return where an off-wing component came from and where it is."""
        fitting = self.fitting
        if fitting is None:
            return "Never Fitted"
        if fitting.removed_on is None:
            return fitting.position
        note = f"From {fitting.aircraft_registration}"
        return f"{note}, At {fitting.sent_to}" if fitting.sent_to else note

    @property
    def limit_text(self) -> str:
        """Return the limit as the Components board writes it."""
        component = self.component
        if component.basis == Basis.ON_CONDITION and component.review_hours is not None:
            every = formatting.amount(Unit.HOURS, component.review_hours)
            return f"On Condition, Reviewed Every {every}"
        if component.basis == Basis.DATE:
            return component.date_label
        if component.basis == Basis.NONE:
            return Basis.NONE.value
        parts = []
        if component.limit_hours is not None:
            parts.append(formatting.amount(Unit.HOURS, component.limit_hours))
        if component.limit_cycles is not None:
            parts.append(formatting.amount(Unit.CYCLES, component.limit_cycles))
        if component.limit_months is not None:
            count = component.limit_months
            parts.append(f"{formatting.whole(count)} Month{'' if count == 1 else 's'}")
        return f"{' or '.join(parts)}, {component.basis}"

    @property
    def since_text(self) -> str:
        """Return the time since new or overhaul."""
        if self.hours is None:
            return "Not Recorded"
        text = formatting.amount(Unit.HOURS, self.hours)
        if self.fitting is not None and self.fitting.life_from is not None:
            text = f"{text}, Since {formatting.long_date(self.fitting.life_from)}"
        return text

    @property
    def remaining_text(self) -> str:
        """Return what remains to each limit, or where an off-wing component stands."""
        fitting = self.fitting
        if not self.fitted:
            if fitting is not None and fitting.due_back_on is not None:
                return f"Due Back {formatting.long_date(fitting.due_back_on)}"
            return "Off-Wing"
        if self.problem:
            return "Cannot Be Calculated"
        if not self.limits:
            return ""
        return "; ".join(_remaining(limit) for limit in self.limits)

    @property
    def due_text(self) -> str:
        """Return each due point: 2,000.0 Hours, 28 February 2027, Review at 9,900.0."""
        if self.component.basis == Basis.ON_CONDITION and self.limits:
            return f"Review at {formatting.hours(Decimal(self.limits[0].due))}"  # type: ignore[arg-type]
        return "; ".join(formatting.point(limit.unit, limit.due) for limit in self.limits)

    @property
    def status(self) -> str:
        """Return the word of the status mark."""
        return self.flag.value


def _remaining(limit: Limit) -> str:
    if limit.remaining >= 0:
        return formatting.amount(limit.unit, limit.remaining)
    return f"{formatting.amount(limit.unit, -limit.remaining)} Overdue"


def _utilisation(aircraft: Aircraft) -> Utilisation | None:
    programme = Programme.objects.filter(aircraft=aircraft).first()
    if programme is None:
        return None
    return Utilisation(programme.hours_per_day, programme.cycles_per_day)


def component_line(component: Component, today: date) -> ComponentLine:
    """Return one component with its time and what remains today (REQ-231 to REQ-234)."""
    fitting = last_installation(component)
    thresholds = due.thresholds_of(component.organisation)

    def line(
        hours: Decimal | None = None,
        cycles: int | None = None,
        found: tuple[Limit, ...] = (),
        flag: Flag = Flag.NONE,
        problem: str = "",
        days: int | None = None,
        soon: bool = False,
        working: Working | None = None,
    ) -> ComponentLine:
        return ComponentLine(
            component, fitting, hours, cycles, found, flag, problem, days, soon, working
        )

    if fitting is None:
        return line()
    if fitting.removed_on is not None:
        assert fitting.airframe_hours_removed is not None  # noqa: S101
        assert fitting.airframe_cycles_removed is not None  # noqa: S101
        hours = rules.hours_since(
            fitting.hours_at_fitting, fitting.airframe_hours_fitted, fitting.airframe_hours_removed
        )
        cycles = rules.cycles_since(
            fitting.cycles_at_fitting,
            fitting.airframe_cycles_fitted,
            fitting.airframe_cycles_removed,
        )
        flag, days = Flag.NONE, None
        if fitting.due_back_on is not None:
            flag = rules.due_back_flag(today, fitting.due_back_on, thresholds.days)
            days = days_between(today, fitting.due_back_on)
        return line(hours, cycles, flag=flag, days=days)

    now = airframe(fitting.aircraft)
    if now is None:
        return line(problem="No Airframe Hours Entered", soon=True)
    if now.hours < fitting.airframe_hours_fitted or now.cycles < fitting.airframe_cycles_fitted:
        return line(problem="Airframe Hours Entered Are Below Those When Fitted", soon=True)
    hours = rules.hours_since(fitting.hours_at_fitting, fitting.airframe_hours_fitted, now.hours)
    cycles = rules.cycles_since(
        fitting.cycles_at_fitting, fitting.airframe_cycles_fitted, now.cycles
    )
    inputs = [
        ("Airframe Hours Now", formatting.hours(now.hours)),
        ("Airframe Hours When Fitted", formatting.hours(fitting.airframe_hours_fitted)),
        ("Hours Since New or Overhaul When Fitted", formatting.hours(fitting.hours_at_fitting)),
    ]
    life = component.life
    if life is not None:
        if life.months is not None and fitting.life_from is None:
            return line(
                hours,
                cycles,
                problem="Calendar Limit Not Worked Out Until the Day It Was New or Last "
                "Overhauled Is Recorded",
                soon=True,
            )
        found = rules.life_limits(life, fitting.life_from, hours, cycles, today)
        if fitting.life_from is not None:
            inputs.append(("New or Last Overhauled", formatting.long_date(fitting.life_from)))
        rule = (
            "Hours Since New or Overhaul Are Those When Fitted and What the Airframe Has "
            "Flown Since. Each Limit Is Counted From New or Overhaul, With No Tolerance"
        )
        source = "ML.A.503; GM1 ML.A.302(c)(4). How the Hours Are Counted Is Ours"
    elif component.basis == Basis.DATE and component.limit_date is not None:
        found = (rules.dated_limit(component.limit_date, today),)
        inputs = [(component.date_label, formatting.long_date(component.limit_date))]
        rule = "The Date on the Component"
        source = "ML.A.503"
    elif component.basis == Basis.ON_CONDITION:
        assert component.last_review_hours is not None  # noqa: S101
        assert component.review_hours is not None  # noqa: S101
        if now.hours < component.last_review_hours:
            return line(
                hours, cycles, problem="Airframe Hours Entered Are Below the Last Review", soon=True
            )
        found = (
            rules.review_limit(component.last_review_hours, component.review_hours, now.hours),
        )
        inputs = [
            ("Airframe Hours Now", formatting.hours(now.hours)),
            ("Airframe Hours at the Last Review", formatting.hours(component.last_review_hours)),
            ("Reviewed Every", formatting.amount(Unit.HOURS, component.review_hours)),
        ]
        rule = "The Airframe Hours at the Last Review and the Review Interval"
        source = "The Organisation's Own, a Departure From the Manufacturer's Interval"
    else:
        return line(hours, cycles)

    utilisation = _utilisation(fitting.aircraft)
    flags = list(Flag)
    flag = max((limit_flag(limit, thresholds) for limit in found), key=flags.index)
    projected = [projected_days(limit, utilisation) for limit in found]
    known = [days for days in projected if days is not None]
    working = Working(
        "How What Remains Was Calculated",
        "; ".join(_remaining(limit) for limit in found),
        rule,
        tuple(inputs),
        source,
    )
    return line(
        hours,
        cycles,
        found,
        flag,
        days=min(known) if len(known) == len(found) else None,
        soon=rules.due_within_months(found, today, utilisation),
        working=working,
    )


def component_lines(today: date, aircraft: Aircraft | None = None) -> list[ComponentLine]:
    """Return every component, the nearest limit first (REQ-234).

    What cannot be calculated comes first, with a limit that cannot be
    placed by a day; then the nearest day, a limit in hours or cycles being
    placed by its projected days and an off-wing component by the day it is
    due back; then those with nothing due, by name.
    """
    components = Component.objects.all()
    if aircraft is not None:
        components = components.filter(
            installations__aircraft=aircraft, installations__removed_on__isnull=True
        )
    lines = [component_line(component, today) for component in components]

    def order(line: ComponentLine) -> tuple[int, int, str, str]:
        placed = line.days is not None
        nothing_due = not line.problem and not line.limits and not placed
        if nothing_due:
            rank, days = 2, NOT_KNOWN
        elif line.problem or not placed:
            rank, days = 0, 0
        else:
            rank, days = 1, line.days or 0
        return (rank, days, line.component.name, line.fitted_to)

    return sorted(lines, key=order)


@dataclass(frozen=True)
class Counts:
    """The counts of the Components board."""

    tracked: int
    off_wing: int
    on_condition: int
    due_in_six_months: int


def counts(lines: list[ComponentLine]) -> Counts:
    """Return how many components are tracked, off-wing, on condition and due in 6 months."""
    return Counts(
        tracked=len(lines),
        off_wing=sum(1 for line in lines if line.fitting is not None and not line.fitted),
        on_condition=sum(1 for line in lines if line.component.basis == Basis.ON_CONDITION),
        due_in_six_months=sum(1 for line in lines if line.fitted and line.due_in_six_months),
    )


def awaiting_refit() -> list[Installation]:
    """Return the latest fitting of each component that is off-wing and sent away (REQ-236).

    ML.A.504(a)(2): a component that does not comply with an applicable
    airworthiness directive is unserviceable, so applicability is checked
    before it is fitted again.
    """
    found = []
    for component in Component.objects.all():
        fitting = last_installation(component)
        if fitting is not None and fitting.removed_on is not None and fitting.sent_to:
            found.append(fitting)
    return found
