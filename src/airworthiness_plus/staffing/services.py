"""Record the plan for each approval, the review and subsequent deviations."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.services import today
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.staffing import rules
from airworthiness_plus.staffing.models import (
    Absence,
    AbsenceType,
    Demand,
    Function,
    Report,
    Review,
)


class RefusedError(ValueError):
    """The proposed entry does not agree with the plan or approval."""


def _check_approval(approval: Approval, actor: User, on: date) -> None:
    if approval.organisation_id != actor.organisation_id or not approval.held_on(on):
        raise RefusedError("Choose an Approval Held on That Day")


@transaction.atomic
def record_demand(
    *,
    actor: User,
    approval: Approval,
    month: date,
    function: str,
    needed: Decimal,
    employed: Decimal,
    contracted: Decimal,
    basis: str,
) -> Demand:
    Organisation.objects.select_for_update().only("id").get(pk=actor.organisation_id)
    _check_approval(approval, actor, today())
    basis = basis.strip()
    if month.day != 1 or function not in Function.values:
        raise RefusedError("Choose the First Day of the Month and a Function")
    if min(needed, employed, contracted) < 0 or not basis:
        raise RefusedError("Enter Non-Negative Hours and the Basis for the Plan")
    matching = Demand.objects.select_for_update().filter(
        approval=approval, month=month, function=function
    )
    line = matching.first()
    if line is not None:
        current = rules.assess(
            needed=line.needed,
            employed=line.employed,
            contracted=line.contracted,
            approval=approval.approval,
        )
        reported = line.reports.filter(
            needed=line.needed, employed=line.employed, contracted=line.contracted
        ).exists()
        if (
            current.reportable
            and not reported
            and (needed, employed, contracted)
            != (
                line.needed,
                line.employed,
                line.contracted,
            )
        ):
            raise RefusedError("Record the Report for This Shortfall Before Changing Its Hours")
        line.needed, line.employed, line.contracted, line.basis = (
            needed,
            employed,
            contracted,
            basis,
        )
        line.save(update_fields=["needed", "employed", "contracted", "basis"])
        return line
    return Demand.objects.create(
        organisation_id=actor.organisation_id,
        approval=approval,
        month=month,
        function=function,
        needed=needed,
        employed=employed,
        contracted=contracted,
        basis=basis,
    )


@transaction.atomic
def review_plan(*, actor: User, approval: Approval, reviewed_on: date, outcome: str) -> Review:
    _check_approval(approval, actor, reviewed_on)
    outcome = outcome.strip()
    if reviewed_on > today() or not outcome:
        raise RefusedError("Give the Review Outcome and a Date No Later Than Today")
    return Review.objects.create(
        organisation_id=actor.organisation_id,
        approval=approval,
        reviewed_by=actor,
        reviewed_on=reviewed_on,
        outcome=outcome,
    )


@transaction.atomic
def record_report(
    demand: Demand, *, actor: User, reported_on: date, reported_to: str, action: str
) -> Report:
    demand = Demand.objects.select_for_update().get(pk=demand.pk)
    _check_approval(demand.approval, actor, reported_on)
    result = rules.assess(
        needed=demand.needed,
        employed=demand.employed,
        contracted=demand.contracted,
        approval=demand.approval.approval,
    )
    if not result.reportable:
        raise RefusedError("This Plan Line Has No Reportable Part-145 Shortfall")
    if reported_on > today() or not reported_to.strip() or not action.strip():
        raise RefusedError("Give the Report Date, Recipients and Action Taken")
    return Report.objects.create(
        organisation_id=actor.organisation_id,
        demand=demand,
        reported_by=actor,
        reported_on=reported_on,
        reported_to=reported_to.strip(),
        action=action.strip(),
        needed=demand.needed,
        employed=demand.employed,
        contracted=demand.contracted,
    )


@transaction.atomic
def record_absence(
    *, actor: User, person: Person, kind: str, starts_on: date, ends_on: date
) -> Absence:
    person = Person.objects.select_for_update().get(pk=person.pk)
    if person.organisation_id != actor.organisation_id:
        raise RefusedError("Choose Staff of This Organisation")
    if kind not in AbsenceType.values or ends_on < starts_on:
        raise RefusedError("Choose an Absence and Set the End On or After the Start")
    if Absence.objects.filter(
        person=person, starts_on__lte=ends_on, ends_on__gte=starts_on
    ).exists():
        raise RefusedError("An Absence Is Already Recorded During These Dates")
    return Absence.objects.create(
        organisation_id=actor.organisation_id,
        person=person,
        kind=kind,
        starts_on=starts_on,
        ends_on=ends_on,
    )
