"""What can be done with service bulletins, changes, repairs and weighings.

Views check the role first, then call these. ML.A.304 and ML.A.305(d),
read in the UK text on 27 November 2026 (Decisions.md, Regulation Facts
in Use): modifications and repairs are carried out using approved data,
and the records hold their current status, the status of the design
approval holder's maintenance recommendations, and the current mass and
balance report.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.modifications.models import (
    APPROVED_ROUTES,
    STANDARD_ROUTES,
    Bulletin,
    Change,
    Classification,
    Data,
    OwnerDecision,
    Route,
    Weighing,
    WeightSchedule,
)
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules import mass as rules
from airworthiness_rules.components import due_back_flag
from airworthiness_rules.dates import days_between
from airworthiness_rules.programme import Flag


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def _locked(aircraft: Aircraft) -> Aircraft:
    """Take the aircraft's row, so that the same form sent twice waits for the first."""
    return Aircraft.objects.select_for_update().get(pk=aircraft.pk)


# Service bulletins


@transaction.atomic
def record_bulletin(
    aircraft: Aircraft,
    *,
    title: str,
    reference: str,
    classification: Classification | str,
    sent_on: date,
    reminder_on: date | None = None,
    decision: OwnerDecision | str = OwnerDecision.AWAITING,
    detail: str = "",
    decided_on: date | None = None,
) -> Bulletin:
    """Record a service bulletin sent to the owner, with the decision if it is made (REQ-249).

    A bulletin is recorded once for an aircraft: the same title and
    reference again is refused.
    """
    today = aircraft_services.today()
    title, reference = title.strip(), reference.strip()
    if not title or not reference:
        raise RefusedError("A Service Bulletin Has a Title and a Reference")
    if classification not in Classification.values:
        raise RefusedError("A Service Bulletin Is Recommended or Optional")
    if sent_on > today:
        raise RefusedError("A Service Bulletin Is Not Sent After Today")
    if reminder_on is not None and reminder_on < sent_on:
        raise RefusedError("A Reminder Is Not Before the Bulletin Was Sent")
    aircraft = _locked(aircraft)
    if Bulletin.objects.filter(aircraft=aircraft, title=title, reference=reference).exists():
        raise RefusedError("This Service Bulletin Is Already Recorded for the Aircraft")
    bulletin = Bulletin.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        title=title,
        reference=reference,
        classification=classification,
        sent_on=sent_on,
        reminder_on=reminder_on,
    )
    if decision != OwnerDecision.AWAITING or detail.strip() or decided_on is not None:
        if decided_on is None:
            raise RefusedError("A Decision Has the Day It Was Recorded")
        decide_bulletin(bulletin, decision=decision, detail=detail, decided_on=decided_on)
    return bulletin


@transaction.atomic
def decide_bulletin(
    bulletin: Bulletin, *, decision: OwnerDecision | str, detail: str, decided_on: date
) -> Bulletin:
    """Record what the owner decided of a service bulletin, once (REQ-250)."""
    bulletin = Bulletin.objects.select_for_update().get(pk=bulletin.pk)
    if not bulletin.awaiting:
        raise RefusedError("The Decision on This Service Bulletin Is Already Recorded")
    if decision not in (OwnerDecision.ACCEPTED, OwnerDecision.DECLINED):
        raise RefusedError("A Decision Is Accepted or Declined")
    detail = detail.strip()
    if not detail:
        raise RefusedError("A Decision Says What Was Decided")
    if decided_on > aircraft_services.today():
        raise RefusedError("A Decision Is Not Recorded After Today")
    if decided_on < bulletin.sent_on:
        raise RefusedError("A Decision Is Not Before the Bulletin Was Sent")
    bulletin.decision = decision
    bulletin.detail = detail
    bulletin.decided_on = decided_on
    bulletin.save(update_fields=["decision", "detail", "decided_on"])
    return bulletin


