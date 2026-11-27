"""Planning examples for the two sample organisations on the test site."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation
from airworthiness_plus.sample.models import Added, Part
from airworthiness_plus.staffing import services
from airworthiness_plus.staffing.models import Demand, Function

PERIOD = date(2026, 12, 1)


@transaction.atomic
def add(organisation: Organisation, actor: User) -> None:
    """Add the planning example once, without changing a plan already entered."""
    with working_for(organisation.id, actor.id):
        Organisation.objects.select_for_update().only("id").get(pk=organisation.pk)
        if Added.objects.filter(part=Part.STAFFING_PLAN).exists():
            return
        if not Demand.objects.exists():
            approval_type = (
                ApprovalType.PART_145
                if organisation.approval_type == ApprovalType.PART_CAMO
                else ApprovalType.PART_CAO
            )
            approval = Approval.objects.filter(
                approval=approval_type, no_longer_held_on=None
            ).first()
            if approval is None:
                return
            if approval_type == ApprovalType.PART_145:
                if aircraft_services.today() < date(2026, 11, 16):
                    return
                _part_145(approval, actor)
            else:
                services.record_demand(
                    actor=actor,
                    approval=approval,
                    month=PERIOD,
                    function=Function.MANAGEMENT,
                    needed=Decimal("110.0"),
                    employed=Decimal("127.5"),
                    contracted=Decimal("0"),
                    basis="Records, Directives and Maintenance Programmes",
                )
        Added.objects.create(organisation=organisation, part=Part.STAFFING_PLAN)


def _part_145(approval: Approval, actor: User) -> None:
    reported = date(2026, 11, 16)
    original = services.record_demand(
        actor=actor,
        approval=approval,
        month=PERIOD,
        function=Function.CERTIFYING,
        needed=Decimal("290.0"),
        employed=Decimal("192.0"),
        contracted=Decimal("0"),
        basis="Certifying hours before contracted cover",
    )
    services.record_report(
        original,
        actor=actor,
        reported_on=reported,
        reported_to="Compliance Monitoring Manager and Accountable Manager",
        action="Booked 88 hours of cover, subject to verification of scope and authorisation",
    )
    services.record_demand(
        actor=actor,
        approval=approval,
        month=PERIOD,
        function=Function.CERTIFYING,
        needed=Decimal("290.0"),
        employed=Decimal("192.0"),
        contracted=Decimal("88.0"),
        basis="Employed hours and forecast contracted cover, subject to qualified availability",
    )
    services.review_plan(
        actor=actor,
        approval=approval,
        reviewed_on=date(2026, 9, 2),
        outcome="Reviewed, no change",
    )
