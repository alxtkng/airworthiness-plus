"""Maintenance data: each set held, its revisions and the checks of its amendment status.

Hazard H-005: a superseded manual revision shown as current. Sources, read
in the UK text on 18 November 2026: ML.A.401, CAO.A.055, AMC1 CAO.A.055,
CAO.A.080, AMC M.A.401(c) point 5, AMC1 145.A.45(g).
"""

from typing import Any

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.organisations.models import Organisation


class Kind(models.TextChoices):
    """What a set of data is, ML.A.401(b)(1) to (5)."""

    AUTHORITY = (
        "Civil Aviation Authority Requirement",
        "Civil Aviation Authority Requirement, Procedure, Standard or Information",
    )
    DIRECTIVE = "Airworthiness Directive", "Airworthiness Directive"
    INSTRUCTIONS = (
        "Instructions for Continued Airworthiness",
        "Instructions for Continued Airworthiness, From a Type or Supplementary Type "
        "Certificate Holder",
    )
    COMPONENT = (
        "Component Manufacturer's Instructions",
        "Component Manufacturer's Instructions",
    )
    MODIFIED = (
        "Modified Maintenance Instructions",
        "Modified Maintenance Instructions, Issued Under 145.A.45(d)",
    )


class Holding(models.TextChoices):
    """Whether the organisation holds the data."""

    HELD = "Held", "Held"
    NOT_HELD = "Not Held", "Not Held"
    NO_LONGER_HELD = "No Longer Held", "No Longer Held"


class Evidence(models.TextChoices):
    """How the amendment status of customer-provided data is shown."""

    WRITTEN_CONFIRMATION = "Written Confirmation", "Written Confirmation"
    WORK_ORDER = "Work Order", "Work Order"
    AMENDMENT_LIST = "Customer's Amendment List", "Customer's Amendment List"


class DataSet(Record):
    """One set of maintenance data (REQ-080 to REQ-084, REQ-086 to REQ-088)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    title = models.CharField("Title", max_length=200)
    author = models.CharField("Author", max_length=200)
    kind = models.CharField("Kind", max_length=60, choices=Kind.choices)
    # The type ratings the data applies to, each exactly as SRG1782 writes it.
    applies_to = ArrayField(models.CharField(max_length=200), default=list, blank=True)
    # Carries mandatory instructions or airworthiness limitations, which
    # AMC1 145.A.45(g) singles out for special attention.
    mandatory = models.BooleanField(
        "Carries Mandatory Instructions or Airworthiness Limitations", default=False
    )
    amendment_service = models.CharField("Amendment Service", max_length=200, blank=True)
    check_due = models.DateField("Next Amendment Check By", null=True, blank=True)
    holding = models.CharField(
        "Holding", max_length=20, choices=Holding.choices, default=Holding.HELD
    )
    no_longer_held_on = models.DateField("No Longer Held From", null=True, blank=True)
    customer_provided = models.BooleanField("Provided by the Customer", default=False)
    provided_by = models.CharField("Provided By", max_length=200, blank=True)
    evidence = models.CharField(
        "Amendment Status Shown By", max_length=40, choices=Evidence.choices, blank=True
    )
    evidence_dated = models.DateField("Shown On", null=True, blank=True)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=Kind.values) & Q(holding__in=Holding.values),
                name="dataset_has_a_known_kind_and_holding",
            ),
            models.CheckConstraint(
                condition=Q(holding=Holding.NO_LONGER_HELD, no_longer_held_on__isnull=False)
                | (~Q(holding=Holding.NO_LONGER_HELD) & Q(no_longer_held_on__isnull=True)),
                name="dataset_no_longer_held_has_its_date",
            ),
            # Customer-provided data says who provided it and how its
            # amendment status is shown, with the date (REQ-086).
            models.CheckConstraint(
                condition=Q(
                    customer_provided=False,
                    provided_by="",
                    evidence="",
                    evidence_dated__isnull=True,
                )
                | (
                    Q(customer_provided=True, evidence__in=Evidence.values)
                    & ~Q(provided_by="")
                    & Q(evidence_dated__isnull=False)
                ),
                name="dataset_customer_data_shows_its_amendment_status",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class Revision(Record):
    """One revision of a set of data (REQ-085).

    Exactly one revision of a set is current. Adding a revision supersedes
    the one before it, which stays in the record marked as superseded, and
    a superseded revision can never be made current again: the database
    refuses.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    data_set = models.ForeignKey(DataSet, on_delete=models.PROTECT, related_name="revisions")
    revision = models.CharField("Revision", max_length=60)
    revision_date = models.DateField("Revision Date")
    current = models.BooleanField(default=True)

    class Meta:
        ordering = ["revision_date", "revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["data_set"],
                condition=Q(current=True),
                name="revision_one_current_for_each_set",
            ),
            models.UniqueConstraint(
                fields=["data_set", "revision"], name="revision_recorded_once_for_each_set"
            ),
        ]

    def __str__(self) -> str:
        return self.revision


class AmendmentCheck(Record):
    """A check that every amendment to a set of data has been received (REQ-082).

    AMC M.A.401(c) point 5: subscribe to the amendment scheme, check that
    all amendments are being received, and monitor the amendment status. A
    check is added and never changed.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    data_set = models.ForeignKey(DataSet, on_delete=models.PROTECT, related_name="checks")
    checked_on = models.DateField("Checked")
    next_due = models.DateField("Next Amendment Check By", null=True)
    checked_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    result = models.CharField("Result", max_length=200)

    class Meta:
        ordering = ["checked_on"]

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the check. A check that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("A check is never changed")
        super().save(*args, **kwargs)