@dataclass(frozen=True)
class BulletinLine:
    """One service bulletin, with what is shown of its decision."""

    bulletin: Bulletin
    flag: Flag
    days: int | None

    @property
    def decision_text(self) -> str:
        """Return the decision as the board writes it: Every 50-Hour Check, or Declined."""
        bulletin = self.bulletin
        if bulletin.decision == OwnerDecision.ACCEPTED:
            return bulletin.detail
        return str(bulletin.decision)

    @property
    def decision_note(self) -> str:
        """Return what stands beside the decision: when it was sent, or why it was declined."""
        bulletin = self.bulletin
        if bulletin.awaiting:
            return f"Sent {formatting.long_date(bulletin.sent_on)}"
        return bulletin.detail if bulletin.decision == OwnerDecision.DECLINED else "Accepted"

    @property
    def recorded_text(self) -> str:
        """Return the day the decision was recorded, or the reminder."""
        bulletin = self.bulletin
        if bulletin.decided_on is not None:
            return formatting.long_date(bulletin.decided_on)
        if bulletin.reminder_on is not None:
            return f"Reminder {formatting.long_date(bulletin.reminder_on)}"
        return "No Reminder Set"

    @property
    def status(self) -> str:
        """Return the word of the status mark: a decision awaited is to assess."""
        if not self.bulletin.awaiting:
            return ""
        return self.flag.value if self.flag is not Flag.NONE else "To Assess"


def bulletin_lines(organisation: Organisation, today: date) -> list[BulletinLine]:
    """Return every service bulletin, those awaiting the owner first (REQ-253)."""
    lines = []
    for bulletin in Bulletin.objects.select_related("aircraft"):
        flag, days = Flag.NONE, None
        if bulletin.awaiting and bulletin.reminder_on is not None:
            flag = due_back_flag(today, bulletin.reminder_on, organisation.due_soon_days)
            days = days_between(today, bulletin.reminder_on)
        lines.append(BulletinLine(bulletin, flag, days))
    return sorted(
        lines,
        key=lambda line: (
            not line.bulletin.awaiting,
            line.bulletin.aircraft.registration,
            line.bulletin.sent_on,
            line.bulletin.title,
        ),
    )


# Changes and repairs


def _data(route: Route, data: Data | str) -> str:
    """Return the data a route is carried out with, or refuse a pair ML.A.304 does not give."""
    if route in STANDARD_ROUTES:
        if data not in ("", Data.STANDARD):
            raise RefusedError(
                "A Standard Change or Standard Repair Uses the Requirements of "
                "Point 21.A.90B or 21.A.431B, ML.A.304"
            )
        return Data.STANDARD.value
    if route in APPROVED_ROUTES:
        if data not in (Data.AUTHORITY, Data.DESIGN_ORGANISATION):
            raise RefusedError(
                "Say Whether the Data Is Approved by the Civil Aviation Authority "
                "or by a Design Organisation, ML.A.304"
            )
        return str(data)
    if data:
        raise RefusedError("Maintenance With the Same Part Number Names No Data")
    return ""


@transaction.atomic
def record_change(
    aircraft: Aircraft,
    *,
    title: str,
    route: Route | str,
    mass_effect: Decimal,
    data_kind: Data | str = "",
    reference: str = "",
    embodied_on: date | None = None,
) -> Change:
    """Record a change or repair, embodied or in progress (REQ-251, REQ-252).

    The same change again for an aircraft, embodied on the same day or
    still in progress, is refused.
    """
    title = title.strip()
    if not title:
        raise RefusedError("A Change or Repair Has a Title")
    if route not in Route.values:
        raise RefusedError("Choose the Approval Route")
    if abs(mass_effect) > rules.MOST_MASS:
        raise RefusedError("A Mass Effect Is at Most 999.9 Kilograms Either Way")
    if embodied_on is not None and embodied_on > aircraft_services.today():
        raise RefusedError("A Change or Repair Is Not Embodied After Today")
    found = _data(Route(route), data_kind)
    aircraft = _locked(aircraft)
    if Change.objects.filter(aircraft=aircraft, title=title, embodied_on=embodied_on).exists():
        raise RefusedError("This Change or Repair Is Already Recorded for the Aircraft")
    return Change.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        title=title,
        route=route,
        data=found,
        reference=reference.strip(),
        mass_effect=mass_effect,
        embodied_on=embodied_on,
    )


@transaction.atomic
def embody_change(change: Change, *, embodied_on: date) -> Change:
    """Record the day a change or repair in progress was embodied, once (REQ-252)."""
    change = Change.objects.select_for_update().get(pk=change.pk)
    if change.embodied_on is not None:
        raise RefusedError("This Change or Repair Is Already Embodied")
    if embodied_on > aircraft_services.today():
        raise RefusedError("A Change or Repair Is Not Embodied After Today")
    change.embodied_on = embodied_on
    change.save(update_fields=["embodied_on"])
    return change


