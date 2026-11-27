"""What can be done with maintenance data. Views check the role first."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.maintenance_data.models import (
    AmendmentCheck,
    DataSet,
    Evidence,
    Holding,
    Kind,
    Revision,
)
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Unit
from airworthiness_rules.programme import Flag, Thresholds, limit_flag


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


@transaction.atomic
def record_data(
    *,
    organisation: Organisation,
    title: str,
    author: str,
    kind: Kind,
    applies_to: Sequence[str] = (),
    mandatory: bool = False,
    amendment_service: str = "",
    check_due: date | None = None,
    held: bool = True,
    revision: str = "",
    revision_date: date | None = None,
    provided_by: str = "",
    evidence: Evidence | None = None,
    evidence_dated: date | None = None,
) -> DataSet:
    """Record a set of maintenance data (REQ-080, REQ-081, REQ-086, REQ-088).

    Data that is needed but not held is recorded as Not Held, so that it
    shows. Customer-provided data names who provided it and how its
    amendment status is shown.
    """
    customer = bool(provided_by)
    if customer and (evidence is None or evidence_dated is None):
        raise RefusedError("Customer-Provided Data Shows Its Amendment Status and the Date")
    if held and (not revision or revision_date is None):
        raise RefusedError("Data Held Has a Revision and a Revision Date")
    data_set = DataSet.objects.create(
        organisation=organisation,
        title=title,
        author=author,
        kind=kind,
        applies_to=list(applies_to),
        mandatory=mandatory,
        amendment_service=amendment_service,
        check_due=check_due,
        holding=Holding.HELD if held else Holding.NOT_HELD,
        customer_provided=customer,
        provided_by=provided_by,
        evidence=evidence or "",
        evidence_dated=evidence_dated if customer else None,
    )
    if held and revision_date is not None:
        Revision.objects.create(
            organisation=organisation,
            data_set=data_set,
            revision=revision,
            revision_date=revision_date,
        )
    return data_set


def current_revision(data_set: DataSet) -> Revision | None:
    """Return the one current revision of a set, if it has any."""
    found: Revision | None = data_set.revisions.filter(current=True).first()
    return found


@transaction.atomic
def add_revision(data_set: DataSet, *, revision: str, revision_date: date) -> Revision:
    """Record a new revision, which supersedes the current one (REQ-085).

    Data recorded as Not Held becomes Held when its first revision arrives.
    """
    data_set = DataSet.objects.select_for_update().get(pk=data_set.pk)
    if data_set.holding == Holding.NO_LONGER_HELD:
        raise RefusedError("This Data Is No Longer Held")
    if data_set.revisions.filter(revision=revision).exists():
        raise RefusedError("This Revision Is Already Recorded")
    previous = current_revision(data_set)
    if previous is not None:
        if revision_date < previous.revision_date:
            raise RefusedError("A New Revision Is Not Dated Before the Current One")
        previous.current = False
        previous.save(update_fields=["current"])
    if data_set.holding == Holding.NOT_HELD:
        data_set.holding = Holding.HELD
        data_set.save(update_fields=["holding"])
    return Revision.objects.create(
        organisation_id=data_set.organisation_id,
        data_set=data_set,
        revision=revision,
        revision_date=revision_date,
    )


@transaction.atomic
def record_check(
    data_set: DataSet, *, checked_by: User, checked_on: date, result: str, next_due: date
) -> AmendmentCheck:
    """Record a check of the amendment status, and when the next is due (REQ-082, REQ-083)."""
    if checked_on > aircraft_services.today():
        raise RefusedError("A Check Cannot Be Dated After Today")
    if next_due <= checked_on:
        raise RefusedError("The Next Check Is After This One")
    # Serialise checks on the same set before deciding which date governs.
    DataSet.objects.select_for_update().only("pk").get(pk=data_set.pk)
    check = AmendmentCheck.objects.create(
        organisation_id=data_set.organisation_id,
        data_set=data_set,
        checked_on=checked_on,
        checked_by=checked_by,
        result=result,
    )
    if not data_set.checks.filter(checked_on__gt=checked_on).exists():
        data_set.check_due = next_due
        data_set.save(update_fields=["check_due"])
    return check


def confirm_customer_status(data_set: DataSet, *, evidence: Evidence, dated: date) -> None:
    """Record how and when the customer showed the amendment status of their data (REQ-086)."""
    if not data_set.customer_provided:
        raise RefusedError("This Data Was Not Provided by a Customer")
    data_set.evidence = evidence
    data_set.evidence_dated = dated
    data_set.save(update_fields=["evidence", "evidence_dated"])


def end_holding(data_set: DataSet, on: date) -> None:
    """Mark data as No Longer Held. The record of having held it stays (REQ-087)."""
    if data_set.holding != Holding.HELD:
        raise RefusedError("Only Data That Is Held Can Stop Being Held")
    data_set.holding = Holding.NO_LONGER_HELD
    data_set.no_longer_held_on = on
    data_set.save(update_fields=["holding", "no_longer_held_on"])


@dataclass(frozen=True)
class DataLine:
    """One set of data and where it stands today."""

    data_set: DataSet
    revision: Revision | None
    last_check: AmendmentCheck | None
    flag: Flag

    @property
    def state(self) -> str:
        """Return whether the data is held and its amendment check is in date."""
        if self.data_set.holding != Holding.HELD:
            return str(self.data_set.holding)
        if self.flag is Flag.OVERDUE:
            return "Amendment Check Overdue"
        if self.data_set.check_due is None:
            return "No Amendment Check Recorded"
        return "Held and Current"


def _line(data_set: DataSet, today: date, thresholds: Thresholds) -> DataLine:
    flag = Flag.NONE
    if data_set.holding == Holding.HELD and data_set.check_due is not None:
        flag = limit_flag(
            Limit(Unit.CALENDAR, data_set.check_due, days_between(today, data_set.check_due)),
            thresholds,
        )
    return DataLine(
        data_set=data_set,
        revision=current_revision(data_set),
        last_check=data_set.checks.select_related("checked_by").order_by("checked_on").last(),
        flag=flag,
    )


def _order(line: DataLine) -> tuple[int, int, str]:
    """Overdue checks first, and among them data with mandatory content first (REQ-084)."""
    rank = {Flag.OVERDUE: 0, Flag.DUE: 1, Flag.DUE_SOON: 2}.get(line.flag, 3)
    if line.data_set.holding == Holding.NOT_HELD:
        rank = 0
    return (rank, 0 if line.data_set.mandatory else 1, line.data_set.title)


def data_lines(organisation: Organisation, today: date) -> list[DataLine]:
    """Return every set of data, the ones needing attention first (REQ-083, REQ-084)."""
    thresholds = due.thresholds_of(organisation)
    lines = [_line(data_set, today, thresholds) for data_set in DataSet.objects.all()]
    return sorted(lines, key=_order)


@dataclass(frozen=True)
class AircraftData:
    """Whether the data for an aircraft's type rating is held and current (REQ-089)."""

    lines: list[DataLine]

    @property
    def answer(self) -> str:
        """Return the worst state among the data for the type rating."""
        states = [line.state for line in self.lines]
        for state in (
            "Not Held",
            "No Longer Held",
            "Amendment Check Overdue",
            "No Amendment Check Recorded",
        ):
            if state in states:
                return state
        return "Held and Current" if states else "No Data Recorded for This Type Rating"


def data_for(aircraft: Aircraft, today: date) -> AircraftData:
    """Return the data that applies to the aircraft's type rating, and where it stands."""
    thresholds = due.thresholds_of(aircraft.organisation)
    sets = DataSet.objects.filter(applies_to__contains=[aircraft.type_rating])
    return AircraftData(sorted((_line(s, today, thresholds) for s in sets), key=_order))
