"""Provider scopes, calibration episodes and retained evidence."""

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from airworthiness_plus.tooling.models import SubmittedToolRecord, ToolRecord, unique_submission


class SignedCalibrationRecord(SubmittedToolRecord):
    delegation = models.ForeignKey(
        "tooling.ToolDelegation", on_delete=models.PROTECT, related_name="+"
    )
    signed_on = models.DateField()

    class Meta:
        abstract = True


class ProviderStatus(models.TextChoices):
    AUTHORISED = "Authorised", "Authorised"
    SUSPENDED = "Suspended", "Suspended"


class ProviderService(models.TextChoices):
    CALIBRATION = "Calibration", "Calibration"
    REPAIR = "Repair", "Repair"
    LOAN = "Loan", "Loan"


class ToolServiceProviderAuthorisation(SignedCalibrationRecord):
    """A dated tooling service scope at one facility for a held maintenance approval."""

    supplier = models.ForeignKey("logistics.Supplier", on_delete=models.PROTECT, related_name="+")
    service = models.CharField(
        max_length=16, choices=ProviderService.choices, default=ProviderService.CALIBRATION
    )
    facility = models.CharField(max_length=150)
    measurement = models.CharField(max_length=80, blank=True)
    method = models.CharField(max_length=150)
    unit = models.CharField(max_length=24, blank=True)
    range_from = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    range_to = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    valid_from = models.DateField()
    valid_to = models.DateField()
    review_on = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=ProviderStatus.choices)
    accreditation = models.CharField(max_length=150, blank=True)
    evidence = models.TextField(max_length=2000)

    class Meta:
        ordering = ["-valid_from", "-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(
                    valid_from__lte=F("valid_to"),
                    status__in=ProviderStatus.values,
                    service__in=ProviderService.values,
                )
                & (
                    Q(
                        range_from__isnull=False,
                        range_to__isnull=False,
                        range_from__lte=F("range_to"),
                    )
                    | (
                        ~Q(service=ProviderService.CALIBRATION)
                        & Q(range_from__isnull=True, range_to__isnull=True)
                    )
                ),
                name="tool_provider_dated_scope",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.supplier} · {self.facility} · {self.service} · {self.measurement} · "
            f"{self.method} · {self.unit}"
        )


class CalibrationOrder(SignedCalibrationRecord):
    """The ordered scope and its original control revision."""

    tool = models.ForeignKey(
        "tooling.Tool", on_delete=models.PROTECT, related_name="calibration_orders"
    )
    control = models.ForeignKey(
        "tooling.ToolControlRevision", on_delete=models.PROTECT, related_name="+"
    )
    provider = models.ForeignKey(ToolServiceProviderAuthorisation, on_delete=models.PROTECT)
    reference = models.CharField(max_length=60)
    measurement = models.CharField(max_length=80)
    unit = models.CharField(max_length=24)
    serial = models.CharField(max_length=100)
    component_ids = models.CharField(max_length=240, blank=True)
    range_from = models.DecimalField(max_digits=16, decimal_places=6)
    range_to = models.DecimalField(max_digits=16, decimal_places=6)
    points = models.JSONField(default=list)
    configuration = models.CharField(max_length=150)
    error_limit = models.DecimalField(max_digits=16, decimal_places=6)
    error_unit = models.CharField(max_length=30)
    limits_source = models.CharField(max_length=200)
    uncertainty_required = models.BooleanField(default=False)
    requested_rule = models.CharField(max_length=200, blank=True)
    reported_due_on = models.DateField(null=True, blank=True)
    reported_label_source = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.UniqueConstraint(
                Lower("reference"), "organisation", name="calibration_order_reference_once"
            ),
            models.CheckConstraint(
                condition=Q(range_from__lte=F("range_to"), error_limit__gt=0),
                name="calibration_order_has_range_and_limit",
            ),
        ]

    def __str__(self) -> str:
        return self.reference


class MovementKind(models.TextChoices):
    DESPATCHED = "Despatched", "Despatched"
    RETURNED = "Returned", "Returned"


class CalibrationMovement(SignedCalibrationRecord):
    order = models.ForeignKey(CalibrationOrder, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=16, choices=MovementKind.choices)
    occurred_on = models.DateField()
    expected_on = models.DateField(null=True, blank=True)
    evidence = models.TextField(max_length=2000)

    class Meta:
        ordering = ["-occurred_on", "-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.UniqueConstraint(
                fields=["order", "kind"], name="calibration_one_movement_of_kind"
            ),
            models.CheckConstraint(
                condition=Q(occurred_on__lte=F("signed_on"))
                & (
                    Q(
                        kind=MovementKind.DESPATCHED,
                        expected_on__isnull=False,
                        expected_on__gte=F("occurred_on"),
                    )
                    | Q(kind=MovementKind.RETURNED, expected_on__isnull=True)
                ),
                name="calibration_dates_match_movement",
            ),
        ]


