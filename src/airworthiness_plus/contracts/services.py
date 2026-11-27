"""What can be done with contracts and work orders. Views check the role first.

Appendix I to Part-ML, read in the UK text on 27 November 2026
(Decisions.md, Regulation Facts in Use), says what a continuing
airworthiness management contract contains and what each party does.
"""

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.contracts.models import (
    Contract,
    EndReason,
    OrderedBy,
    Outcome,
    Scope,
    WorkOrder,
)
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.programme.models import WorkDone
from airworthiness_rules import contracts as rules


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


@transaction.atomic
def draw_up_contract(
    aircraft: Aircraft,
    *,
    scope: Scope | str,
    type_of_operation: str,
    owner_address: str,
    signed_on: date,
    tasks: str = "",
) -> Contract:
    """Record a contract signed with the owner of an aircraft (REQ-240).

    The owner is the aircraft's customer. An aircraft has one contract in
    force: the same form sent twice waits for the first and is refused.
    """
    type_of_operation, owner_address, tasks = (
        type_of_operation.strip(),
        owner_address.strip(),
        tasks.strip(),
    )
    if scope not in Scope.values:
        raise RefusedError("A Contract Says Which Tasks Are Contracted")
    if scope == Scope.LIMITED and not tasks:
        raise RefusedError("A Contract for Limited Tasks Names Them")
    if scope == Scope.ALL and tasks:
        raise RefusedError("Limited Tasks Are Named Only for a Contract Limited to Them")
    if not type_of_operation:
        raise RefusedError("A Contract States the Type of Operation, Appendix I to Part-ML")
    if not owner_address:
        raise RefusedError("A Contract States the Address of the Owner, Appendix I to Part-ML")
    if signed_on > aircraft_services.today():
        raise RefusedError("A Contract Is Not Signed After Today")
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    if Contract.objects.filter(aircraft=aircraft, ended_on__isnull=True).exists():
        raise RefusedError("This Aircraft Already Has a Contract in Force")
    latest = Contract.objects.filter(aircraft=aircraft).order_by("ended_on").last()
    if latest is not None and latest.ended_on is not None and signed_on < latest.ended_on:
        raise RefusedError("A Contract Is Not Signed Before the Last One Ended")
    contract = Contract.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        customer_id=aircraft.customer_id,
        scope=scope,
        tasks=tasks,
        type_of_operation=type_of_operation,
        owner_address=owner_address,
        signed_on=signed_on,
    )
    # What the contract says of the aircraft, the owner and the organisation
    # is written by the database (REQ-241).
    contract.refresh_from_db()
    return contract


@transaction.atomic
def end_contract(contract: Contract, *, ended_on: date, end_reason: EndReason | str) -> Contract:
    """Record that a contract has ended, and why (REQ-242). Recorded once."""
    Aircraft.objects.select_for_update().get(pk=contract.aircraft_id)
    contract = Contract.objects.select_for_update().get(pk=contract.pk)
    if contract.ended_on is not None:
        raise RefusedError("This Contract Has Already Ended")
    if end_reason not in EndReason.values:
        raise RefusedError("An Ended Contract Says Why It Ended")
    if ended_on > aircraft_services.today():
        raise RefusedError("A Contract Does Not End After Today")
    if ended_on < contract.signed_on:
        raise RefusedError("A Contract Does Not End Before It Was Signed")
    contract.ended_on = ended_on
    contract.end_reason = end_reason
    contract.save(update_fields=["ended_on", "end_reason"])
    return contract


@transaction.atomic
def record_authority_told(contract: Contract, told_on: date) -> Contract:
    """Record the day the organisation told the Civil Aviation Authority (REQ-243)."""
    contract = Contract.objects.select_for_update().get(pk=contract.pk)
    if contract.ended_on is None:
        raise RefusedError("This Contract Has Not Ended")
    if contract.authority_told_on is not None:
        raise RefusedError("The Day the Civil Aviation Authority Was Told Is Already Recorded")
    if told_on > aircraft_services.today():
        raise RefusedError("The Civil Aviation Authority Is Not Told After Today")
    if told_on < contract.ended_on:
        raise RefusedError("The Civil Aviation Authority Is Not Told Before the Contract Ended")
    contract.authority_told_on = told_on
    contract.save(update_fields=["authority_told_on"])
    return contract


def in_force_on(aircraft: Aircraft, day: date) -> Contract | None:
    """Return the contract in force for the aircraft on ``day``, if there was one."""
    for contract in Contract.objects.filter(aircraft=aircraft).order_by("-signed_on"):
        if rules.in_force(contract.signed_on, contract.ended_on, day):
            return contract
    return None


