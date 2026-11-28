"""Forms for suppliers, Goods In and Stores (REQ-340 to REQ-358)."""

from typing import Any
from uuid import uuid4

from django import forms
from django.db.models import QuerySet

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.logistics.models import (
    CheckKind,
    CheckOutcome,
    Destination,
    DocumentKind,
    ItemClass,
    LocationKind,
    ShelfLifeBasis,
    StockUnit,
    StoresAction,
    StoresLocation,
    SubcontractorOutcome,
    SupplierStatus,
)
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning.models import WorkCard


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


# Stores (REQ-358)

DATE = forms.DateInput(attrs={"type": "date"})
MAINTENANCE = [(kind.value, kind.label) for kind in (ApprovalType.PART_CAO, ApprovalType.PART_145)]


def submission_field() -> forms.UUIDField:
    return forms.UUIDField(label="Submission Reference", widget=forms.HiddenInput, initial=uuid4)


def quantity_field(label: str, *, required: bool = True) -> forms.DecimalField:
    return forms.DecimalField(
        label=label,
        max_digits=13,
        decimal_places=3,
        required=required,
        help_text="Whole numbers for Each. Up to three decimal places for litres.",
    )


class StoresAppointmentForm(Form):
    request_id = submission_field()
    approval = forms.ChoiceField(label="Maintenance Approval", choices=MAINTENANCE)
    person = forms.ModelChoiceField(label="Person", queryset=Person.objects.none())
    action = forms.ChoiceField(label="Stores Action", choices=StoresAction.choices)
    starts_on = forms.DateField(label="First Day", widget=DATE)
    ends_on = forms.DateField(label="Last Day", widget=DATE)
    exposition_reference = forms.CharField(
        label="Exposition Procedure and Revision", max_length=200
    )
    authority = forms.CharField(
        label="Signed Appointment Reference and Scope", max_length=1000, widget=forms.Textarea
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        people: QuerySet[Person] = Person.objects.filter(user__isnull=False)
        self.fields["person"].queryset = people  # type: ignore[attr-defined]


class StoresWithdrawalForm(Form):
    request_id = submission_field()
    evidence = forms.CharField(label="Reason and Evidence", max_length=1000, widget=forms.Textarea)


class StoresLocationForm(Form):
    request_id = submission_field()
    code = forms.CharField(label="Location Code", max_length=40)
    name = forms.CharField(label="Location", max_length=200)
    kind = forms.ChoiceField(label="Use", choices=LocationKind.choices)
    classes = forms.MultipleChoiceField(
        label="Classes Held", choices=ItemClass.choices, widget=forms.CheckboxSelectMultiple
    )
    storage_conditions = forms.CharField(
        label="Storage Conditions",
        max_length=300,
        help_text="The manufacturer's and the procedure's conditions this location meets.",
    )
    secure = forms.BooleanField(
        label="Secure and Segregated",
        required=False,
        help_text="Required for quarantine.",
    )


def _locations(queryset: QuerySet[StoresLocation] | None) -> QuerySet[StoresLocation]:
    return queryset if queryset is not None else StoresLocation.objects.none()


class PostingEvidenceForm(Form):
    request_id = submission_field()
    assessed_on = forms.DateField(label="Assessed On", widget=DATE)
    unit = forms.ChoiceField(
        label="Unit", choices=[("", "Not Resolved"), *StockUnit.choices], required=False
    )
    quantity = quantity_field("Quantity", required=False)
    manufacturer = forms.CharField(label="Manufacturer", max_length=120, required=False)
    part_number = forms.CharField(label="Part Number", max_length=100, required=False)
    serial = forms.CharField(label="Serial Number", max_length=100, required=False)
    batch = forms.CharField(label="Batch or Lot", max_length=100, required=False)
    specification = forms.CharField(
        label="Standard or Specification", max_length=160, required=False
    )
    shelf_life_basis = forms.ChoiceField(
        label="Shelf-Life Basis",
        choices=[("", "Unknown"), *ShelfLifeBasis.choices],
        required=False,
        help_text="From the manufacturer's label or instructions. A date alone is not a basis.",
    )
    shelf_life_to = forms.DateField(label="Shelf-Life Date", required=False, widget=DATE)
    location = forms.ModelChoiceField(
        label="Location", queryset=StoresLocation.objects.none(), required=False
    )
    tag = forms.CharField(label="Quarantine Tag", max_length=100, required=False)
    evidence = forms.CharField(
        label="Original Records and Evidence Relied On", max_length=2000, widget=forms.Textarea
    )

    def __init__(
        self, *args: Any, locations: QuerySet[StoresLocation] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = _locations(locations)  # type: ignore[attr-defined]


class StockPostingForm(Form):
    request_id = submission_field()


class StockMovementForm(Form):
    request_id = submission_field()
    source = forms.ModelChoiceField(label="From", queryset=StoresLocation.objects.none())
    destination = forms.ModelChoiceField(label="To", queryset=StoresLocation.objects.none())
    quantity = quantity_field("Quantity to Move")
    moved_on = forms.DateField(label="Moved On", widget=DATE)
    evidence = forms.CharField(label="Movement Evidence", max_length=1000, widget=forms.Textarea)

    def __init__(
        self,
        *args: Any,
        sources: QuerySet[StoresLocation] | None = None,
        destinations: QuerySet[StoresLocation] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["source"].queryset = _locations(sources)  # type: ignore[attr-defined]
        self.fields["destination"].queryset = _locations(destinations)  # type: ignore[attr-defined]


class StockCountForm(Form):
    request_id = submission_field()
    location = forms.ModelChoiceField(label="Location", queryset=StoresLocation.objects.none())
    counted = forms.DecimalField(
        label="Counted Quantity", max_digits=13, decimal_places=3, min_value=0
    )
    evidence = forms.CharField(label="Count Evidence", max_length=1000, widget=forms.Textarea)

    def __init__(
        self, *args: Any, locations: QuerySet[StoresLocation] | None = None, **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["location"].queryset = _locations(locations)  # type: ignore[attr-defined]


class StockAdjustmentForm(Form):
    request_id = submission_field()
    evidence = forms.CharField(
        label="Adjustment Authority and Evidence", max_length=1000, widget=forms.Textarea
    )


class AllocationForm(Form):
    request_id = submission_field()
    evidence = forms.CharField(label="Custody Evidence", max_length=1000, widget=forms.Textarea)


class AllocationCardChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: WorkCard) -> str:
        return f"{obj.package.reference} · {obj.package.aircraft.registration} · {obj.title}"


class ReserveAllocationForm(AllocationForm):
    field_order = [
        "source",
        "card",
        "quantity",
        "required_identity",
        "applicable_source",
        "evidence",
    ]

    source = forms.ModelChoiceField(label="Source Location", queryset=StoresLocation.objects.all())
    card = AllocationCardChoice(
        label="Work Card",
        queryset=WorkCard.objects.select_related("package__aircraft"),
    )
    quantity = quantity_field("Quantity to Reserve")
    required_identity = forms.CharField(
        label="Required Part Number or Specification", max_length=100
    )
    applicable_source = forms.CharField(
        label="Applicable Parts Data Reference and Revision", max_length=300
    )


class ReturnAllocationForm(AllocationForm):
    field_order = ["destination", "evidence"]

    destination = forms.ModelChoiceField(
        label="Secure Quarantine Location",
        queryset=StoresLocation.objects.filter(
            kind=LocationKind.QUARANTINE, secure=True, withdrawal__isnull=True
        ),
    )


class QuarantineAllocationForm(ReturnAllocationForm):
    field_order = ["source", "destination", "quantity", "evidence"]

    source = forms.ModelChoiceField(label="Source Location", queryset=StoresLocation.objects.all())
    quantity = quantity_field("Quantity to Quarantine")
