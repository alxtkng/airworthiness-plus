"""Forms for the workshop's equipment custody and evidence."""

from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.maintenance_data.models import Revision
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.tooling.calibration_forms import date_field, evidence_field
from airworthiness_plus.tooling.custody_models import (
    ReturnCondition,
    ToolIssue,
    ToolPreUseInspection,
)
from airworthiness_plus.tooling.forms import approval_field, submission_field


class AssignmentForm(Form):
    approval = approval_field()
    evidence = forms.CharField(label="Signed Approval Assignment Evidence", max_length=250)


class IssueForm(Form):
    request_id = submission_field()
    package = forms.ModelChoiceField(
        label="Issued Work Package", queryset=WorkPackage.objects.none()
    )
    custodian = forms.ModelChoiceField(
        label="Person Taking Custody", queryset=Person.objects.none()
    )
    location = forms.CharField(label="Custody Location", max_length=150)
    evidence = evidence_field("Signed Handover Evidence")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["package"].queryset = WorkPackage.objects.filter(  # type: ignore[attr-defined]
            issued_on__isnull=False, released_on__isnull=True
        )
        self.fields["custodian"].queryset = Person.objects.all()  # type: ignore[attr-defined]


class CardEvidenceForm(forms.Form):
    request_id = submission_field()
    card = forms.ModelChoiceField(label="Work Card", queryset=WorkCard.objects.none())
    revision = forms.ModelChoiceField(
        label="Maintenance Data Revision", queryset=Revision.objects.none()
    )

    def __init__(self, *args: Any, issue: ToolIssue, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cards = WorkCard.objects.filter(package_id=issue.work_approval.package_id)
        self.fields["card"].queryset = cards  # type: ignore[attr-defined]
        self.fields["revision"].queryset = Revision.objects.filter(  # type: ignore[attr-defined]
            data_set_id__in=cards.values("data_set_id"), current=True
        ).select_related("data_set")


class InspectionForm(CardEvidenceForm, Form):
    passed = forms.BooleanField(label="Inspection Satisfactory", required=False)
    evidence = evidence_field("Inspection Findings and Evidence")


class UseForm(CardEvidenceForm, Form):
    inspection = forms.ModelChoiceField(
        label="Inspection for This Use",
        queryset=ToolPreUseInspection.objects.none(),
        required=False,
    )
    configuration = forms.CharField(label="Actual Task Configuration", max_length=240)
    setting = forms.CharField(label="Setting and Units", max_length=120, required=False)
    evidence = evidence_field("Attributable Signed Use Evidence")

    def __init__(self, *args: Any, issue: ToolIssue, **kwargs: Any) -> None:
        super().__init__(*args, issue=issue, **kwargs)
        self.fields["inspection"].queryset = issue.inspections.all()  # type: ignore[attr-defined]


class ReturnForm(Form):
    request_id = submission_field()
    returned_by = forms.ModelChoiceField(
        label="Person Returning the Tool", queryset=Person.objects.none()
    )
    location = forms.CharField(label="Receiving Location", max_length=150)
    condition = forms.ChoiceField(label="Condition on Return", choices=ReturnCondition.choices)
    evidence = evidence_field("Handover and Condition Evidence")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["returned_by"].queryset = Person.objects.all()  # type: ignore[attr-defined]


class ClaimForm(Form):
    request_id = submission_field()
    occurred_on = date_field("Claimed Event Date")
    claim = forms.CharField(label="Reported Activity", max_length=240)
    attributed_to = forms.CharField(label="Person or Account Cited by the Source", max_length=150)
    subject = forms.CharField(label="Aircraft or Component as Reported", max_length=150)
    source = evidence_field("Original Source and Attribution")
    gaps = evidence_field("Missing or Disputed Evidence and Authority")
    card = forms.ModelChoiceField(
        label="Linked Work Card", queryset=WorkCard.objects.none(), required=False
    )
    work = forms.ModelChoiceField(
        label="Linked Maintenance Record", queryset=WorkDone.objects.none(), required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["card"].queryset = WorkCard.objects.all()  # type: ignore[attr-defined]
        self.fields["work"].queryset = WorkDone.objects.all()  # type: ignore[attr-defined]
