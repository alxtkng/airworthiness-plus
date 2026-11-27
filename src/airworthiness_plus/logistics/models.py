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