# Weighings and the weight schedule


@transaction.atomic
def record_weighing(aircraft: Aircraft, *, weighed_on: date, reference: str) -> Weighing:
    """Record a weighing of an aircraft (REQ-254). Not before the last one recorded."""
    reference = reference.strip()
    if not reference:
        raise RefusedError("A Weighing Names Its Report")
    if weighed_on > aircraft_services.today():
        raise RefusedError("An Aircraft Is Not Weighed After Today")
    aircraft = _locked(aircraft)
    last = Weighing.objects.filter(aircraft=aircraft).order_by("-weighed_on").first()
    if last is not None and weighed_on == last.weighed_on:
        raise RefusedError("A Weighing on This Day Is Already Recorded")
    if last is not None and weighed_on < last.weighed_on:
        raise RefusedError("A Weighing Is Not Before the Last One Recorded")
    return Weighing.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        weighed_on=weighed_on,
        reference=reference,
    )


@transaction.atomic
def record_schedule(aircraft: Aircraft, *, issue: int, issued_on: date) -> WeightSchedule:
    """Record an issue of the weight schedule (REQ-254). Each issue follows the last."""
    if not 1 <= issue <= 9999:
        raise RefusedError("An Issue Is From 1 to 9,999")
    if issued_on > aircraft_services.today():
        raise RefusedError("A Weight Schedule Is Not Issued After Today")
    aircraft = _locked(aircraft)
    last = WeightSchedule.objects.filter(aircraft=aircraft).order_by("-issue").first()
    if last is not None and issue == last.issue:
        raise RefusedError("This Issue Is Already Recorded")
    if last is not None and (issue < last.issue or issued_on < last.issued_on):
        raise RefusedError("An Issue Follows the Last One Recorded")
    return WeightSchedule.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        issue=issue,
        issued_on=issued_on,
    )


def mass(value: Decimal) -> str:
    """Write a mass change with its sign: +1.2 Kilograms, a true minus for a loss."""
    sign = "+" if value > 0 else ("\u2212" if value < 0 else "")
    return f"{sign}{abs(value):,.1f} Kilograms"


@dataclass(frozen=True)
class ChangeLine:
    """One change or repair, and whether its records are complete."""

    change: Change
    records: str

    @property
    def status(self) -> str:
        """Return the word of the status mark: a schedule to update is to assess."""
        return "To Assess" if self.records == SCHEDULE_UPDATE else ""

    @property
    def embodied_text(self) -> str:
        """Return the day embodied, or In Progress."""
        if self.change.embodied_on is None:
            return IN_PROGRESS
        return formatting.long_date(self.change.embodied_on)

    @property
    def mass_text(self) -> str:
        """Return the mass effect with its sign."""
        return mass(self.change.mass_effect)


SCHEDULE_UPDATE = "Weight Schedule Update"
IN_PROGRESS = "In Progress"
COMPLETE = "Complete"
REWEIGH = "Reweigh"
CURRENT = "Current"
NO_WEIGHING = "No Weighing Recorded"


def _last_schedule(aircraft: Aircraft) -> WeightSchedule | None:
    return WeightSchedule.objects.filter(aircraft=aircraft).order_by("-issue").first()


def _records(change: Change, schedule: WeightSchedule | None) -> str:
    """Return what is outstanding of a change: nothing once it is in the weight schedule."""
    if change.embodied_on is None:
        return IN_PROGRESS
    if change.mass_effect == 0:
        return COMPLETE
    issued = schedule.issued_on if schedule is not None else None
    return COMPLETE if rules.in_schedule(change.embodied_on, issued) else SCHEDULE_UPDATE


def change_lines(aircraft: Aircraft | None = None) -> list[ChangeLine]:
    """Return every change and repair, what is outstanding first, then the latest (REQ-253)."""
    changes = Change.objects.select_related("aircraft")
    if aircraft is not None:
        changes = changes.filter(aircraft=aircraft)
    schedules: dict[object, WeightSchedule | None] = {}
    lines = []
    for change in changes:
        if change.aircraft_id not in schedules:
            schedules[change.aircraft_id] = _last_schedule(change.aircraft)
        lines.append(ChangeLine(change, _records(change, schedules[change.aircraft_id])))
    order = {SCHEDULE_UPDATE: 0, IN_PROGRESS: 1, COMPLETE: 2}
    return sorted(
        lines,
        key=lambda line: (
            order[line.records],
            -(line.change.embodied_on or date.max).toordinal(),
            line.change.aircraft.registration,
            line.change.title,
        ),
    )


