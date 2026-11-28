"""Supplier, Goods In and Stores records (REQ-340 to REQ-358)."""

from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
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


# Stores PR 1 (REQ-358): appointments, locations, the once-only posting of an
# accepted or quarantined disposition, and the movement ledger. Every record is
# appended and never changed. Balances are derived from movements.

QUANTITY_DIGITS = 13
QUANTITY_PLACES = 3
# The largest positive integer an existing receipt could hold.
QUANTITY_LIMIT = Decimal(2_147_483_647)


class StockUnit(models.TextChoices):
    EACH = "Each", "Each"
    LITRE = "Litre", "Litre"


class StoresAction(models.TextChoices):
    LOCATIONS = "Locations", "Maintain Stores Locations"
    POST = "Post", "Post Accepted Items to Stock"
    MOVE = "Move", "Move Stock"
    COUNT = "Count", "Count Stock"
    ADJUST = "Adjust", "Adjust Stock After a Count"


class LocationKind(models.TextChoices):
    SERVICEABLE = "Serviceable Store", "Serviceable Store"
    QUARANTINE = "Quarantine", "Quarantine"


class ShelfLifeBasis(models.TextChoices):
    THROUGH = "Usable Through the Date", "Usable Through the Date"
    BEFORE = "Expires at the Start of the Date", "Expires at the Start of the Date"
    NOT_APPLICABLE = "Not Applicable", "Not Applicable"


class PostingKind(models.TextChoices):
    STOCK = "Stock", "Serviceable Stock"
    HOLD = "Hold", "Quarantine Hold"


class MovementKind(models.TextChoices):
    INTAKE = "Intake", "Intake"
    HOLD = "Hold", "Quarantine Hold"
    TRANSFER = "Transfer", "Transfer"
    ADJUSTMENT = "Adjustment", "Count Adjustment"


class StoresRecord(Record):
    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    submission = models.UUIDField()
    entered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


def _once(name: str) -> models.UniqueConstraint:
    return models.UniqueConstraint(fields=["organisation", "submission"], name=name)


