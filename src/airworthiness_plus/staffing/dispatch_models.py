"""Timed dispatch records attached to roster shifts and maintenance work."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.history.models import Record


class DispatchAssignment(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    card = models.ForeignKey("planning.WorkCard", on_delete=models.PROTECT, related_name="+")
    shift = models.ForeignKey("staffing.Shift", on_delete=models.PROTECT, related_name="+")
    starts_at = models.DateTimeField("Starts")
    ends_at = models.DateTimeField("Ends")
    reason = models.CharField("Planning or Change Reason", max_length=300)
    supersedes = models.OneToOneField(
        "self", null=True, on_delete=models.PROTECT, related_name="replacement"
    )

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at")) & ~Q(reason=""),
                name="staffing_dispatch_assignment_has_time_and_reason",
            ),
            models.UniqueConstraint(
                fields=["card"],
                condition=Q(supersedes__isnull=True),
                name="staffing_dispatch_has_one_initial_assignment_per_card",
            ),
        ]


class DispatchWindow(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    shift = models.ForeignKey(
        "staffing.Shift", null=True, on_delete=models.PROTECT, related_name="+"
    )
    package = models.ForeignKey(
        "planning.WorkPackage", null=True, on_delete=models.PROTECT, related_name="+"
    )
    starts_at = models.DateTimeField("Starts")
    ends_at = models.DateTimeField("Ends")
    note = models.CharField("Window Note", max_length=300)

    class Meta:
        ordering = ["starts_at", "pk"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at"))
                & ~Q(note="")
                & (
                    Q(shift__isnull=False, package__isnull=True)
                    | Q(shift__isnull=True, package__isnull=False)
                ),
                name="staffing_dispatch_window_has_time_and_one_scope",
            ),
        ]
