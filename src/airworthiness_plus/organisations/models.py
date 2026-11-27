"""The organisation record and the approvals it holds (REQ-001, REQ-200)."""

from datetime import date
from decimal import Decimal

from django.contrib.postgres.fields import ArrayField
from django.db import models
from django.db.models import F, Q

from airworthiness_plus.history.models import Record


class ApprovalType(models.TextChoices):
    """An approval an organisation may hold (Decisions.md, Canvas Build, decision 1)."""

    PART_CAO = "Part-CAO", "Part-CAO"
    PART_CAMO = "Part-CAMO", "Part-CAMO"
    PART_145 = "Part-145", "Part-145"


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
    """One approved organisation. Every other record belongs to exactly one (REQ-002).

    ``approval_type`` and ``approval_reference`` are the approval the
    organisation was set up with. Its certificates carry that reference
    (REQ-110). Every approval it holds, that one among them, is an
    ``Approval`` record (REQ-200).
    """

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
    # An earlier alert for airworthiness review certificates, in days before
    # expiry, where the organisation has turned one on (REQ-213).
    review_alert_days = models.PositiveSmallIntegerField(null=True, blank=True)
    # The organisation's own default limits, in days, for a deferred defect
    # (REQ-214). ML.A.403(b) says who may defer; the regulation gives no number.
    deferral_days_non_required = models.PositiveSmallIntegerField(db_default=30)
    deferral_days_with_agreement = models.PositiveSmallIntegerField(db_default=30)
    deferral_days_certifying_staff = models.PositiveSmallIntegerField(db_default=30)
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
            # CAO.A.095 gives the privileges of a Part-CAO: an organisation set up
            # as one has at least one. The privileges of the other approvals are
            # not yet recorded (REQ-200).
            models.CheckConstraint(
                condition=(Q(privileges__len__gte=1) | ~Q(approval_type=ApprovalType.PART_CAO))
                & Q(approval_type__in=ApprovalType.values)
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
            models.CheckConstraint(
                condition=Q(review_alert_days__isnull=True)
                | Q(review_alert_days__gt=F("due_soon_days")),
                name="organisation_review_alert_is_the_earlier",
            ),
            # The most each may be (REQ-212 to REQ-214). Ours, not the regulation's.
            models.CheckConstraint(
                condition=Q(due_soon_days__lte=365)
                & Q(due_soon_hours__lte=Decimal("999.9"))
                & Q(due_soon_cycles__lte=9999)
                & (Q(review_alert_days__isnull=True) | Q(review_alert_days__lte=365))
                & Q(deferral_days_non_required__lte=365)
                & Q(deferral_days_with_agreement__lte=365)
                & Q(deferral_days_certifying_staff__lte=365),
                name="organisation_settings_are_within_their_bounds",
            ),
            models.CheckConstraint(
                condition=Q(deferral_days_non_required__gte=1)
                & Q(deferral_days_with_agreement__gte=1)
                & Q(deferral_days_certifying_staff__gte=1),
                name="organisation_deferral_limits_are_at_least_a_day",
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


class Approval(Record):
    """One approval an organisation holds, with its reference (REQ-200).

    An approval is recorded once for an organisation. One that ends is kept,
    marked with the day it ended, and may be recorded as held again.
    """

    organisation = models.ForeignKey(
        Organisation, on_delete=models.PROTECT, related_name="approvals"
    )
    approval = models.CharField("Approval", max_length=20, choices=ApprovalType.choices)
    reference = models.CharField("Approval Reference", max_length=40)
    no_longer_held_on = models.DateField("No Longer Held From", null=True, blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [
            models.UniqueConstraint(fields=["organisation", "approval"], name="approval_held_once"),
            models.CheckConstraint(
                condition=Q(approval__in=ApprovalType.values) & ~Q(reference=""),
                name="approval_is_known_and_has_its_reference",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.approval}, {self.reference}"

    @property
    def held(self) -> bool:
        """Return whether the approval is held now."""
        return self.no_longer_held_on is None

    def held_on(self, day: date) -> bool:
        """Return whether the record says the approval was held on ``day``.

        The record carries the day the approval was no longer held from,
        and no day it was first held: an approval is taken as held on any
        day before it ended. So one recorded after ``day`` counts as held
        on it, which errs toward keeping a record longer (REQ-206).
        """
        return self.no_longer_held_on is None or self.no_longer_held_on > day
