"""Forms for the supplier register (REQ-340 to REQ-343)."""

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.logistics.models import SubcontractorOutcome, SupplierStatus
from airworthiness_plus.organisations.models import ApprovalType


class EvaluationForm(Form):
    approval = forms.ChoiceField(
        label="Approval",
        choices=[(kind, kind.label) for kind in (ApprovalType.PART_CAO, ApprovalType.PART_145)],
    )
    supplies = forms.CharField(label="Supplies", max_length=200)
    release_documents = forms.CharField(label="Release Documents", max_length=200, required=False)
    evaluated_on = forms.DateField(label="Evaluated On")
    next_evaluation_on = forms.DateField(label="Next Evaluation", required=False)
    status = forms.ChoiceField(label="Status", choices=SupplierStatus.choices)
    evidence = forms.CharField(label="Evaluation Evidence", max_length=2000, widget=forms.Textarea)


class NewSupplierForm(EvaluationForm):
    name = forms.CharField(label="Supplier", max_length=200)
    field_order = ["name"]


class SubcontractorAssessmentForm(Form):
    approval = forms.ChoiceField(
        label="Approval",
        choices=[(kind, kind.label) for kind in (ApprovalType.PART_CAO, ApprovalType.PART_145)],
    )
    assessed_on = forms.DateField(label="Assessed On")
    scope = forms.CharField(label="Scope of Work", max_length=240)
    exposition_reference = forms.CharField(
        label="Exposition Procedure and List Reference", max_length=160, required=False
    )
    qualification_evidence = forms.CharField(
        label="Qualification Evidence", max_length=240, required=False
    )
    controls = forms.CharField(
        label="Controls or Reasons for Suspension", max_length=2000, widget=forms.Textarea
    )
    pre_audit_reference = forms.CharField(
        label="Pre-Audit Reference",
        max_length=160,
        required=False,
        help_text="Required to record controls under Part-145.",
    )
    outcome = forms.ChoiceField(label="Outcome", choices=SubcontractorOutcome.choices)
