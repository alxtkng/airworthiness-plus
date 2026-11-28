"""Record and read supplier evaluations under the applicable maintenance approval."""

from dataclasses import dataclass
from datetime import date
from uuid import UUID

from django.db import IntegrityError, transaction
from django.db.models import F, Prefetch

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.logistics.models import (
    SubcontractorAssessment,
    SubcontractorOutcome,
    Supplier,
    SupplierEvaluation,
    SupplierStatus,
)
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
    term, reference = _approval_on(organisation, approval, evaluated_on)
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


def _approval_on(organisation: Organisation, kind: str, day: date) -> tuple[Approval, str]:
    for approval in maintenance_approvals(organisation, day):
        if approval.approval == kind and (reference := approval.reference_on(day)):
            return approval, reference
    raise RefusedError(f"The Organisation Held No {kind} Maintenance Approval on This Day")


@transaction.atomic
def assess_subcontractor(
    supplier: Supplier,
    *,
    approval: str,
    assessed_on: date,
    scope: str,
    exposition_reference: str,
    qualification_evidence: str,
    controls: str,
    pre_audit_reference: str,
    outcome: str,
) -> SubcontractorAssessment:
    """Append evidence about the recorded scope and controls under this approval."""
    organisation = Organisation.objects.select_for_update(no_key=True).get(
        pk=supplier.organisation_id
    )
    if assessed_on > aircraft_services.today():
        raise RefusedError("An Assessment Cannot Be Dated in the Future")
    term, reference = _approval_on(organisation, approval, assessed_on)
    if outcome == SubcontractorOutcome.CONTROLS_RECORDED:
        if not exposition_reference or not qualification_evidence:
            raise RefusedError("Record the Exposition Reference and Qualification Evidence")
        if approval == ApprovalType.PART_145 and not pre_audit_reference:
            raise RefusedError("Record the Pre-Audit Reference for the Part-145 Assessment")
    return SubcontractorAssessment.objects.create(
        organisation=organisation,
        supplier=supplier,
        approval=term,
        approval_reference=reference,
        assessed_on=assessed_on,
        scope=scope,
        exposition_reference=exposition_reference,
        qualification_evidence=qualification_evidence,
        controls=controls,
        pre_audit_reference=pre_audit_reference,
        outcome=outcome,
    )
