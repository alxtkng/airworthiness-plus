"""Supplier identities and append-only evaluation evidence (REQ-340 to REQ-342)."""

from django.db import models
from django.db.models import F, Q
from django.db.models.functions import Lower

from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Approval, Organisation


class SupplierStatus(models.TextChoices):
    APPROVED = "Approved", "Approved"
    SUSPENDED = "Suspended", "Suspended"
    NOT_APPROVED = "Not Approved", "Not Approved"


class Supplier(Record):
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    name = models.CharField("Supplier", max_length=200)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "organisation", name="supplier_name_once_per_organisation"
            ),
            models.CheckConstraint(condition=~Q(name=""), name="supplier_has_a_name"),
        ]

    def __str__(self) -> str:
        return self.name


class SupplierEvaluation(Record):
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="evaluations")
    approval = models.ForeignKey(Approval, on_delete=models.PROTECT, related_name="+")
    approval_reference = models.CharField("Approval Reference", max_length=40)
    supplies = models.CharField("Supplies", max_length=200)
    release_documents = models.CharField("Release Documents", max_length=200, blank=True)
    evaluated_on = models.DateField("Evaluated On")
    next_evaluation_on = models.DateField("Next Evaluation", null=True, blank=True)
    status = models.CharField("Status", max_length=20, choices=SupplierStatus.choices)
    evidence = models.TextField("Evaluation Evidence", max_length=2000)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-evaluated_on", "-recorded_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=SupplierStatus.values) & ~Q(supplies="") & ~Q(evidence=""),
                name="supplier_evaluation_has_evidence",
            ),
            models.CheckConstraint(
                condition=Q(next_evaluation_on__isnull=True)
                | Q(next_evaluation_on__gt=F("evaluated_on")),
                name="supplier_next_evaluation_is_later",
            ),
            models.CheckConstraint(
                condition=~Q(status=SupplierStatus.APPROVED) | Q(next_evaluation_on__isnull=False),
                name="approved_supplier_has_next_evaluation",
            ),
        ]


class SubcontractorOutcome(models.TextChoices):
    CONTROLS_RECORDED = "Controls Recorded", "Controls Recorded"
    SUSPENDED = "Suspended", "Suspended"


class SubcontractorAssessment(Record):
    """The dated evidence for work under the receiving organisation's approval."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    supplier = models.ForeignKey(
        Supplier, on_delete=models.PROTECT, related_name="subcontractor_assessments"
    )
    approval = models.ForeignKey(Approval, on_delete=models.PROTECT, related_name="+")
    approval_reference = models.CharField("Approval Reference", max_length=40)
    assessed_on = models.DateField("Assessed On")
    scope = models.CharField("Scope of Work", max_length=240)
    exposition_reference = models.CharField(
        "Exposition Procedure and List Reference", max_length=160, blank=True
    )
    qualification_evidence = models.CharField("Qualification Evidence", max_length=240, blank=True)
    controls = models.TextField("Controls or Reasons for Suspension", max_length=2000)
    pre_audit_reference = models.CharField("Pre-Audit Reference", max_length=160, blank=True)
    outcome = models.CharField("Outcome", max_length=20, choices=SubcontractorOutcome.choices)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-assessed_on", "-recorded_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(outcome__in=SubcontractorOutcome.values)
                & ~Q(scope="")
                & ~Q(controls="")
                & (
                    ~Q(outcome=SubcontractorOutcome.CONTROLS_RECORDED)
                    | (~Q(exposition_reference="") & ~Q(qualification_evidence=""))
                ),
                name="subcontractor_assessment_has_evidence",
            ),
        ]


class ItemClass(models.TextChoices):
    SERVICEABLE = "Serviceable Component", "Serviceable Component"
    UNSERVICEABLE = "Unserviceable Component", "Unserviceable Component"
    UNSALVAGEABLE = "Unsalvageable Component", "Unsalvageable Component"
    STANDARD = "Standard Part", "Standard Part"
    MATERIAL = "Material", "Material"


class DocumentKind(models.TextChoices):
    CAA_FORM_1 = "CAA Form 1", "CAA Form 1"
    EQUIVALENT = "Equivalent Release", "Equivalent Release"
    EXCEPTION = "Permitted Exception", "Permitted Exception"
    CONFORMITY = "Conformity Evidence", "Conformity Evidence"


class CheckKind(models.TextChoices):
    SOURCE = "Supplier", "Supplier"
    DOCUMENT = "Release Document", "Release Document"
    IDENTITY = "Part Number and Modification Status", "Part Number and Modification Status"
    CONDITION = "Condition and Packaging", "Condition and Packaging"
    SHELF = "Shelf Life", "Shelf Life"
    SUSPECT = "Suspected Unapproved Part Checks", "Suspected Unapproved Part Checks"


class CheckOutcome(models.TextChoices):
    PASS = "Pass", "Pass"
    FAIL = "Fail", "Fail"
    NOT_APPLICABLE = "Not Applicable", "Not Applicable"


class Destination(models.TextChoices):
    STORES = "Accepted into Stores", "Accepted into Stores"
    RETURN = "Returned to Supplier", "Returned to Supplier"
    QUARANTINE = "Quarantined", "Quarantined"


class Receipt(Record):
    """What arrived, with its source and as-received classification."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    item = models.CharField("Item", max_length=200)
    received_on = models.DateField("Received On")
    classification = models.CharField("Received Class", max_length=30, choices=ItemClass.choices)
    source = models.CharField("Supplier or Owner Source", max_length=200)
    item_reference = models.CharField("Part, Serial, Batch or Specification", max_length=200)
    quantity = models.PositiveIntegerField()
    delivery_reference = models.CharField("Delivery Line Reference", max_length=100)
    release_document = models.CharField(
        "Release Document Shown on Arrival", max_length=200, blank=True
    )
    intended_use = models.CharField("Intended Aircraft or Work Package", max_length=200, blank=True)
    shelf_life_to = models.DateField("Shelf Life To", null=True, blank=True)

    class Meta:
        ordering = ["-received_on", "item", "id"]
        constraints = [
            models.UniqueConstraint(
                Lower("delivery_reference"), "organisation", name="receipt_delivery_line_once"
            ),
            models.CheckConstraint(
                condition=Q(classification__in=ItemClass.values, quantity__gt=0),
                name="receipt_has_class_and_quantity",
            ),
        ]


