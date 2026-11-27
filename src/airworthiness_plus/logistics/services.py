"""Record and read supplier evaluations under the applicable maintenance approval."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import Supplier, SupplierEvaluation, SupplierStatus
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation, Privilege
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Unit
from airworthiness_rules.programme import Flag, Thresholds, limit_flag


class RefusedError(ValueError):
    """The evaluation does not agree with the organisation's records."""


def maintenance_approvals(organisation: Organisation, day: date) -> list[Approval]:
    """Return the organisation's maintenance approvals effective on the given day."""
    return [
        one
        for one in approvals.every(organisation)
        if one.held_on(day)
        and (
            one.approval == ApprovalType.PART_145
            or (
                one.approval == ApprovalType.PART_CAO
                and Privilege.MAINTENANCE in organisation.privileges
            )
        )
    ]


@dataclass(frozen=True)
class EvaluationLine:
    approval: Approval
    evaluation: SupplierEvaluation | None
    due_status: str


@dataclass(frozen=True)
class SupplierLine:
    supplier: Supplier
    evaluations: list[EvaluationLine]


def register(organisation: Organisation, held: list[Approval], today: date) -> list[SupplierLine]:
    """Show one supplier and the latest evaluation for each current maintenance approval."""
    current = SupplierEvaluation.objects.filter(
        approval__in=held, approval_reference=F("approval__reference")
    )
    suppliers = Supplier.objects.filter(organisation=organisation).prefetch_related(
        Prefetch("evaluations", queryset=current)
    )
    lines = []
    thresholds = Thresholds(days=organisation.due_soon_days)
    for supplier in suppliers:
        latest: dict[UUID, SupplierEvaluation] = {}
        for recorded in supplier.evaluations.all():
            latest.setdefault(recorded.approval_id, recorded)
        evaluations = []
        for approval in held:
            evaluation = latest.get(approval.id)
            deadline = evaluation.next_evaluation_on if evaluation else None
            flag = Flag.NONE
            if deadline:
                flag = limit_flag(
                    Limit(Unit.CALENDAR, deadline, days_between(today, deadline)), thresholds
                )
            evaluations.append(EvaluationLine(approval, evaluation, flag.value))
        lines.append(SupplierLine(supplier, evaluations))
    return lines


@transaction.atomic
def record_evaluation(
    organisation: Organisation,
    *,
    approval: str,
    supplies: str,
    release_documents: str,
    evaluated_on: date,
    next_evaluation_on: date | None,
    status: str,
    evidence: str,
    supplier: Supplier | None = None,
    name: str = "",
) -> SupplierEvaluation:
    """Append evidence, using the existing identity when recording a later evaluation."""
    organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
    today = aircraft_services.today()
    if evaluated_on > today:
        raise RefusedError("An Evaluation Cannot Be Dated in the Future")
    if next_evaluation_on and next_evaluation_on <= evaluated_on:
        raise RefusedError("The Next Evaluation Must Be After the Evaluation")
    if status == SupplierStatus.APPROVED and next_evaluation_on is None:
        raise RefusedError("Record the Next Evaluation for an Approved Supplier")
    term = next(
        (
            one
            for one in maintenance_approvals(organisation, evaluated_on)
            if one.approval == approval
        ),
        None,
    )
    reference = term.reference_on(evaluated_on) if term is not None else None
    if reference is None or term is None:
        raise RefusedError(f"The Organisation Held No {approval} Maintenance Approval on This Day")
    if supplier is None:
        try:
            with transaction.atomic():
                supplier = Supplier.objects.create(organisation=organisation, name=name)
        except IntegrityError as error:
            if Supplier.objects.filter(organisation=organisation, name__iexact=name).exists():
                raise RefusedError("This Supplier Is Already Recorded. Open Its Record") from error
            raise
    elif supplier.organisation_id != organisation.id:
        raise RefusedError("Choose a Supplier of This Organisation")
    return SupplierEvaluation.objects.create(
        organisation=organisation,
        supplier=supplier,
        approval=term,
        approval_reference=reference,
        supplies=supplies,
        release_documents=release_documents,
        evaluated_on=evaluated_on,
        next_evaluation_on=next_evaluation_on,
        status=status,
        evidence=evidence,
    )
