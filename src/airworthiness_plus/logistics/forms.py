"""Forms for the supplier register (REQ-340 to REQ-343)."""

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    DocumentKind,
    ItemClass,
    SubcontractorOutcome,
    SupplierStatus,
)
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.people.models import Person


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


class ReceiptForm(Form):
    item = forms.CharField(label="Item", max_length=200)
    received_on = forms.DateField(label="Received On")
    classification = forms.ChoiceField(label="Received Class", choices=ItemClass.choices)
    source = forms.CharField(label="Supplier or Owner Source", max_length=200)
    item_reference = forms.CharField(label="Part, Serial, Batch or Specification", max_length=200)
    quantity = forms.IntegerField(label="Quantity", min_value=1, max_value=2_147_483_647)
    delivery_reference = forms.CharField(label="Delivery Line Reference", max_length=100)
    release_document = forms.CharField(
        label="Release Document Shown on Arrival", max_length=200, required=False
    )
    intended_use = forms.CharField(
        label="Intended Aircraft or Work Package", max_length=200, required=False
    )
    shelf_life_to = forms.DateField(label="Shelf Life To", required=False)


class ReceivingCheckForm(Form):
    check = forms.ChoiceField(label="Check", choices=CheckKind.choices)
    outcome = forms.ChoiceField(label="Result", choices=CheckOutcome.choices)
    checked_on = forms.DateField(label="Checked On")
    evidence = forms.CharField(
        label="What Was Checked and the Evidence", max_length=1000, widget=forms.Textarea
    )


class ReceivingDispositionForm(Form):
    approval = forms.ChoiceField(
        label="Maintenance Approval",
        choices=[(kind, kind.label) for kind in (ApprovalType.PART_CAO, ApprovalType.PART_145)],
    )
    inspector = forms.ModelChoiceField(label="Receiving Inspector", queryset=Person.objects.all())
    inspector_authority = forms.CharField(label="Inspector Authorisation Evidence", max_length=200)
    inspected_on = forms.DateField(label="Inspection Decision On")
    disposition_on = forms.DateField(label="Moved or Returned On")
    outcome = forms.ChoiceField(label="Disposition", choices=Destination.choices)
    destination = forms.CharField(
        label="Store, Quarantine Location or Return Recipient", max_length=200
    )
    evidence = forms.CharField(
        label="Decision Reason and Movement Evidence", max_length=1000, widget=forms.Textarea
    )
    document_kind = forms.ChoiceField(
        label="Evidence Type",
        choices=[("", "Choose an evidence type"), *DocumentKind.choices],
        required=False,
        help_text="Required for Stores. Select the evidence that was checked.",
    )
    document_reference = forms.CharField(
        label="Evidence Reference",
        max_length=200,
        required=False,
        help_text=(
            "Give the reference where the checked release, conformity statement "
            "or exception evidence can be retrieved."
        ),
    )
    evidence_basis = forms.CharField(
        label="Standard, Specification or Regulatory Basis",
        max_length=200,
        required=False,
        help_text=(
            "For conformity, give the applicable standard or specification. "
            "For an equivalent release or exception, give the agreement or rule relied on."
        ),
    )
    manufacturing_source = forms.CharField(
        label="Manufacturing Source",
        max_length=200,
        required=False,
        help_text="For material, give the manufacturing source stated on the conformity evidence.",
    )
    material_supplier_source = forms.CharField(
        label="Supplier Source on Material Evidence",
        max_length=200,
        required=False,
        help_text="For material, give the supplier source stated on the conformity evidence.",
    )


class StoresExerciseForm(Form):
    question = forms.CharField(label="Exercise Question", widget=forms.HiddenInput)
    quantity = forms.IntegerField(min_value=0, label="Quantity")