class ReceivingCheck(Record):
    """One recorded observation; a later observation can correct it before disposition."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    receipt = models.ForeignKey(Receipt, on_delete=models.PROTECT, related_name="checks")
    kind = models.CharField("Check", max_length=40, choices=CheckKind.choices)
    outcome = models.CharField("Result", max_length=20, choices=CheckOutcome.choices)
    evidence = models.TextField("What Was Checked and the Evidence", max_length=1000)
    checked_on = models.DateField("Checked On")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-checked_on", "-recorded_at", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=CheckKind.values)
                & (
                    Q(outcome__in=[CheckOutcome.PASS, CheckOutcome.FAIL])
                    | Q(kind=CheckKind.SHELF, outcome=CheckOutcome.NOT_APPLICABLE)
                ),
                name="receiving_check_has_a_valid_result",
            ),
        ]


class ReceivingDisposition(Record):
    """The final incoming decision and movement evidence, retained in one record."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    receipt = models.OneToOneField(Receipt, on_delete=models.PROTECT, related_name="disposition")
    approval = models.ForeignKey(Approval, on_delete=models.PROTECT, related_name="+")
    approval_reference = models.CharField("Approval Reference", max_length=40)
    inspector = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    inspector_name = models.CharField("Inspector Name at Recording", max_length=200)
    inspector_authority = models.CharField("Inspector Authorisation Evidence", max_length=200)
    inspected_on = models.DateField("Inspection Decision On")
    disposition_on = models.DateField("Moved or Returned On")
    outcome = models.CharField("Disposition", max_length=25, choices=Destination.choices)
    destination = models.CharField("Store, Quarantine Location or Return Recipient", max_length=200)
    evidence = models.TextField("Decision Reason and Movement Evidence", max_length=1000)
    document_kind = models.CharField(
        "Evidence Type", max_length=25, choices=DocumentKind.choices, blank=True
    )
    document_reference = models.CharField("Evidence Reference", max_length=200, blank=True)
    evidence_basis = models.CharField(
        "Standard, Specification or Regulatory Basis", max_length=200, blank=True
    )
    manufacturing_source = models.CharField("Manufacturing Source", max_length=200, blank=True)
    material_supplier_source = models.CharField(
        "Supplier Source on Material Evidence", max_length=200, blank=True
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(outcome__in=Destination.values, disposition_on__gte=F("inspected_on")),
                name="receiving_disposition_has_outcome_and_ordered_dates",
            ),
        ]


class StockEntry(Record):
    """The initial Stores entry for an accepted disposition."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    disposition = models.OneToOneField(
        ReceivingDisposition, on_delete=models.PROTECT, related_name="stock_entry"
    )

    class Meta:
        ordering = ["-disposition__disposition_on", "disposition__receipt__item", "id"]
