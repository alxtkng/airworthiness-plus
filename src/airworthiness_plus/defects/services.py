"""What can be done with defects. Views check the role first, then call these.

ML.A.403, confirmed in the UK text on 24 November 2026 (Decisions.md,
Regulation Facts in Use): a defect that seriously endangers flight safety
is rectified before further flight; any other may be deferred by those
points (b)(1) to (4) name, and is rectified within the limits specified
in the maintenance data.
"""

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Status
from airworthiness_plus.defects.models import Basis, Decision, Defect, RepeatAction
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.programme.models import WorkDone
from airworthiness_rules import defects as rules
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Unit
from airworthiness_rules.programme import Flag

CLOSED_SHOWN_FOR_DAYS = 30
"""The Defects board: Closed, Last 30 Days."""


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def default_days(organisation: Organisation, basis: Basis) -> int | None:
    """Return the organisation's default limit for a deferral, in days (REQ-214).

    None for the minimum equipment list, which gives its own limit
    (ML.A.403(b)(2)).
    """
    return {
        Basis.PILOT_NON_REQUIRED: organisation.deferral_days_non_required,
        Basis.PILOT_LIST: None,
        Basis.PILOT_WITH_AGREEMENT: organisation.deferral_days_with_agreement,
        Basis.CERTIFYING_STAFF: organisation.deferral_days_certifying_staff,
    }[basis]


@transaction.atomic
def record_defect(
    aircraft: Aircraft,
    *,
    title: str,
    found_on: date,
    chapter: int,
    system: str,
    decision: Decision | str,
    decided_on: date,
    note: str = "",
    basis: Basis | str = "",
    decided_by: Person | None = None,
    data_limit_on: date | None = None,
    rectification: str = "",
    closed_on: date | None = None,
    work_done: WorkDone | None = None,
    maintenance_authorisation: MaintenanceAuthorisation | None = None,
    scope_confirmed: bool = False,
    legacy_evidence: str = "",
) -> Defect:
    """Record a defect with what was decided of it (REQ-220 to REQ-222).

    A defect that is Not Deferrable makes the aircraft Unserviceable, if it
    is not already (ML.A.403(a)). A deferred defect is given its limit from
    the organisation's default for the decision as it stands today, and
    from a limit in the maintenance data when that is the earlier
    (ML.A.403(c)). A defect already rectified is recorded with its
    rectification, and changes nothing of the aircraft.

    One at a time for an aircraft: the same form sent twice waits for the
    first and is refused.
    """
    today = aircraft_services.today()
    title, system, note = title.strip(), system.strip(), note.strip()
    if not title:
        raise RefusedError("A Defect Has a Title")
    if not system:
        raise RefusedError("A Defect Names Its System")
    if not rules.FIRST_CHAPTER <= chapter <= rules.LAST_CHAPTER:
        raise RefusedError("A Chapter Is From 1 to 99")
    if found_on > today or decided_on > today:
        raise RefusedError("A Defect Is Not Found or Decided After Today")
    if decided_on < found_on:
        raise RefusedError("A Decision Is Not Before the Defect Was Found")
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    matching = Defect.objects.filter(aircraft=aircraft, title=title, found_on=found_on)
    if matching.filter(closed_on__isnull=True).exists():
        raise RefusedError("This Defect Is Already Recorded and Open")

    limit: date | None = None
    days: int | None = None
    if decision == Decision.DEFERRED:
        if basis not in Basis.values:
            raise RefusedError("A Deferred Defect Says Who Deferred It, ML.A.403(b)")
        basis = Basis(basis)
        if basis is Basis.CERTIFYING_STAFF:
            if decided_by is None:
                raise RefusedError("Certifying Staff Who Defer a Defect Are Named, ML.A.403(b)(4)")
            _check_certifying(decided_by, decided_on)
        elif decided_by is not None:
            raise RefusedError("A Pilot-in-Command Is Not Chosen From the Staff")
        days = default_days(aircraft.organisation, basis)
        if days is None and data_limit_on is None:
            raise RefusedError("Give the Limit the Minimum Equipment List Gives, ML.A.403(b)(2)")
        if data_limit_on is not None and data_limit_on < found_on:
            raise RefusedError("A Limit Is Not Before the Day the Defect Was First Identified")
        limit = rules.deferral_limit(found_on, days, data_limit_on)
        if days_between(decided_on, limit) > rules.MOST_DAYS:
            raise RefusedError("A Limit Is at Most 365 Days After the Decision")
    elif decision == Decision.NOT_DEFERRABLE:
        if basis or data_limit_on is not None:
            raise RefusedError("A Defect That Is Not Deferrable Has No Limit")
        basis = ""
        if decided_by is not None:
            _check_certifying(decided_by, decided_on)
    else:
        raise RefusedError("A Defect Is Deferred or Not Deferrable")

    legacy_evidence = legacy_evidence.strip()
    try:
        people_services.check_certification_evidence(
            person=decided_by if basis == Basis.CERTIFYING_STAFF else None,
            on=decided_on,
            today=today,
            authorisation=maintenance_authorisation,
            scope_confirmed=scope_confirmed,
            legacy_evidence=legacy_evidence,
        )
    except people_services.RefusedError as error:
        raise RefusedError(str(error)) from error
    closing = closed_on is not None or bool(rectification.strip()) or work_done is not None
    if closing:
        _check_closure(aircraft, found_on, decided_on, rectification, closed_on, work_done, today)
        if matching.filter(
            chapter=chapter,
            system=system,
            note=note,
            decision=decision,
            basis=basis,
            decided_on=decided_on,
            decided_by=decided_by,
            data_limit_on=data_limit_on,
            rectification=rectification.strip(),
            closed_on=closed_on,
            work_done=work_done,
        ).exists():
            raise RefusedError("This Rectified Defect Is Already Recorded")
    elif decision == Decision.NOT_DEFERRABLE and aircraft.status != Status.UNSERVICEABLE:
        # ML.A.403(a): rectified before further flight.
        aircraft_services.make_unserviceable(aircraft, title, found_on)
    defect = Defect.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        title=title,
        note=note,
        found_on=found_on,
        chapter=chapter,
        system=system,
        decision=decision,
        basis=basis,
        decided_on=decided_on,
        decided_by=decided_by,
        maintenance_authorisation=maintenance_authorisation,
        scope_confirmed=scope_confirmed,
        legacy_evidence=legacy_evidence,
        default_days=days,
        data_limit_on=data_limit_on if decision == Decision.DEFERRED else None,
        limit_on=limit,
        rectification=rectification.strip() if closing else "",
        closed_on=closed_on if closing else None,
        work_done=work_done if closing else None,
    )
    # Who decided is written by the database, as their record stands (REQ-225).
    defect.refresh_from_db(fields=["decided_by_name", "decided_by_licence", "default_started_on"])
    return defect


