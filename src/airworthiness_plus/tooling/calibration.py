"""Record scoped calibration evidence and distinguish acceptance from return to use."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.tooling import services, status
from airworthiness_plus.tooling.calibration_models import (
    CalibrationCertificate,
    CalibrationMovement,
    CalibrationOrder,
    CalibrationReinstatement,
    CalibrationResult,
    CertificateDecision,
    DecisionOutcome,
    MovementKind,
    Phase,
    ProviderService,
    ProviderStatus,
    Statement,
    ToolServiceProviderAuthorisation,
)
from airworthiness_plus.tooling.calibration_status import (
    decision_on,
    latest_certificate,
    movement,
    order_open,
)
from airworthiness_plus.tooling.models import (
    ControlKind,
    EventKind,
    Tool,
    ToolAction,
    ToolControlEvent,
    ToolControlRevision,
    ToolDelegation,
)
from airworthiness_rules.dates import add_months

RefusedError = services.RefusedError


def scope_on(scope: ToolServiceProviderAuthorisation, day: date) -> bool:
    """Check the scope version in force on the relevant date, including suspensions."""
    grant = scope.delegation
    if grant.approval.reference_on(day) != grant.approval_reference:
        return False
    latest = ToolServiceProviderAuthorisation.objects.filter(
        organisation=scope.organisation,
        supplier=scope.supplier,
        service=scope.service,
        delegation__approval_id=grant.approval_id,
        delegation__approval_reference=grant.approval_reference,
        delegation__site__iexact=grant.site,
        facility__iexact=scope.facility,
        measurement__iexact=scope.measurement,
        method__iexact=scope.method,
        unit__iexact=scope.unit,
        valid_from__lte=day,
    ).first()
    return (
        latest == scope
        and scope.status == ProviderStatus.AUTHORISED
        and scope.valid_to >= day
        and (scope.review_on is None or scope.review_on >= day)
    )


@transaction.atomic
def authorise_provider(
    user: User,
    *,
    request_id: UUID,
    approval: str,
    site: str,
    supplier: Supplier,
    service: str,
    facility: str,
    measurement: str,
    method: str,
    unit: str,
    range_from: Decimal | None,
    range_to: Decimal | None,
    valid_from: date,
    valid_to: date,
    review_on: date | None,
    status: str,
    accreditation: str,
    evidence: str,
) -> ToolServiceProviderAuthorisation:
    organisation, today = services._lock(user, Action.RECORD_TOOL_PROVIDER)
    grant = services._authorise(organisation, user, approval, ToolAction.PROVIDER, site, today)
    if supplier.organisation_id != organisation.pk:
        raise RefusedError("Choose a supplier of this organisation")
    if valid_from > valid_to or (
        range_from is not None and range_to is not None and range_from > range_to
    ):
        raise RefusedError("Give the scope range and the validity dates in order")
    if (range_from is None) != (range_to is None) or (
        service == ProviderService.CALIBRATION and range_from is None
    ):
        raise RefusedError("Give both limits of the calibration range")
    if service == ProviderService.CALIBRATION and not (measurement and unit):
        raise RefusedError("Record the calibration measurement type and unit")
    if review_on and not valid_from <= review_on <= valid_to:
        raise RefusedError("The review date must fall within the validity dates")
    if (
        status == ProviderStatus.AUTHORISED
        and service == ProviderService.CALIBRATION
        and approval == ApprovalType.PART_145
        and not accreditation
    ):
        raise RefusedError("Record the dated laboratory accreditation scope for Part-145")
    fields = dict(
        organisation=organisation,
        delegation=grant,
        supplier=supplier,
        service=service,
        facility=facility,
        measurement=measurement,
        method=method,
        unit=unit,
        range_from=range_from,
        range_to=range_to,
        valid_from=valid_from,
        valid_to=valid_to,
        review_on=review_on,
        status=status,
        accreditation=accreditation,
        evidence=evidence,
    )
    return services._retry(ToolServiceProviderAuthorisation, request_id, fields) or (
        ToolServiceProviderAuthorisation.objects.create(
            submission=request_id, signed_on=today, **fields
        )
    )


@transaction.atomic
def place_order(
    user: User,
    tool: Tool,
    *,
    request_id: UUID,
    provider: ToolServiceProviderAuthorisation,
    reference: str,
    measurement: str,
    unit: str,
    range_from: Decimal,
    range_to: Decimal,
    points: list[str],
    configuration: str,
    error_limit: Decimal,
    error_unit: str,
    limits_source: str,
    uncertainty_required: bool,
    requested_rule: str,
    reported_due_on: date | None,
    reported_label_source: str,
) -> CalibrationOrder:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    tool = Tool.objects.get(pk=tool.pk, organisation=organisation)
    if provider.organisation_id != organisation.pk:
        raise RefusedError("Choose a provider scope of this organisation")
    grant = services._authorise(
        organisation,
        user,
        provider.delegation.approval.approval,
        ToolAction.ORDER,
        tool.site,
        today,
    )
    fields = dict(
        organisation=organisation,
        tool=tool,
        delegation=grant,
        provider=provider,
        reference=reference,
        serial=tool.serial,
        component_ids=tool.component_ids,
        measurement=measurement,
        unit=unit,
        range_from=range_from,
        range_to=range_to,
        points=points,
        configuration=configuration,
        error_limit=error_limit,
        error_unit=error_unit,
        limits_source=limits_source,
        uncertainty_required=uncertainty_required,
        requested_rule=requested_rule,
        reported_due_on=reported_due_on,
        reported_label_source=reported_label_source,
    )
    if bool(reported_due_on) != bool(reported_label_source):
        raise RefusedError("Record the prior label deadline with its source")
    if saved := services._retry(CalibrationOrder, request_id, fields):
        return saved
    if CalibrationOrder.objects.filter(
        organisation=organisation, reference__iexact=reference
    ).exists():
        raise RefusedError("This order reference is already recorded")
    condition = status.condition_on(tool, today)
    if condition and condition.kind == EventKind.WITHDRAWN:
        raise RefusedError("The asset has been withdrawn")
    if not tool.serial or (tool.is_assembly and not tool.component_ids):
        raise RefusedError("Record the tool serial and controlled component identities first")
    if provider.delegation.site.casefold() != tool.site.casefold() or not scope_on(provider, today):
        raise RefusedError("Choose a current provider authorisation for the maintenance site")
    if (
        provider.service != ProviderService.CALIBRATION
        or provider.range_from is None
        or provider.range_to is None
        or provider.measurement.casefold() != measurement.casefold()
        or provider.unit != unit
        or not provider.range_from <= range_from <= range_to <= provider.range_to
    ):
        raise RefusedError("The ordered range is outside the authorised provider scope")
    requested = {Decimal(point) for point in points}
    if not requested or min(requested) != range_from or max(requested) != range_to:
        raise RefusedError("The required test points must cover both ends of the ordered range")
    control = status.active_controls(tool, grant.approval, grant.approval_reference, today).get(
        ControlKind.CALIBRATION
    )
    if control is None:
        raise RefusedError("Record the calibration control basis for this approval first")
    if any(order_open(order, today) for order in tool.calibration_orders.all()):
        raise RefusedError("This tool already has an open calibration order")
    return CalibrationOrder.objects.create(
        control=control,
        submission=request_id,
        signed_on=today,
        **fields,
    )


def _order_actor(
    user: User,
    organisation: Organisation,
    order: CalibrationOrder,
    action: ToolAction,
    today: date,
) -> ToolDelegation:
    if order.organisation_id != organisation.pk:
        raise RefusedError("Choose an order of this organisation")
    grant = services._authorise(
        organisation,
        user,
        order.delegation.approval.approval,
        action,
        order.tool.site,
        today,
    )
    if grant.approval_reference != order.delegation.approval_reference:
        raise RefusedError("This order belongs to an earlier maintenance approval reference")
    return grant


@transaction.atomic
def record_movement(
    user: User,
    order: CalibrationOrder,
    *,
    request_id: UUID,
    kind: str,
    occurred_on: date,
    expected_on: date | None,
    evidence: str,
) -> CalibrationMovement:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    grant = _order_actor(user, organisation, order, ToolAction.RECEIPT, today)
    fields = dict(
        organisation=organisation,
        delegation=grant,
        order=order,
        kind=kind,
        occurred_on=occurred_on,
        expected_on=expected_on,
        evidence=evidence,
    )
    if saved := services._retry(CalibrationMovement, request_id, fields):
        return saved
    if CalibrationMovement.objects.filter(order=order, kind=kind).exists() or occurred_on > today:
        raise RefusedError("Record each movement once, on or before today")
    if kind == MovementKind.DESPATCHED:
        if not expected_on or expected_on < occurred_on:
            raise RefusedError("Give an expected return date on or after despatch")
        if not scope_on(order.provider, occurred_on):
            raise RefusedError("The recorded provider scope was inactive on despatch")
    else:
        despatch = movement(order, MovementKind.DESPATCHED, today)
        if not despatch or despatch.occurred_on > occurred_on or expected_on is not None:
            raise RefusedError("Record actual return on or after despatch, with no expected date")
    return CalibrationMovement.objects.create(submission=request_id, signed_on=today, **fields)


@transaction.atomic
def record_certificate(
    user: User,
    order: CalibrationOrder,
    *,
    request_id: UUID,
    number: str,
    revision: str,
    source: str,
    calibrated_on: date,
    received_on: date,
    serial: str,
    component_ids: str,
    facility: str,
    standard: str,
    method: str,
    configuration: str,
    traceability: str,
    rule: str,
    adjustment: str,
) -> CalibrationCertificate:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    grant = _order_actor(user, organisation, order, ToolAction.RESULT, today)
    fields = dict(
        organisation=organisation,
        delegation=grant,
        order=order,
        number=number,
        revision=revision,
        source=source,
        calibrated_on=calibrated_on,
        received_on=received_on,
        serial=serial,
        component_ids=component_ids,
        facility=facility,
        standard=standard,
        method=method,
        configuration=configuration,
        traceability=traceability,
        rule=rule,
        adjustment=adjustment,
    )
    if saved := services._retry(CalibrationCertificate, request_id, fields):
        return saved
    despatch = movement(order, MovementKind.DESPATCHED, today)
    if not despatch or not despatch.occurred_on <= calibrated_on <= received_on <= today:
        raise RefusedError(
            "The dates must run from despatch through calibration and certificate receipt"
        )
    if order.certificates.filter(number__iexact=number, revision__iexact=revision).exists():
        raise RefusedError("This certificate number and revision have already been recorded")
    return CalibrationCertificate.objects.create(submission=request_id, signed_on=today, **fields)


@transaction.atomic
def record_result(
    user: User,
    certificate: CalibrationCertificate,
    *,
    request_id: UUID,
    phase: str,
    reference_value: Decimal,
    measured_value: Decimal | None,
    error: Decimal | None,
    uncertainty: Decimal | None,
    coverage: str,
    convention: str,
    statement: str,
) -> CalibrationResult:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    order = certificate.order
    grant = _order_actor(user, organisation, order, ToolAction.RESULT, today)
    fields = dict(
        organisation=organisation,
        delegation=grant,
        certificate=certificate,
        phase=phase,
        reference_value=reference_value,
        measured_value=measured_value,
        error=error,
        uncertainty=uncertainty,
        coverage=coverage,
        convention=convention,
        statement=statement,
    )
    if saved := services._retry(CalibrationResult, request_id, fields):
        return saved
    if certificate != latest_certificate(order, today) or certificate.decisions.exists():
        raise RefusedError("Record new results on a corrected certificate revision")
    if certificate.results.filter(phase=phase, reference_value=reference_value).exists():
        raise RefusedError("This point already has a result for this phase")
    # A result trigger creates the sole case in this same INSERT transaction.
    return CalibrationResult.objects.create(submission=request_id, signed_on=today, **fields)


def _validate_certificate(
    certificate: CalibrationCertificate, day: date, internal_rule: str
) -> None:
    order = certificate.order
    if certificate.serial != order.serial or certificate.component_ids != order.component_ids:
        raise RefusedError("The certificate serial or controlled components do not match the order")
    if (
        certificate.facility != order.provider.facility
        or certificate.method != order.provider.method
        or certificate.standard != order.control.standard
        or certificate.configuration != order.configuration
        or not scope_on(order.provider, certificate.calibrated_on)
    ):
        raise RefusedError(
            "The certificate facility, method, standard or coverage is outside the ordered scope"
        )
    if not certificate.traceability:
        raise RefusedError("The certificate needs documented metrological traceability")
    returned = movement(order, MovementKind.RETURNED, day)
    if returned and certificate.calibrated_on > returned.occurred_on:
        raise RefusedError("Calibration must precede or coincide with physical return")
    if order.requested_rule and certificate.rule != order.requested_rule:
        raise RefusedError("Verify the requested conformity decision rule")
    required = {Decimal(point) for point in order.points}
    found = {p.reference_value: p for p in certificate.results.all() if p.phase == Phase.FOUND}
    left = {p.reference_value: p for p in certificate.results.all() if p.phase == Phase.LEFT}
    if not required <= found.keys() or not required <= left.keys():
        raise RefusedError("Record as-found and as-left evidence for all ordered test points")
    for point in (*found.values(), *left.values()):
        if not order.range_from <= point.reference_value <= order.range_to:
            raise RefusedError("The certificate includes a point outside the ordered scope")
        if point.statement in {Statement.CONFORMS, Statement.FAILS} and not certificate.rule:
            raise RefusedError("The laboratory conformity claim has no decision rule")
        if (
            order.uncertainty_required
            and (point.phase == Phase.LEFT or point.statement == Statement.CONFORMS)
            and (point.uncertainty is None or not point.coverage)
        ):
            raise RefusedError("The ordered scope requires uncertainty and coverage")
        if point.phase == Phase.FOUND:
            continue
        if point.error is None or point.measured_value is None or not point.convention:
            raise RefusedError("Record the as-left reading, signed error and error convention")
        if point.statement == Statement.MEASUREMENT:
            if (
                not internal_rule
                or point.uncertainty is None
                or not point.coverage
                or abs(point.error) + point.uncertainty > order.error_limit
            ):
                raise RefusedError(
                    "An internal measurement decision needs a cited rule "
                    "and uncertainty within limits"
                )
        elif point.statement != Statement.CONFORMS or abs(point.error) > order.error_limit:
            raise RefusedError(
                "The as-left evidence does not support conformity within the ordered limits"
            )


@transaction.atomic
def decide_certificate(
    user: User,
    certificate: CalibrationCertificate,
    *,
    request_id: UUID,
    outcome: str,
    reason: str,
    internal_rule: str,
) -> CertificateDecision:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    order = certificate.order
    grant = _order_actor(user, organisation, order, ToolAction.CERTIFICATE, today)
    fields = dict(
        organisation=organisation,
        delegation=grant,
        certificate=certificate,
        outcome=outcome,
        reason=reason,
        internal_rule=internal_rule,
    )
    if saved := services._retry(CertificateDecision, request_id, fields):
        return saved
    if certificate != latest_certificate(order, today):
        raise RefusedError("Decide the current certificate revision")
    if outcome == DecisionOutcome.ACCEPTED:
        _validate_certificate(certificate, today, internal_rule)
    return CertificateDecision.objects.create(submission=request_id, signed_on=today, **fields)


def _same_calibration_scope(first: ToolControlRevision, second: ToolControlRevision) -> bool:
    fields = (
        "instruction",
        "instruction_revision",
        "standard",
        "method",
        "limits",
        "scope",
        "loan_task",
        "loan_evidence",
        "loan_identity",
    )
    return all(getattr(first, field) == getattr(second, field) for field in fields)


@transaction.atomic
def reinstate(
    user: User,
    order: CalibrationOrder,
    *,
    request_id: UUID,
    evidence: str,
) -> CalibrationReinstatement:
    organisation, today = services._lock(user, Action.RECORD_TOOL_CALIBRATION)
    grant = _order_actor(user, organisation, order, ToolAction.REINSTATE, today)
    certificate = latest_certificate(order, today)
    decision = decision_on(certificate, today) if certificate else None
    if not certificate or not decision or decision.outcome != DecisionOutcome.ACCEPTED:
        raise RefusedError("Accept the current certificate before reinstating the tool")
    fields = dict(organisation=organisation, delegation=grant, decision=decision, evidence=evidence)
    if saved := services._retry(CalibrationReinstatement, request_id, fields):
        return saved
    if hasattr(decision, "reinstatement"):
        raise RefusedError("This certificate decision has already been reinstated")
    if not movement(order, MovementKind.RETURNED, today):
        raise RefusedError("Record physical return before reinstating the tool")
    _validate_certificate(certificate, today, decision.internal_rule)
    tool = order.tool
    label = status.label(tool, grant.approval, grant.approval_reference, today, 0)
    if any(
        line.revision.kind != ControlKind.CALIBRATION
        and line.status in {"Completion evidence needed", "Overdue"}
        for line in label.controls
    ):
        raise RefusedError("Complete all other applicable controls before reinstating the tool")
    control = next(
        (line.revision for line in label.controls if line.revision.kind == ControlKind.CALIBRATION),
        None,
    )
    if (
        control is None
        or control.interval_months is None
        or not _same_calibration_scope(order.control, control)
    ):
        raise RefusedError("The current control scope must match the accepted calibration")
    due = add_months(certificate.calibrated_on, control.interval_months)
    if due < today:
        raise RefusedError("The accepted calibration is already overdue")
    if condition := label.condition:
        if condition.kind == EventKind.WITHDRAWN:
            raise RefusedError("The asset has been withdrawn")
        if condition.kind in status.RESTRICTIONS:
            if not tool.control_events.filter(
                kind=EventKind.REPAIRED,
                occurred_on__gte=condition.occurred_on,
                entered_at__gt=condition.entered_at,
            ).exists():
                raise RefusedError("Record rectification of the physical restriction first")
            ToolControlEvent.objects.create(
                organisation=organisation,
                tool=tool,
                delegation=grant,
                kind=EventKind.REINSTATED,
                occurred_on=today,
                signed_on=today,
                evidence=evidence,
                submission=request_id,
            )
    return CalibrationReinstatement.objects.create(
        submission=request_id,
        control=control,
        occurred_on=certificate.calibrated_on,
        due_on=due,
        signed_on=today,
        **fields,
    )