@dataclass(frozen=True)
class WeightLine:
    """One aircraft: its last weighing, its weight schedule and the mass change since."""

    aircraft: Aircraft
    weighing: Weighing | None
    schedule: WeightSchedule | None
    # The changes embodied since the weighing, the earliest first.
    changes: tuple[Change, ...]
    net: Decimal
    threshold: Decimal | None
    state: str

    @property
    def status(self) -> str:
        """Return the word of the status mark."""
        return "To Assess" if self.state in (SCHEDULE_UPDATE, REWEIGH) else ""

    @property
    def changes_text(self) -> str:
        """Return the changes since the weighing: their titles, or how many."""
        if self.weighing is None:
            return ""
        if not self.changes:
            return "None"
        if len(self.changes) > 2:
            return f"{len(self.changes)} Changes"
        return "; ".join(change.title for change in self.changes)

    @property
    def net_text(self) -> str:
        """Return the net change with its sign, where there is a weighing to count from."""
        return mass(self.net) if self.weighing is not None else ""

    @property
    def threshold_text(self) -> str:
        """Return the organisation's reweigh threshold, or that none is set."""
        if self.threshold is None:
            return "No Reweigh Threshold Set"
        return f"{self.threshold:,.1f} Kilograms"

    @property
    def working(self) -> Working | None:
        """Return how the net change was worked out (REQ-139)."""
        if self.weighing is None:
            return None
        inputs = [("Last Weighed", formatting.long_date(self.weighing.weighed_on))]
        inputs += [
            (
                f"{change.title}, {formatting.long_date(change.embodied_on or date.min)}",
                mass(change.mass_effect),
            )
            for change in self.changes
        ]
        inputs.append(("Reweigh Threshold of the Organisation", self.threshold_text))
        return Working(
            "How the Net Change Was Calculated",
            mass(self.net),
            "The Sum of the Mass Effect of Each Change or Repair Embodied After the Day "
            "of the Last Weighing",
            tuple(inputs),
            "ML.A.305(d). The Threshold Is the Organisation's Own; the Regulation Gives None",
        )


def weight_line(aircraft: Aircraft) -> WeightLine:
    """Return one aircraft's weighing, schedule and mass change since (REQ-255, REQ-256).

    Reweigh, once the net change is over the organisation's threshold;
    with none set, nothing is marked for a reweigh. Otherwise a weight
    schedule to update, while a change with a mass effect is not yet in
    an issue of it.
    """
    threshold = aircraft.organisation.reweigh_threshold_kilograms
    weighing = Weighing.objects.filter(aircraft=aircraft).order_by("-weighed_on").first()
    schedule = _last_schedule(aircraft)
    if weighing is None:
        return WeightLine(aircraft, None, schedule, (), Decimal("0.0"), threshold, NO_WEIGHING)
    since = tuple(
        change
        for change in Change.objects.filter(aircraft=aircraft, embodied_on__isnull=False).order_by(
            "embodied_on", "title", "id"
        )
        if change.embodied_on is not None
        and rules.counted_since(change.embodied_on, weighing.weighed_on)
    )
    net = rules.net_change(change.mass_effect for change in since)
    if rules.over_threshold(net, threshold):
        state = REWEIGH
    elif any(_records(change, schedule) == SCHEDULE_UPDATE for change in since):
        state = SCHEDULE_UPDATE
    else:
        state = CURRENT
    return WeightLine(aircraft, weighing, schedule, since, net, threshold, state)


def weight_lines() -> list[WeightLine]:
    """Return every aircraft of the Fleet, what needs attention first (REQ-256)."""
    lines = [weight_line(aircraft) for aircraft in Aircraft.objects.filter(stage=Stage.FLEET)]
    order = {REWEIGH: 0, SCHEDULE_UPDATE: 1, NO_WEIGHING: 2, CURRENT: 3}
    return sorted(lines, key=lambda line: (order[line.state], line.aircraft.registration))