def _check_certifying(person: Person, on: date) -> None:
    """Refuse a person who is not certifying staff, or who had left by the day."""
    if person.staff_group != StaffGroup.CERTIFYING:
        raise RefusedError("The Person Named Is Not Certifying Staff")
    if person.joined_on is not None and person.joined_on > on:
        raise RefusedError("The Person Named Had Not Joined by the Day of the Decision")
    if person.left_on is not None and person.left_on < on:
        raise RefusedError("The Person Named Had Left by the Day of the Decision")


def _check_closure(
    aircraft: Aircraft,
    found_on: date,
    decided_on: date,
    rectification: str,
    closed_on: date | None,
    work_done: WorkDone | None,
    today: date,
) -> None:
    if not rectification.strip():
        raise RefusedError("A Closed Defect Says How It Was Rectified")
    if closed_on is None:
        raise RefusedError("A Closed Defect Has the Day It Was Closed")
    if closed_on > today:
        raise RefusedError("A Defect Is Not Closed After Today")
    if closed_on < found_on:
        raise RefusedError("A Defect Is Not Closed Before It Was Found")
    if closed_on < decided_on:
        raise RefusedError("A Defect Is Not Closed Before the Decision Was Made")
    if work_done is not None and work_done.aircraft_id != aircraft.id:
        raise RefusedError("The Work Done Belongs to Another Aircraft")