class StoresAppointment(StoresRecord):
    """Recorded evidence that a person holds a Stores action under an exposition."""

    person = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    approval = models.ForeignKey(Approval, on_delete=models.PROTECT, related_name="+")
    approval_reference = models.CharField("Approval Reference", max_length=40)
    action = models.CharField("Action", max_length=12, choices=StoresAction.choices)
    starts_on = models.DateField("From")
    ends_on = models.DateField("To")
    exposition_reference = models.CharField("Exposition Procedure and Revision", max_length=200)
    authority = models.TextField("Appointment Evidence", max_length=1000)

    class Meta:
        ordering = ["person__full_name", "action", "-starts_on", "-entered_at"]
        constraints = [
            _once("stores_appointment_once"),
            models.CheckConstraint(
                condition=Q(ends_on__gte=F("starts_on"), action__in=StoresAction.values)
                & ~Q(exposition_reference="")
                & ~Q(authority="")
                & ~Q(approval_reference=""),
                name="stores_appointment_has_scope_and_evidence",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.person.full_name}, {self.get_action_display()}"


class StoresAppointmentWithdrawal(StoresRecord):
    appointment = models.OneToOneField(
        StoresAppointment, on_delete=models.PROTECT, related_name="withdrawal"
    )
    withdrawn_on = models.DateField("Withdrawn On")
    evidence = models.TextField("Withdrawal Evidence", max_length=1000)

    class Meta:
        constraints = [
            _once("stores_appointment_withdrawal_once"),
            models.CheckConstraint(
                condition=~Q(evidence=""), name="stores_withdrawal_has_evidence"
            ),
        ]


class StoresLocation(StoresRecord):
    """One place that holds stock, with the rules that apply to it."""

    code = models.CharField("Location Code", max_length=40)
    name = models.CharField("Location", max_length=200)
    kind = models.CharField("Use", max_length=20, choices=LocationKind.choices)
    classes = ArrayField(
        models.CharField(max_length=30, choices=ItemClass.choices), verbose_name="Classes Held"
    )
    storage_conditions = models.CharField("Storage Conditions", max_length=300)
    secure = models.BooleanField("Secure and Segregated", default=False)
    recorded_on = models.DateField()
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["kind", "code", "id"]
        constraints = [
            _once("stores_location_once"),
            models.UniqueConstraint(
                Lower("code"), "organisation", name="stores_location_code_once"
            ),
            models.CheckConstraint(
                condition=Q(kind__in=LocationKind.values)
                & ~Q(code="")
                & ~Q(name="")
                & ~Q(storage_conditions="")
                & ~Q(classes=[])
                & (~Q(kind=LocationKind.QUARANTINE) | Q(secure=True)),
                name="stores_location_has_rules",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code}, {self.name}"


class StoresLocationWithdrawal(StoresRecord):
    location = models.OneToOneField(
        StoresLocation, on_delete=models.PROTECT, related_name="withdrawal"
    )
    withdrawn_on = models.DateField("Withdrawn On")
    evidence = models.TextField("Reason and Evidence", max_length=1000)
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        constraints = [
            _once("stores_location_withdrawal_once"),
            models.CheckConstraint(
                condition=~Q(evidence=""), name="stores_location_withdrawal_has_evidence"
            ),
        ]


class PostingEvidence(StoresRecord):
    """A dated assessment that resolves what Stores needs to post a disposition.

    For a legacy acceptance it is the authorised mapping of the original
    records. Values left blank remain blocking reasons. A later assessment
    supersedes an earlier one and both are kept.
    """

    disposition = models.ForeignKey(
        ReceivingDisposition, on_delete=models.PROTECT, related_name="posting_evidence"
    )
    unit = models.CharField("Unit", max_length=10, choices=StockUnit.choices, blank=True)
    quantity = models.DecimalField(
        "Quantity",
        max_digits=QUANTITY_DIGITS,
        decimal_places=QUANTITY_PLACES,
        null=True,
        blank=True,
    )
    manufacturer = models.CharField("Manufacturer", max_length=120, blank=True)
    part_number = models.CharField("Part Number", max_length=100, blank=True)
    serial = models.CharField("Serial Number", max_length=100, blank=True)
    batch = models.CharField("Batch or Lot", max_length=100, blank=True)
    specification = models.CharField("Standard or Specification", max_length=160, blank=True)
    shelf_life_basis = models.CharField(
        "Shelf-Life Basis", max_length=40, choices=ShelfLifeBasis.choices, blank=True
    )
    shelf_life_to = models.DateField("Shelf-Life Date", null=True, blank=True)
    location = models.ForeignKey(
        StoresLocation, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    tag = models.CharField("Quarantine Tag", max_length=100, blank=True)
    assessed_on = models.DateField("Assessed On")
    evidence = models.TextField("Original Records and Evidence Relied On", max_length=2000)
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-assessed_on", "-entered_at", "-id"]
        constraints = [
            _once("stores_posting_evidence_once"),
            models.CheckConstraint(
                condition=~Q(evidence="")
                & (Q(quantity__isnull=True) | Q(quantity__gt=0, quantity__lte=QUANTITY_LIMIT))
                & (Q(unit="") | Q(unit__in=StockUnit.values))
                & (Q(shelf_life_basis="") | Q(shelf_life_basis__in=ShelfLifeBasis.values)),
                name="stores_posting_evidence_is_valid",
            ),
        ]


class StockPosting(StoresRecord):
    """The once-only posting of one disposition, keyed by its immutable identifier."""

    disposition = models.OneToOneField(
        ReceivingDisposition, on_delete=models.PROTECT, related_name="posting"
    )
    evidence = models.ForeignKey(PostingEvidence, on_delete=models.PROTECT, related_name="+")
    kind = models.CharField("Posting", max_length=10, choices=PostingKind.choices)
    location_rules = models.CharField("Location Rules at Posting", max_length=600)
    posted_on = models.DateField("Posted On")
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-posted_on", "-entered_at", "id"]
        constraints = [
            _once("stores_posting_once"),
            models.CheckConstraint(
                condition=Q(kind__in=PostingKind.values) & ~Q(location_rules=""),
                name="stores_posting_is_valid",
            ),
        ]


class StockCount(StoresRecord):
    """A physical count against the ledger. It changes nothing by itself."""

    posting = models.ForeignKey(StockPosting, on_delete=models.PROTECT, related_name="counts")
    location = models.ForeignKey(StoresLocation, on_delete=models.PROTECT, related_name="+")
    counted = models.DecimalField(
        "Counted Quantity", max_digits=QUANTITY_DIGITS, decimal_places=QUANTITY_PLACES
    )
    # Written by the database from the ledger at the moment of the count.
    on_hand = models.DecimalField(
        "Ledger Quantity", max_digits=QUANTITY_DIGITS, decimal_places=QUANTITY_PLACES
    )
    counted_on = models.DateField("Counted On")
    evidence = models.TextField("Count Evidence", max_length=1000)
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["-counted_on", "-entered_at", "-id"]
        constraints = [
            _once("stores_count_once"),
            models.CheckConstraint(
                condition=Q(counted__gte=0, on_hand__gte=0) & ~Q(evidence=""),
                name="stores_count_is_valid",
            ),
        ]

    @property
    def variance(self) -> Decimal:
        return self.counted - self.on_hand


class StockMovement(StoresRecord):
    """One entry in the ledger. Each moves a positive quantity in the posting's unit."""

    posting = models.ForeignKey(StockPosting, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField("Movement", max_length=12, choices=MovementKind.choices)
    source = models.ForeignKey(
        StoresLocation, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    destination = models.ForeignKey(
        StoresLocation, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    quantity = models.DecimalField(
        "Quantity", max_digits=QUANTITY_DIGITS, decimal_places=QUANTITY_PLACES
    )
    moved_on = models.DateField("Moved On")
    evidence = models.TextField("Movement Evidence", max_length=1000)
    count = models.OneToOneField(
        StockCount, on_delete=models.PROTECT, null=True, blank=True, related_name="adjustment"
    )
    recorded_on = models.DateField()
    appointment = models.ForeignKey(StoresAppointment, on_delete=models.PROTECT, related_name="+")

    class Meta:
        ordering = ["moved_on", "entered_at", "id"]
        constraints = [
            _once("stores_movement_once"),
            models.CheckConstraint(
                condition=Q(kind__in=MovementKind.values, quantity__gt=0)
                & ~Q(evidence="")
                & (
                    Q(
                        kind__in=[MovementKind.INTAKE, MovementKind.HOLD],
                        source__isnull=True,
                        destination__isnull=False,
                        count__isnull=True,
                    )
                    | Q(
                        kind=MovementKind.TRANSFER,
                        source__isnull=False,
                        destination__isnull=False,
                        count__isnull=True,
                    )
                    | Q(kind=MovementKind.ADJUSTMENT, count__isnull=False)
                    & (
                        Q(source__isnull=True, destination__isnull=False)
                        | Q(source__isnull=False, destination__isnull=True)
                    )
                )
                & ~Q(source=F("destination")),
                name="stores_movement_has_valid_ends",
            ),
        ]
