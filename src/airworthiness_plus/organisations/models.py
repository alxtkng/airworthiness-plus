"""The organisation record (REQ-001)."""

from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import Q

from airworthiness_plus.history.models import Record


class ApprovalType(models.TextChoices):
    """The approval an organisation holds. The private beta slice is Part-CAO only."""

    PART_CAO = "Part-CAO", "Part-CAO"


class Privilege(models.TextChoices):
    """The privileges of a Part-CAO, CAO.A.095(a) to (d)."""

    MAINTENANCE = "Maintenance", "Maintenance"
    CONTINUING_AIRWORTHINESS_MANAGEMENT = (
        "Continuing Airworthiness Management",
        "Continuing Airworthiness Management",
    )
    AIRWORTHINESS_REVIEW = "Airworthiness Review", "Airworthiness Review"
    PERMIT_TO_FLY = "Permit to Fly", "Permit to Fly"


class Organisation(Record):
    """One approved organisation. Every other record belongs to exactly one (REQ-002)."""

    name = models.CharField(max_length=200)
    approval_type = models.CharField(
        max_length=20, choices=ApprovalType.choices, default=ApprovalType.PART_CAO
    )
    approval_reference = models.CharField(max_length=40)
    # CAA Form 15c carries the organisation's name, address and approval reference.
    address = models.CharField(max_length=300, blank=True)
    privileges = ArrayField(models.CharField(max_length=40, choices=Privilege.choices))
    scope_of_work = models.TextField()
    # How close a limit must be to count as Due Soon (REQ-055). Ours, not the
    # regulation's, and each organisation may set its own.
    due_soon_days = models.PositiveSmallIntegerField(default=30)
    due_soon_hours = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("10.0"))
    due_soon_cycles = models.PositiveSmallIntegerField(default=10)
    # The Civil Aviation Authority's written approval to keep records in this
    # system, and the day the parallel run began (REQ-173, REQ-174).
    records_approval_reference = models.CharField(max_length=100, blank=True)
    records_approval_dated = models.DateField(null=True, blank=True)
    parallel_run_started_on = models.DateField(null=True, blank=True)
    # The highest certificate serial known to have been issued. It matters only
    # after a restore from backup, when certificates issued since the backup are
    # no longer in the records: the next serial still follows it (REQ-154). Set
    # by the owner of the records, never by the application, and never lowered.
    certificate_serial_floor = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(privileges__len__gte=1)
                & Q(
                    privileges__contained_by=[
                        Privilege.MAINTENANCE,
                        Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT,
                        Privilege.AIRWORTHINESS_REVIEW,
                        Privilege.PERMIT_TO_FLY,
                    ]
                ),
                name="organisation_has_known_privileges",
            ),
            models.CheckConstraint(
                condition=Q(records_approval_reference="", records_approval_dated__isnull=True)
                | (~Q(records_approval_reference="") & Q(records_approval_dated__isnull=False)),
                name="organisation_records_approval_has_its_date",
            ),
            models.CheckConstraint(
                condition=Q(due_soon_hours__gte=0),
                name="organisation_due_soon_hours_not_below_zero",
            ),
            # CAO.A.095(c): airworthiness review is open to an organisation
            # whose approval includes maintenance or continuing airworthiness
            # management.
            models.CheckConstraint(
                condition=~Q(privileges__contains=[Privilege.AIRWORTHINESS_REVIEW])
                | Q(privileges__contains=[Privilege.MAINTENANCE])
                | Q(privileges__contains=[Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT]),
                name="organisation_review_needs_maintenance_or_management",
            ),
            # CAO.A.095(d): the permit to fly privilege is open to an
            # organisation whose approval includes airworthiness review.
            models.CheckConstraint(
                condition=~Q(privileges__contains=[Privilege.PERMIT_TO_FLY])
                | Q(privileges__contains=[Privilege.AIRWORTHINESS_REVIEW]),
                name="organisation_permit_to_fly_needs_review",
            ),
        ]

    def __str__(self) -> str:
        return self.name