@transaction.atomic
def close_defect(
    defect: Defect,
    *,
    rectification: str,
    closed_on: date,
    work_done: WorkDone | None = None,
) -> Defect:
    """Record that a defect is rectified (REQ-224).

    The aircraft's status is not changed here: an aircraft is made
    Serviceable on its own page, by whoever may, once nothing stops it.
    A defect is closed once; a second submit of the form is refused.
    """
    defect = Defect.objects.select_for_update().get(pk=defect.pk)
    if defect.closed_on is not None:
        raise RefusedError("This Defect Is Already Closed")
    _check_closure(
        defect.aircraft,
        defect.found_on,
        defect.decided_on,
        rectification,
        closed_on,
        work_done,
        aircraft_services.today(),
    )
    defect.rectification = rectification.strip()
    defect.closed_on = closed_on
    defect.work_done = work_done
    defect.save(update_fields=["rectification", "closed_on", "work_done"])
    return defect


@dataclass(frozen=True)
class DefectLine:
    """One open defect, with its limit and what remains of it."""

    defect: Defect
    flag: Flag
    days_left: int | None

    @property
    def status(self) -> str:
        """Return the word of the status mark: Unserviceable, or the flag of the limit."""
        if self.defect.decision == Decision.NOT_DEFERRABLE:
            return Status.UNSERVICEABLE.value
        return self.flag.value

    @property
    def limit_text(self) -> str:
        """Return the limit as the Defects board writes it: Grounded, or the day."""
        if self.defect.limit_on is None:
            return "Grounded"
        return formatting.long_date(self.defect.limit_on)

    @property
    def remaining_text(self) -> str:
        """Return what remains: 15 Days, or 2 Days Overdue once the limit is passed."""
        if self.days_left is None:
            return f"Since {formatting.long_date(self.defect.found_on)}"
        if self.days_left < 0:
            return f"{formatting.amount(Unit.CALENDAR, -self.days_left)} Overdue"
        return formatting.amount(Unit.CALENDAR, self.days_left)

    @property
    def working(self) -> Working | None:
        """Return how the limit was worked out (REQ-139), for a deferred defect."""
        defect = self.defect
        if defect.limit_on is None:
            return None
        inputs = [("Decided", formatting.long_date(defect.decided_on))]
        if defect.default_started_on is not None:
            inputs.append(("First Identified", formatting.long_date(defect.default_started_on)))
        if defect.default_days is not None:
            inputs.append(
                (
                    "Default Limit of the Organisation",
                    formatting.amount(Unit.CALENDAR, defect.default_days),
                )
            )
        if defect.data_limit_on is not None:
            label = (
                "Limit Given in the Minimum Equipment List"
                if defect.basis == Basis.PILOT_LIST
                else "Limit in the Maintenance Data"
            )
            inputs.append((label, formatting.long_date(defect.data_limit_on)))
        if defect.default_days is None:
            rule = "The Limit the Minimum Equipment List Gives"
        else:
            start = (
                "The Day the Defect Was First Identified"
                if defect.default_started_on is not None
                else "The Day of the Decision"
            )
            rule = (
                f"{start} and the Organisation's Default Limit, "
                "or the Limit in the Maintenance Data When It Is Earlier"
            )
        return Working(
            "How the Limit Was Calculated",
            formatting.long_date(defect.limit_on),
            rule,
            tuple(inputs),
            f"{defect.point}; ML.A.403(c). The Number of Days Is the Organisation's Own",
        )


def _line(defect: Defect, today: date, lead_days: int) -> DefectLine:
    if defect.limit_on is None:
        return DefectLine(defect, Flag.NONE, None)
    return DefectLine(
        defect,
        rules.deferral_flag(today, defect.limit_on, lead_days),
        days_between(today, defect.limit_on),
    )


def open_lines(
    organisation: Organisation, today: date, aircraft: Aircraft | None = None
) -> list[DefectLine]:
    """Return every open defect, what stops an aircraft first, then the nearest limit (REQ-223)."""
    defects = Defect.objects.filter(closed_on__isnull=True).select_related("aircraft")
    if aircraft is not None:
        defects = defects.filter(aircraft=aircraft)
    lines = [_line(defect, today, organisation.due_soon_days) for defect in defects]
    return sorted(
        lines,
        key=lambda line: (
            line.days_left is not None,
            line.days_left or 0,
            line.defect.aircraft.registration,
            line.defect.title,
        ),
    )


