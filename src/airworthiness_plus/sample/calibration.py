"""Illustrative C06 and C07 custody records for the marked test site."""

from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.session import working_for
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.organisations.models import ApprovalType, Organisation
from airworthiness_plus.people.models import Person
from airworthiness_plus.sample.tools import DAY, SITE, submission
from airworthiness_plus.tooling.calibration_models import (
    CalibrationCertificate,
    CalibrationMovement,
    CalibrationOrder,
    CertificateDecision,
    DecisionOutcome,
    MovementKind,
    ProviderStatus,
    ToolServiceProviderAuthorisation,
)
from airworthiness_plus.tooling.models import (
    ControlKind,
    Tool,
    ToolAction,
    ToolControlRevision,
    ToolDelegation,
)


def add(organisation: Organisation, administrator: User) -> int:
    """Add the board's reported dates and evidence gaps once."""
    if organisation.approval_reference != "UK.CAO.[Number]":
        return 0
    with working_for(organisation.pk, administrator.pk), transaction.atomic():
        organisation = Organisation.objects.select_for_update(no_key=True).get(pk=organisation.pk)
        if CalibrationOrder.objects.filter(organisation=organisation).exists():
            return 0
        if Tool.objects.filter(organisation=organisation, asset_id__in=("0143", "0160")).exists():
            return 0
        supplier = Supplier.objects.filter(
            organisation=organisation,
            name="[Calibration Laboratory]",
        ).first()
        signer = (
            Person.objects.select_related("user")
            .filter(
                organisation=organisation,
                user__username="lucy.grant@your-organisation.example",
            )
            .first()
        )
        term = organisation.approvals.filter(approval=ApprovalType.PART_CAO).first()
        reference = term.reference_on(DAY) if term else None
        if not supplier or not signer or not signer.user or not term or not reference:
            return 0
        grants = {
            action: ToolDelegation.objects.get_or_create(
                organisation=organisation,
                submission=submission(action),
                defaults={
                    "person": signer,
                    "approval": term,
                    "approval_reference": reference,
                    "action": action,
                    "site": SITE,
                    "starts_on": DAY,
                    "ends_on": date(2099, 12, 31),
                    "procedure": "Fictitious sample exposition, C.3, demonstration revision",
                    "authority": "Fictitious example of a signed site delegation",
                },
            )[0]
            for action in (
                ToolAction.REGISTER,
                ToolAction.CONTROL,
                ToolAction.PROVIDER,
                ToolAction.ORDER,
                ToolAction.RECEIPT,
                ToolAction.RESULT,
                ToolAction.CERTIFICATE,
                ToolAction.REINSTATE,
            )
        }
        with working_for(organisation.pk, signer.user.pk):
            _sample_order(supplier, grants, torque=True)
            _sample_order(supplier, grants, torque=False)
        return 2


def _sample_order(
    supplier: Supplier, grants: dict[ToolAction, ToolDelegation], *, torque: bool
) -> None:
    # The board supplies the torque range and dates. Electrical scope, hardware serials
    # and authorisation references are illustrative only. Neither certificate is accepted.
    organisation = supplier.organisation
    asset, reference = ("0143", "2026-C07") if torque else ("0160", "2026-C06")
    start, end = (Decimal(4), Decimal(20)) if torque else (Decimal(1), Decimal(10))
    unit, measurement = ("Nm", "Torque") if torque else ("V", "Voltage")
    signed = {"organisation": organisation, "signed_on": DAY}
    tool = Tool.objects.create(
        organisation=organisation,
        submission=submission(asset),
        asset_id=asset,
        description="Torque Wrench" if torque else "Digital Multimeter",
        site=SITE,
        location="Tool Board" if torque else "Quarantine Shelf",
        serial=f"DEMO-{asset}",
        owner="Organisation",
        registered_on=DAY,
        delegation=grants[ToolAction.REGISTER],
        measurement_range=f"{start} to {end} {unit}",
    )
    basis = ToolControlRevision.objects.create(
        organisation=organisation,
        submission=submission(f"{asset}/basis"),
        tool=tool,
        delegation=grants[ToolAction.CONTROL],
        effective_on=DAY,
        kind=ControlKind.CALIBRATION,
        interval_months=12 if torque else 24,
        instruction="Fictitious tooling board",
        instruction_revision="18 November 2026 board",
        method="Illustrative order method",
        limits="Refer to the controlled order",
        standard="Demonstration standard reference",
        scope=f"Demonstration {measurement} range",
        decision_basis="Board example for the sample site",
    )
    provider = ToolServiceProviderAuthorisation.objects.create(
        **signed,
        submission=submission(f"{asset}/provider"),
        delegation=grants[ToolAction.PROVIDER],
        supplier=supplier,
        facility="Fictitious Laboratory Facility",
        measurement=measurement,
        unit=unit,
        method="Illustrative order method",
        range_from=start,
        range_to=end,
        valid_from=date(2026, 10, 1),
        valid_to=date(2027, 1, 11),
        status=ProviderStatus.AUTHORISED,
        evidence="Fictitious sample provider scope schedule",
    )
    order = CalibrationOrder.objects.create(
        **signed,
        submission=submission(reference),
        delegation=grants[ToolAction.ORDER],
        tool=tool,
        provider=provider,
        control=basis,
        reference=reference,
        serial=tool.serial,
        measurement=measurement,
        unit=unit,
        range_from=start,
        range_to=end,
        points=[str(start), str(end)],
        configuration="Illustrative scope",
        error_limit=Decimal(4),
        error_unit="Percent",
        limits_source="Demonstration only",
        reported_due_on=date(2026, 11, 20) if torque else None,
        reported_label_source="Tools board, reported label deadline" if torque else "",
    )
    CalibrationMovement.objects.create(
        **signed,
        submission=submission(f"{reference}/despatch"),
        delegation=grants[ToolAction.RECEIPT],
        order=order,
        kind=MovementKind.DESPATCHED,
        evidence="Despatch on the fictitious Providers board",
        occurred_on=date(2026, 11, 14) if torque else date(2026, 10, 13),
        expected_on=date(2026, 11, 28) if torque else date(2026, 10, 27),
    )
    if torque:
        return
    CalibrationMovement.objects.create(
        **signed,
        submission=submission(f"{reference}/return"),
        delegation=grants[ToolAction.RECEIPT],
        order=order,
        kind=MovementKind.RETURNED,
        evidence="Physical return on the fictitious Tools board",
        occurred_on=date(2026, 10, 27),
    )
    certificate = CalibrationCertificate.objects.create(
        **signed,
        submission=submission(f"{reference}/certificate"),
        delegation=grants[ToolAction.RESULT],
        order=order,
        number="DEMO-C06",
        revision="1",
        source="Fictitious C06 certificate example",
        calibrated_on=date(2026, 10, 26),
        received_on=date(2026, 10, 27),
        serial=tool.serial,
        facility=provider.facility,
        standard=basis.standard,
        method=provider.method,
        configuration=order.configuration,
    )
    CertificateDecision.objects.create(
        **signed,
        submission=submission(f"{reference}/decision"),
        delegation=grants[ToolAction.CERTIFICATE],
        certificate=certificate,
        outcome=DecisionOutcome.REJECTED,
        reason=(
            "Certificate lacks traceability. The board records that a correction "
            "was requested on 29 October."
        ),
    )