@dataclass(frozen=True)
class ContractLine:
    """One contract and where it stands."""

    contract: Contract

    @property
    def status(self) -> str:
        """Return Active, Records Transfer or Ended, as the Contracts board writes them."""
        if self.contract.ended_on is not None:
            return "Ended"
        if self.contract.aircraft.stage == Stage.TRANSFER_IN:
            return "Records Transfer"
        return "Active"

    @property
    def status_note(self) -> str:
        """Return what goes with the status: records received, or why and when it ended."""
        contract = self.contract
        if contract.ended_on is not None:
            return f"{contract.end_reason}, {formatting.long_date(contract.ended_on)}"
        aircraft = contract.aircraft
        if aircraft.stage == Stage.TRANSFER_IN:
            return f"{aircraft.records_received} of {aircraft.records_expected} Received"
        return ""

    @property
    def to_tell(self) -> bool:
        """Return whether the organisation has still to tell the Civil Aviation Authority.

        Appendix I: the organisation informs the authority whenever the
        contract has not been respected or is denounced by either party.
        """
        contract = self.contract
        return (
            contract.ended_on is not None
            and contract.end_reason != EndReason.OTHER
            and contract.authority_told_on is None
        )

    @property
    def owner_deadline(self) -> date | None:
        """Return the owner's last day to tell the authority, after a non-conformity."""
        contract = self.contract
        if contract.ended_on is None or contract.end_reason != EndReason.NON_CONFORMITY:
            return None
        return rules.owner_notice_deadline(contract.ended_on)

    @property
    def working(self) -> Working | None:
        """Return how the owner's last day was worked out (REQ-139)."""
        deadline = self.owner_deadline
        if deadline is None or self.contract.ended_on is None:
            return None
        return Working(
            "How the Owner\N{RIGHT SINGLE QUOTATION MARK}s Last Day Was Calculated",
            formatting.long_date(deadline),
            "Within 2 Weeks of the Termination of the Contract, Counted as 14 Days",
            (("Ended", formatting.long_date(self.contract.ended_on)),),
            "Appendix I to Part-ML. The Count in Days Is Ours",
        )


def contract_lines() -> list[ContractLine]:
    """Return every contract (REQ-246).

    Those in force first; among them those for every task, then those for
    limited tasks, as the Contracts board has them; then by Aircraft
    Registration.
    """
    contracts = Contract.objects.select_related("aircraft", "customer__organisation")
    return sorted(
        (ContractLine(contract) for contract in contracts),
        key=lambda line: (
            line.contract.ended_on is not None,
            line.contract.scope != Scope.ALL,
            line.contract.registration,
            line.contract.signed_on,
        ),
    )


@transaction.atomic
def add_work_order(
    aircraft: Aircraft, *, work: str, ordered_by: OrderedBy | str, agreed_on: date
) -> WorkOrder:
    """Record a written request for maintenance (REQ-244).

    It is placed under the contract in force for the aircraft on the day it
    was agreed, if there was one. The same order sent twice is recorded once.
    """
    work = work.strip()
    if not work:
        raise RefusedError("A Work Order Says What Work Is Ordered")
    if ordered_by not in OrderedBy.values:
        raise RefusedError("A Work Order Says Who Ordered It")
    if agreed_on > aircraft_services.today():
        raise RefusedError("A Work Order Is Not Agreed After Today")
    aircraft = Aircraft.objects.select_for_update().get(pk=aircraft.pk)
    if WorkOrder.objects.filter(
        aircraft=aircraft, work=work, agreed_on=agreed_on, closed_on__isnull=True
    ).exists():
        raise RefusedError("This Work Order Is Already Recorded and Open")
    order = WorkOrder.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        contract=in_force_on(aircraft, agreed_on),
        work=work,
        ordered_by=ordered_by,
        agreed_on=agreed_on,
    )
    order.refresh_from_db()
    return order


@transaction.atomic
def close_work_order(
    order: WorkOrder,
    *,
    closed_on: date,
    outcome: Outcome | str,
    work_done: WorkDone | None = None,
) -> WorkOrder:
    """Record that a work order is completed or withdrawn (REQ-245). Recorded once."""
    order = WorkOrder.objects.select_for_update().get(pk=order.pk)
    if order.closed_on is not None:
        raise RefusedError("This Work Order Is Already Closed")
    if outcome not in Outcome.values:
        raise RefusedError("A Closed Work Order Is Completed or Withdrawn")
    if closed_on > aircraft_services.today():
        raise RefusedError("A Work Order Is Not Closed After Today")
    if closed_on < order.agreed_on:
        raise RefusedError("A Work Order Is Not Closed Before It Was Agreed")
    if work_done is not None:
        if outcome != Outcome.COMPLETED:
            raise RefusedError("Work Done Goes With a Completed Work Order")
        if work_done.aircraft_id != order.aircraft_id:
            raise RefusedError("The Work Done Belongs to Another Aircraft")
    order.closed_on = closed_on
    order.outcome = outcome
    order.work_done = work_done
    order.save(update_fields=["closed_on", "outcome", "work_done"])
    return order


def work_orders() -> list[WorkOrder]:
    """Return every work order: those open first, in the order they were agreed (REQ-246)."""
    orders = WorkOrder.objects.select_related("aircraft", "contract", "work_done")
    return sorted(
        orders,
        key=lambda order: (
            order.closed_on is not None,
            order.agreed_on,
            order.aircraft.registration,
            order.work,
        ),
    )
