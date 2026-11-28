"""Retained work-linked tool custody and verification evidence."""

from django.db import models
from django.db.models import Q

from airworthiness_plus.tooling.models import (
    EventKind,
    SubmittedToolRecord,
    ToolRecord,
    unique_submission,
)


class WorkPackageApproval(ToolRecord):
    package = models.OneToOneField(
        "planning.WorkPackage", on_delete=models.PROTECT, related_name="tooling_approval"
    )
    approval = models.ForeignKey(
        "organisations.Approval", on_delete=models.PROTECT, related_name="+"
    )
    reference = models.CharField(max_length=40)
    assigned_on = models.DateField()
    evidence = models.CharField(max_length=250)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(reference="") & ~Q(evidence=""),
                name="tooling_package_approval_has_evidence",
            )
        ]


class CustodyEvidence(SubmittedToolRecord):
    delegation = models.ForeignKey(
        "tooling.ToolDelegation", on_delete=models.PROTECT, related_name="+"
    )
    occurred_on = models.DateField()
    evidence = models.TextField()

    class Meta:
        abstract = True
        constraints = [
            unique_submission(),
            models.CheckConstraint(condition=~Q(evidence=""), name="%(class)s_has_evidence"),
        ]


class ToolIssue(CustodyEvidence):
    tool = models.ForeignKey("tooling.Tool", on_delete=models.PROTECT, related_name="issues")
    work_approval = models.ForeignKey(
        WorkPackageApproval, on_delete=models.PROTECT, related_name="issues"
    )
    custodian = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    location = models.CharField(max_length=150)
    controls = models.JSONField()

    class Meta(CustodyEvidence.Meta):
        ordering = ["-entered_at", "-id"]
        constraints = [
            *CustodyEvidence.Meta.constraints,
            models.CheckConstraint(condition=~Q(location=""), name="toolissue_has_location"),
        ]


class ToolPreUseInspection(CustodyEvidence):
    issue = models.ForeignKey(ToolIssue, on_delete=models.PROTECT, related_name="inspections")
    card = models.ForeignKey("planning.WorkCard", on_delete=models.PROTECT, related_name="+")
    revision = models.ForeignKey(
        "maintenance_data.Revision", on_delete=models.PROTECT, related_name="+"
    )
    control = models.ForeignKey(
        "tooling.ToolControlRevision", on_delete=models.PROTECT, related_name="+"
    )
    passed = models.BooleanField()

    class Meta(CustodyEvidence.Meta):
        ordering = ["-entered_at", "-id"]


class ToolUse(CustodyEvidence):
    issue = models.ForeignKey(ToolIssue, on_delete=models.PROTECT, related_name="uses")
    card = models.ForeignKey(
        "planning.WorkCard", on_delete=models.PROTECT, related_name="tool_uses"
    )
    revision = models.ForeignKey(
        "maintenance_data.Revision", on_delete=models.PROTECT, related_name="+"
    )
    aircraft_registration = models.CharField(max_length=20)
    inspection = models.OneToOneField(
        ToolPreUseInspection, on_delete=models.PROTECT, null=True, related_name="use"
    )
    configuration = models.CharField(max_length=240)
    setting = models.CharField(max_length=120, blank=True)
    controls = models.JSONField()

    class Meta(CustodyEvidence.Meta):
        ordering = ["entered_at", "id"]


class ReturnCondition(models.TextChoices):
    SATISFACTORY = "Satisfactory", "Satisfactory"
    UNSERVICEABLE = EventKind.UNSERVICEABLE, "Unserviceable"


class ToolReturn(CustodyEvidence):
    issue = models.OneToOneField(ToolIssue, on_delete=models.PROTECT, related_name="return_record")
    returned_by = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    location = models.CharField(max_length=150)
    kind = models.CharField(max_length=24, choices=ReturnCondition.choices)

    class Meta(CustodyEvidence.Meta):
        constraints = [
            *CustodyEvidence.Meta.constraints,
            models.CheckConstraint(
                condition=Q(kind__in=ReturnCondition.values) & ~Q(location=""),
                name="toolreturn_has_condition_and_location",
            ),
        ]


class HistoricalToolClaim(SubmittedToolRecord):
    """Evidence supplied after the event, including incomplete or conflicting claims."""

    tool = models.ForeignKey(
        "tooling.Tool", on_delete=models.PROTECT, related_name="historical_claims"
    )
    card = models.ForeignKey(
        "planning.WorkCard",
        on_delete=models.PROTECT,
        null=True,
        related_name="historical_tool_claims",
    )
    work = models.ForeignKey(
        "programme.WorkDone",
        on_delete=models.PROTECT,
        null=True,
        related_name="historical_tool_claims",
    )
    occurred_on = models.DateField()
    claim = models.CharField(max_length=240)
    attributed_to = models.CharField(max_length=150)
    subject = models.CharField(max_length=150)
    source = models.TextField()
    gaps = models.TextField()

    class Meta:
        ordering = ["-occurred_on", "-entered_at", "-id"]
        constraints = [
            unique_submission(),
            models.CheckConstraint(
                condition=~Q(claim="")
                & ~Q(attributed_to="")
                & ~Q(subject="")
                & ~Q(source="")
                & ~Q(gaps=""),
                name="historical_tool_claim_has_source_and_gaps",
            ),
        ]


class ReleaseGeneralVerification(ToolRecord):
    """Separate signed evidence of physical clearance and custody reconciliation."""

    release = models.OneToOneField(
        "releases.Release", on_delete=models.PROTECT, related_name="general_verification"
    )
    work_approval = models.ForeignKey(
        WorkPackageApproval, on_delete=models.PROTECT, null=True, related_name="+"
    )
    approval = models.ForeignKey(
        "organisations.Approval", on_delete=models.PROTECT, related_name="+"
    )
    approval_reference = models.CharField(max_length=40)
    rule = models.CharField(max_length=30)
    performed_on = models.DateField()
    panels = models.CharField(max_length=30)
    signed_evidence = models.CharField(max_length=240)
    accountability = models.TextField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=~Q(signed_evidence="")
                & ~Q(accountability="")
                & Q(panels__in=["All refitted", "None removed"])
                & Q(rule__in=["CAO.A.060(i)", "145.A.48(c)(1)"])
                & ~Q(approval_reference=""),
                name="general_verification_has_signed_findings",
            ),
        ]
