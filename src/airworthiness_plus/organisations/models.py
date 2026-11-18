"""The organisation record (REQ-001)."""

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
    privileges = ArrayField(models.CharField(max_length=40, choices=Privilege.choices))
    scope_of_work = models.TextField()

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
