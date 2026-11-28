"""Read outcomes and the physical hold independently of historical case status."""

from datetime import date

from airworthiness_plus.tooling.calibration_models import (
    CalibrationCertificate,
    CalibrationMovement,
    CalibrationOrder,
    CalibrationReinstatement,
    CertificateDecision,
    DecisionOutcome,
    MovementKind,
)
from airworthiness_plus.tooling.models import Tool


def movement(order: CalibrationOrder, kind: MovementKind, day: date) -> CalibrationMovement | None:
    return next(
        (event for event in order.movements.all() if event.kind == kind and event.signed_on <= day),
        None,
    )


def latest_certificate(order: CalibrationOrder, day: date) -> CalibrationCertificate | None:
    return next((cert for cert in order.certificates.all() if cert.signed_on <= day), None)


def decision_on(certificate: CalibrationCertificate, day: date) -> CertificateDecision | None:
    return next((entry for entry in certificate.decisions.all() if entry.signed_on <= day), None)


def reinstatement_on(order: CalibrationOrder, day: date) -> CalibrationReinstatement | None:
    if (certificate := latest_certificate(order, day)) and (
        decision := decision_on(certificate, day)
    ):
        reinstatement = getattr(decision, "reinstatement", None)
        if (
            isinstance(reinstatement, CalibrationReinstatement)
            and reinstatement.signed_on <= day
            and decision.outcome == DecisionOutcome.ACCEPTED
        ):
            return reinstatement
    return None


def order_open(order: CalibrationOrder, day: date) -> bool:
    return order.signed_on <= day and reinstatement_on(order, day) is None


def holding_order(tool: Tool, day: date) -> CalibrationOrder | None:
    """Resolve the shared physical hold, whichever approval is displayed."""
    return next(
        (
            order
            for order in tool.calibration_orders.all()
            if order_open(order, day)
            and (
                movement(order, MovementKind.DESPATCHED, day) is not None
                or (hasattr(order, "impact_case") and order.impact_case.opened_on <= day)
            )
        ),
        None,
    )
