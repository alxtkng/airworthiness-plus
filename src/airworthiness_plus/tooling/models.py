"""Physical tools and the dated evidence behind their labels (REQ-360 to REQ-363)."""

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from airworthiness_plus.history.models import Record


class ToolAction(models.TextChoices):
    REGISTER = "Register", "Register a Tool"
    CONTROL = "Control", "Approve a Control Basis"
    EVIDENCE = "Evidence", "Accept Control Evidence"
    CONDITION = "Condition", "Record Tool Condition"
    REINSTATE = "Reinstate", "Authorise Return to Use"


class ControlKind(models.TextChoices):
    CALIBRATION = "Calibration", "Calibration"
    SERVICING = "Servicing", "Servicing"
    BEFORE_USE = "Before each use", "Before each use"


class EventKind(models.TextChoices):
    CALIBRATED = "Calibration completed", "Calibration completed"
    SERVICED = "Servicing completed", "Servicing completed"
    INSPECTED = "Pre-use inspection", "Pre-use inspection"
    INTERIM_PASS = "Interim check passed", "Interim check passed"
    INTERIM_FAIL = "Interim check failed", "Interim check failed"
    UNSERVICEABLE = "Unserviceable", "Unserviceable"
    REPAIRED = "Repair completed", "Repair completed"
    REINSTATED = "Return to use", "Return to use"
    WITHDRAWN = "Withdrawn", "Withdrawn"


class ToolRecord(Record):
    organisation = models.ForeignKey(
        "organisations.Organisation", on_delete=models.PROTECT, related_name="+"
    )
    entered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


def unique_submission() -> models.UniqueConstraint:
    return models.UniqueConstraint(
        fields=["organisation", "submission"], name="%(class)s_unique_submission"
    )


class SubmittedToolRecord(ToolRecord):
    submission = models.UUIDField()

    class Meta:
        abstract = True


class ToolDelegation(SubmittedToolRecord):
    """Recorded evidence of a person's existing authority under an exposition."""

    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    approval = models.ForeignKey("organisations.Approval", on_delete=models.PROTECT)
    approval_reference = models.CharField(max_length=40)
    action = models.CharField(max_length=12, choices=ToolAction.choices)
    site = models.CharField(max_length=100)
    starts_on = models.DateField()
    ends_on = models.DateField()
    procedure = models.CharField(max_length=200)
    authority = models.TextField()

    class Meta:
        ordering = ["person__full_name", "action", "-starts_on", "-entered_at"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(ends_on__gte=F("starts_on"))
                & Q(action__in=ToolAction.values)
                & ~Q(site="")
                & ~Q(procedure="")
                & ~Q(authority="")
                & ~Q(approval_reference=""),
                name="tooling_delegation_has_valid_scope_and_evidence",
            ),
        ]


class ToolDelegationWithdrawal(ToolRecord):
    delegation = models.OneToOneField(
        ToolDelegation, on_delete=models.PROTECT, related_name="withdrawal"
    )
    withdrawn_on = models.DateField()
    evidence = models.TextField()


class Tool(SubmittedToolRecord):
    """A single asset identity shared by the organisation's maintenance approvals."""

    asset_id = models.CharField(max_length=50)
    description = models.CharField(max_length=150)
    manufacturer = models.CharField(max_length=120, blank=True)
    model = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, blank=True)
    serial = models.CharField(max_length=100, blank=True)
    component_ids = models.CharField(max_length=240, blank=True)
    is_assembly = models.BooleanField(default=False)
    measurement_range = models.CharField(max_length=120, blank=True)
    owner = models.CharField(max_length=150, blank=True)
    lender = models.CharField(max_length=150, blank=True)
    site = models.CharField(max_length=100)
    location = models.CharField(max_length=150)
    notes = models.TextField(blank=True)
    registered_on = models.DateField()
    delegation = models.ForeignKey(ToolDelegation, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["asset_id", "id"]
        constraints = [
            unique_submission(),
            models.UniqueConstraint(
                Lower("asset_id"), "organisation", name="tooling_unique_asset_in_organisation"
            ),
            models.CheckConstraint(
                condition=~Q(asset_id="")
                & ~Q(description="")
                & ~Q(site="")
                & ~Q(location="")
                & (~Q(owner="") | ~Q(lender="")),
                name="tooling_asset_has_identity_and_location",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.description} {self.asset_id}"


class ToolControlRevision(SubmittedToolRecord):
    """One version of one applicable control under a maintenance approval."""

    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name="control_revisions")
    delegation = models.ForeignKey(ToolDelegation, on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=20, choices=ControlKind.choices)
    effective_on = models.DateField()
    interval_months = models.PositiveSmallIntegerField(null=True, blank=True)
    instruction = models.CharField(max_length=200)
    instruction_revision = models.CharField(max_length=80)
    method = models.TextField()
    limits = models.TextField()
    decision_basis = models.TextField()
    scope = models.TextField()
    standard = models.CharField(max_length=160, blank=True)
    loan_task = models.CharField(max_length=240, blank=True)
    loan_evidence = models.CharField(max_length=240, blank=True)
    loan_identity = models.CharField(max_length=350, blank=True)

    class Meta:
        ordering = ["-effective_on", "-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(kind=ControlKind.BEFORE_USE, interval_months__isnull=True)
                | Q(
                    kind__in=[ControlKind.CALIBRATION, ControlKind.SERVICING],
                    interval_months__isnull=False,
                    interval_months__gt=0,
                ),
                name="tooling_interval_matches_control",
            ),
            models.CheckConstraint(
                condition=(~Q(kind=ControlKind.CALIBRATION) | ~Q(standard=""))
                & ~Q(instruction="")
                & ~Q(instruction_revision="")
                & ~Q(method="")
                & ~Q(limits="")
                & ~Q(scope="")
                & ~Q(decision_basis=""),
                name="tooling_control_has_sources_and_acceptance_basis",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.kind} · {self.delegation.approval.approval} · "
            f"{self.instruction} ({self.instruction_revision})"
        )


class ToolControlEvent(SubmittedToolRecord):
    """A dated observation, completion or physical condition decision."""

    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name="control_events")
    delegation = models.ForeignKey(ToolDelegation, on_delete=models.PROTECT, related_name="+")
    control = models.ForeignKey(
        ToolControlRevision, on_delete=models.PROTECT, null=True, blank=True, related_name="events"
    )
    kind = models.CharField(max_length=24, choices=EventKind.choices)
    occurred_on = models.DateField()
    signed_on = models.DateField()
    evidence = models.TextField()
    reference_instrument = models.CharField(max_length=120, blank=True)
    result = models.CharField(max_length=160, blank=True)
    limit = models.CharField(max_length=160, blank=True)

    class Meta:
        ordering = ["-occurred_on", "-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=Q(occurred_on__lte=F("signed_on")) & ~Q(evidence=""),
                name="tooling_event_has_dated_evidence",
            ),
            models.CheckConstraint(
                condition=(
                    Q(kind__in=EventKind.values[:5], control__isnull=False)
                    | Q(kind__in=EventKind.values[5:], control__isnull=True)
                ),
                name="tooling_event_control_matches_kind",
            ),
            models.CheckConstraint(
                condition=~Q(kind__in=[EventKind.INTERIM_PASS, EventKind.INTERIM_FAIL])
                | (~Q(reference_instrument="") & ~Q(result="") & ~Q(limit="")),
                name="tooling_interim_has_measurement_evidence",
            ),
        ]