def defect_line(defect: Defect, today: date) -> DefectLine:
    """Return one defect with its flag today."""
    return _line(defect, today, defect.aircraft.organisation.due_soon_days)


def closed_lately(today: date) -> list[Defect]:
    """Return the defects closed in the last 30 days, the latest first (REQ-224)."""
    return [
        defect
        for defect in Defect.objects.filter(closed_on__isnull=False)
        .select_related("aircraft", "work_done")
        .order_by("-closed_on", "aircraft__registration", "title")
        if 0 <= days_between(defect.closed_on or today, today) <= CLOSED_SHOWN_FOR_DAYS
    ]


@dataclass(frozen=True)
class RepeatLine:
    """The same defect on one type in 12 months: a type rating and a chapter (REQ-226)."""

    type_rating: str
    chapter: int
    system: str
    defects: tuple[Defect, ...]
    action: RepeatAction | None

    @property
    def count(self) -> int:
        """Return how many of the defect were found in the 12 months."""
        return len(self.defects)

    @property
    def state(self) -> str:
        """Return Repeat, Watching or No Action."""
        return rules.repeat_state(self.count)

    @property
    def status(self) -> str:
        """Mark a repeat for assessment when the latest occurrence has no covering action."""
        covered = self.action is not None and self.defects[-1].found_on <= self.action.recorded_on
        return "To Assess" if self.state == "Repeat" and not covered else ""

    @property
    def registrations(self) -> str:
        """Return the aircraft the defect was found on."""
        return ", ".join(sorted({defect.aircraft.registration for defect in self.defects}))

    @property
    def system_text(self) -> str:
        """Return the system as the board writes it: Chapter 33, Lights."""
        return f"Chapter {self.chapter}, {self.system}"


def repeat_lines(today: date) -> list[RepeatLine]:
    """Return each type rating and chapter with a defect in the 12 months to today (REQ-226).

    The same defect is a defect in the same chapter on aircraft of the same
    type rating, matched exactly. Ours: the board does not say. The most
    of a defect comes first.
    """
    groups: dict[tuple[str, int], list[Defect]] = {}
    for defect in Defect.objects.select_related("aircraft").order_by("found_on", "id"):
        if rules.counted(defect.found_on, today):
            groups.setdefault((defect.aircraft.type_rating, defect.chapter), []).append(defect)
    actions: dict[tuple[str, int], RepeatAction] = {}
    for action in RepeatAction.objects.filter(superseded_by__isnull=True):
        actions[(action.type_rating, action.chapter)] = action
    lines = [
        RepeatLine(type_rating, chapter, found[-1].system, tuple(found), actions.get(key))
        for key, found in groups.items()
        for type_rating, chapter in [key]
    ]
    return sorted(lines, key=lambda line: (-line.count, line.type_rating, line.chapter))


@transaction.atomic
def record_repeat_action(
    organisation: Organisation, *, type_rating: str, chapter: int, action: str
) -> RepeatAction:
    """Record what was done about the same defect on one type (REQ-227).

    For a type rating and chapter that a defect is recorded for. The same
    action sent twice is recorded once.
    """
    today = aircraft_services.today()
    action = action.strip()
    if not action:
        raise RefusedError("An Action Says What Was Done")
    Organisation.objects.select_for_update().get(pk=organisation.pk)
    if not Defect.objects.filter(aircraft__type_rating=type_rating, chapter=chapter).exists():
        raise RefusedError("No Defect Is Recorded for This Type Rating and Chapter")
    latest = RepeatAction.objects.filter(
        type_rating=type_rating, chapter=chapter, superseded_by__isnull=True
    ).first()
    if (
        latest is not None
        and latest.action == action
        and not Defect.objects.filter(
            aircraft__type_rating=type_rating,
            chapter=chapter,
            found_on__gt=latest.recorded_on,
            found_on__lte=today,
        ).exists()
    ):
        raise RefusedError("This Action Is Already Recorded")
    return RepeatAction.objects.create(
        organisation=organisation,
        type_rating=type_rating,
        chapter=chapter,
        action=action,
        recorded_on=today,
        supersedes=latest,
    )
