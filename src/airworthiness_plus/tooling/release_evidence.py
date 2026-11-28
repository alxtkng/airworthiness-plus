"""Require and retain signed verification at organisation release entry points."""

from dataclasses import dataclass
from datetime import date

from airworthiness_plus.organisations.models import Approval, ApprovalType
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.releases.models import Release
from airworthiness_plus.tooling import custody
from airworthiness_plus.tooling.custody_models import (
    ReleaseGeneralVerification,
    ToolIssue,
    WorkPackageApproval,
)


@dataclass(frozen=True)
class Verification:
    approval: str
    performed_on: date | None
    cleared: bool
    panels: str
    signed_evidence: str
    accountability: str


@dataclass(frozen=True)
class CheckedVerification:
    evidence: Verification
    approval: Approval
    reference: str
    package_approval: WorkPackageApproval | None
    performed_on: date

    def retain(self, release: Release) -> None:
        rule = (
            "CAO.A.060(i)" if self.approval.approval == ApprovalType.PART_CAO else "145.A.48(c)(1)"
        )
        ReleaseGeneralVerification.objects.create(
            organisation_id=release.organisation_id,
            release=release,
            work_approval=self.package_approval,
            approval=self.approval,
            approval_reference=self.reference,
            rule=rule,
            performed_on=self.performed_on,
            panels=self.evidence.panels,
            signed_evidence=self.evidence.signed_evidence.strip(),
            accountability=self.evidence.accountability.strip(),
        )


def check(
    work: WorkDone,
    issued_on: date,
    evidence: Verification | None,
    package: WorkPackage | None,
) -> CheckedVerification:
    if (
        evidence is None
        or evidence.performed_on is None
        or not evidence.cleared
        or not evidence.signed_evidence.strip()
        or not evidence.accountability.strip()
        or evidence.panels not in {"All refitted", "None removed"}
    ):
        raise custody.RefusedError(
            "Record signed physical general verification and tool accountability"
        )
    assignment = None
    if package is not None:
        if (package.aircraft_id, package.organisation_id) != (
            work.aircraft_id,
            work.organisation_id,
        ):
            raise custody.RefusedError("The release work must belong to the work package")
        assignment = (
            WorkPackageApproval.objects.filter(package=package).select_related("approval").first()
        )
        if assignment is None:
            raise custody.RefusedError(
                "Record the governing maintenance approval on the work package"
            )
        if evidence.approval and evidence.approval != assignment.approval.approval:
            raise custody.RefusedError("General verification must use the work package approval")
        if (
            assignment.assigned_on > issued_on
            or assignment.approval.reference_on(issued_on) != assignment.reference
        ):
            raise custody.RefusedError(
                "The governing maintenance approval must cover the release date"
            )
        approval, reference = assignment.approval, assignment.reference
    else:
        approval, reference = custody.select_approval(
            work.organisation, evidence.approval, issued_on
        )
    if not work.dated <= evidence.performed_on <= issued_on:
        raise custody.RefusedError(
            "General verification must follow maintenance and precede release"
        )
    if package and (
        package.cards.filter(completed_on__gt=evidence.performed_on).exists()
        or package.cards.filter(inspected_on__gt=evidence.performed_on).exists()
    ):
        raise custody.RefusedError("General verification must follow maintenance and inspection")
    if (
        ToolIssue.objects.filter(
            work_approval__package__aircraft_id=work.aircraft_id,
            occurred_on__lte=issued_on,
        )
        .exclude(return_record__occurred_on__lte=evidence.performed_on)
        .exists()
    ):
        raise custody.RefusedError("Account for every open tool issue before general verification")
    return CheckedVerification(evidence, approval, reference, assignment, evidence.performed_on)