class CalibrationCertificate(SignedCalibrationRecord):
    """The certificate identity, source and verbatim coverage evidence."""

    order = models.ForeignKey(
        CalibrationOrder, on_delete=models.PROTECT, related_name="certificates"
    )
    number = models.CharField(max_length=100)
    revision = models.CharField(max_length=80)
    source = models.CharField(max_length=240)
    calibrated_on = models.DateField()
    received_on = models.DateField()
    serial = models.CharField(max_length=100, blank=True)
    component_ids = models.CharField(max_length=240, blank=True)
    facility = models.CharField(max_length=150, blank=True)
    standard = models.CharField(max_length=160, blank=True)
    method = models.CharField(max_length=150, blank=True)
    configuration = models.CharField(max_length=150, blank=True)
    traceability = models.TextField(max_length=2000, blank=True)
    rule = models.TextField(max_length=2000, blank=True)
    adjustment = models.TextField(max_length=2000, blank=True)

    class Meta:
        ordering = ["-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.UniqueConstraint(
                Lower("number"),
                Lower("revision"),
                "order",
                name="calibration_certificate_revision_once",
            ),
            models.CheckConstraint(
                condition=Q(calibrated_on__lte=F("received_on"), received_on__lte=F("signed_on")),
                name="calibration_certificate_dates_in_order",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number}, {self.revision}"


class Phase(models.TextChoices):
    FOUND = "As found", "As Found"
    LEFT = "As left", "As Left"


class Statement(models.TextChoices):
    CONFORMS = "Conforming", "Conforming"
    FAILS = "Nonconforming", "Nonconforming"
    MEASUREMENT = "Measurement only", "Measurement Only"
    INCONCLUSIVE = "Inconclusive", "Inconclusive"


class CalibrationResult(SignedCalibrationRecord):
    certificate = models.ForeignKey(
        CalibrationCertificate, on_delete=models.PROTECT, related_name="results"
    )
    phase = models.CharField(max_length=12, choices=Phase.choices)
    reference_value = models.DecimalField(max_digits=16, decimal_places=6)
    measured_value = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    error = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    uncertainty = models.DecimalField(max_digits=16, decimal_places=6, null=True, blank=True)
    coverage = models.CharField(max_length=100, blank=True)
    convention = models.CharField(max_length=150, blank=True)
    statement = models.CharField(max_length=24, choices=Statement.choices)

    class Meta:
        ordering = ["phase", "reference_value"]
        constraints = [
            unique_submission(),
            models.UniqueConstraint(
                fields=["certificate", "phase", "reference_value"],
                name="calibration_point_once_per_phase",
            ),
            models.CheckConstraint(
                condition=Q(phase__in=Phase.values, statement__in=Statement.values)
                & (Q(uncertainty__isnull=True) | Q(uncertainty__gte=0)),
                name="calibration_point_has_known_phase_and_statement",
            ),
        ]


class DecisionOutcome(models.TextChoices):
    ACCEPTED = "Accepted", "Accepted"
    REJECTED = "Rejected", "Rejected"
    HELD = "Held", "Held"


class CertificateDecision(SignedCalibrationRecord):
    certificate = models.ForeignKey(
        CalibrationCertificate, on_delete=models.PROTECT, related_name="decisions"
    )
    outcome = models.CharField(max_length=12, choices=DecisionOutcome.choices)
    reason = models.TextField(max_length=2000)
    internal_rule = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ["-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(outcome__in=DecisionOutcome.values), name="calibration_known_decision"
            ),
        ]


class CalibrationReinstatement(SignedCalibrationRecord):
    """Authority to use the tool again after calibration under the linked scope."""

    decision = models.OneToOneField(
        CertificateDecision, on_delete=models.PROTECT, related_name="reinstatement"
    )
    control = models.ForeignKey(
        "tooling.ToolControlRevision", on_delete=models.PROTECT, related_name="+"
    )
    evidence = models.TextField(max_length=2000)
    occurred_on = models.DateField()
    due_on = models.DateField()

    class Meta:
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(occurred_on__lte=F("signed_on"), due_on__gte=F("signed_on")),
                name="calibration_reinstatement_has_current_dates",
            ),
        ]


class ToolImpactCase(ToolRecord):
    """One open case and retained trigger for one out-of-limits calibration episode."""

    order = models.OneToOneField(
        CalibrationOrder, on_delete=models.PROTECT, related_name="impact_case"
    )
    trigger = models.OneToOneField(
        CalibrationResult, on_delete=models.PROTECT, related_name="impact_case"
    )
    opened_on = models.DateField()
    provisional = models.BooleanField()
