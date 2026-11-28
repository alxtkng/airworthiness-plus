"""Published staffing, working hours, and recorded handovers."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.history.models import Record


class Settings(Record):
    organisation = models.OneToOneField("organisations.Organisation", on_delete=models.PROTECT)
    annual_leave_days = models.PositiveSmallIntegerField(
        "Annual Leave Allowance in Days", default=25
    )
    load_margin_percent = models.PositiveSmallIntegerField("Load Warning Percentage", default=85)
    other_hours_weekly = models.DecimalField(
        "Other Hours per Week", max_digits=6, decimal_places=1, default=50
    )
    maximum_shift_minutes = models.PositiveSmallIntegerField(
        "Longest Shift in Minutes", default=600
    )
    minimum_rest_minutes = models.PositiveSmallIntegerField("Minimum Rest in Minutes", default=660)
    maximum_week_minutes = models.PositiveSmallIntegerField("Weekly Limit in Minutes", default=2880)
    critical_first_half = models.BooleanField(
        "Critical Tasks in the First Half of a Shift", default=True
    )
    publish_days = models.PositiveSmallIntegerField("Publish This Many Days Ahead", default=14)
    overlap_minutes = models.PositiveSmallIntegerField("Handover Overlap in Minutes", default=15)
    standard_break_minutes = models.PositiveSmallIntegerField(
        "Standard Break in Minutes", default=30
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    load_margin_percent__range=(1, 100),
                    other_hours_weekly__gte=0,
                    maximum_shift_minutes__range=(1, 1440),
                    minimum_rest_minutes__range=(0, 10080),
                    maximum_week_minutes__range=(1, 10080),
                    publish_days__range=(0, 365),
                    overlap_minutes__range=(0, 1440),
                    standard_break_minutes__range=(0, 1439),
                ),
                name="staffing_settings_use_valid_planning_limits",
            ),
        ]


class PublishedRoster(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    week = models.DateField("Week Beginning")
    published_on = models.DateField("Published")
    published_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    note = models.CharField("Changes and Agreement", max_length=400)
    supersedes = models.OneToOneField(
        "self",
        on_delete=models.PROTECT,
        null=True,
        related_name="replacement",
    )

    class Meta:
        ordering = ["week", "published_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "week"],
                condition=Q(supersedes__isnull=True),
                name="staffing_roster_has_one_first_publication",
            ),
            models.CheckConstraint(condition=~Q(note=""), name="staffing_publication_has_evidence"),
        ]


class Shift(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    approval = models.ForeignKey("organisations.Approval", on_delete=models.PROTECT)
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT)
    area = models.CharField("Area", max_length=100)
    shift_name = models.CharField("Shift", max_length=100)
    starts_at = models.DateTimeField("Starts")
    ends_at = models.DateTimeField("Ends")
    break_minutes = models.PositiveSmallIntegerField("Break in Minutes")
    other_minutes = models.PositiveSmallIntegerField("Other Work in Minutes That Day", default=0)
    maintenance = models.BooleanField("Performs Maintenance", default=True)
    critical_at = models.DateTimeField("Critical Task Time", null=True)
    mitigation = models.CharField("Risk Assessment or Mitigation", max_length=400, blank=True)
    permission = models.CharField(
        "Civil Aviation Authority Permission Reference", max_length=200, blank=True
    )
    withdrawn_on = models.DateField("Withdrawn", null=True)
    withdrawal_reason = models.CharField("Reason Withdrawn", max_length=300, blank=True)

    class Meta:
        ordering = ["starts_at", "area", "shift_name", "person__full_name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__gt=F("starts_at"))
                & ~Q(area="")
                & ~Q(shift_name="")
                & (
                    Q(critical_at__isnull=True)
                    | Q(critical_at__gte=F("starts_at"), critical_at__lt=F("ends_at"))
                ),
                name="staffing_shift_is_timed_and_named",
            ),
            models.CheckConstraint(
                condition=Q(withdrawn_on__isnull=True, withdrawal_reason="")
                | (Q(withdrawn_on__isnull=False) & ~Q(withdrawal_reason="")),
                name="staffing_shift_withdrawal_has_reason",
            ),
        ]


class PublishedShift(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    publication = models.ForeignKey(
        PublishedRoster, on_delete=models.PROTECT, related_name="entries"
    )
    shift = models.ForeignKey(Shift, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "shift"], name="staffing_shift_in_publication_once"
            ),
        ]


class Handover(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    package = models.ForeignKey("planning.WorkPackage", on_delete=models.PROTECT, null=True)
    card = models.ForeignKey("planning.WorkCard", on_delete=models.PROTECT, null=True)
    outgoing = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    incoming = models.ForeignKey("people.Person", on_delete=models.PROTECT, related_name="+")
    handed_at = models.DateTimeField("Handed Over")
    stage = models.CharField("Stage Reached and Open Tasks", max_length=500)
    parts = models.CharField("Parts, Tools and Warnings", max_length=500)
    overlap = models.PositiveSmallIntegerField("Planned Overlap in Minutes", null=True)
    overlap_target = models.PositiveSmallIntegerField(
        "Planned Overlap Target in Minutes", null=True
    )
    acknowledged_at = models.DateTimeField("Acknowledged", null=True)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, related_name="+"
    )

    class Meta:
        ordering = ["-handed_at", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(outgoing=F("incoming"))
                & ~Q(stage="")
                & ~Q(parts="")
                & (
                    Q(acknowledged_at__isnull=True, actor__isnull=True)
                    | Q(acknowledged_at__gte=F("handed_at"), actor__isnull=False)
                ),
                name="staffing_handover_identifies_people_and_state",
            ),
        ]


class BankHoliday(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    on = models.DateField("Date")
    name = models.CharField("Bank Holiday", max_length=120)

    class Meta:
        ordering = ["on"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "on"], name="staffing_one_holiday_per_day"
            ),
            models.CheckConstraint(condition=~Q(name=""), name="staffing_holiday_is_named"),
        ]


class ShiftPattern(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    name = models.CharField("Shift Pattern", max_length=100)
    area = models.CharField("Area", max_length=100)
    days = models.CharField("Days", max_length=120)
    starts_at = models.TimeField("Starts")
    ends_at = models.TimeField("Ends")
    break_minutes = models.PositiveSmallIntegerField("Break in Minutes")

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "name"], name="staffing_one_pattern_per_name"
            ),
            models.CheckConstraint(
                condition=~Q(name="") & ~Q(area="") & ~Q(days=""),
                name="staffing_shift_pattern_is_named",
            ),
        ]


class StaffingMinimum(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    approval = models.ForeignKey("organisations.Approval", on_delete=models.PROTECT)
    function = models.CharField("Function", max_length=40)
    minimum = models.PositiveSmallIntegerField("Minimum")
    normal = models.PositiveSmallIntegerField("Normal")
    applies_on = models.CharField("Applies On", max_length=200)

    class Meta:
        ordering = ["approval__approval", "function"]
        constraints = [
            models.UniqueConstraint(
                fields=["approval", "function"], name="staffing_one_minimum_per_function"
            ),
            models.CheckConstraint(
                condition=(Q(normal__gte=F("minimum")) & ~Q(applies_on="")),
                name="staffing_minimum_does_not_exceed_normal",
            ),
        ]
