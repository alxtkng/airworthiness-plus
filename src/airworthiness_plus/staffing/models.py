"""Staffing requirements, reviews, deviations and absences (REQ-324 to REQ-327)."""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.history.models import Record


class Function(models.TextChoices):
    PLANNING = "Planning", "Planning"
    CERTIFYING = "Certifying Staff", "Certifying Staff"
    MAINTENANCE = "Maintenance Support", "Maintenance Support"
    INSPECTION = "Independent Inspection", "Independent Inspection"
    MANAGEMENT = "Continuing Airworthiness Management", "Continuing Airworthiness Management"
    REVIEW = "Airworthiness Reviews", "Airworthiness Reviews"
    SAFETY = "Safety Management", "Safety Management"
    MONITORING = "Compliance Monitoring", "Compliance Monitoring"


class Demand(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    approval = models.ForeignKey("organisations.Approval", on_delete=models.PROTECT)
    month = models.DateField("Month")
    function = models.CharField("Function", max_length=40, choices=Function.choices)
    needed = models.DecimalField("Hours Needed", max_digits=7, decimal_places=1)
    employed = models.DecimalField("Employed Hours Available", max_digits=7, decimal_places=1)
    contracted = models.DecimalField("Contracted Hours Available", max_digits=7, decimal_places=1)
    basis = models.CharField("Work and Availability Basis", max_length=400)

    class Meta:
        ordering = ["month", "approval__approval", "function"]
        constraints = [
            models.UniqueConstraint(
                fields=["approval", "month", "function"],
                name="staffing_one_line_per_function_month",
            ),
            models.CheckConstraint(
                condition=Q(
                    month__day=1,
                    function__in=Function.values,
                    needed__gte=0,
                    employed__gte=0,
                    contracted__gte=0,
                )
                & ~Q(basis=""),
                name="staffing_demand_has_valid_month_hours_and_basis",
            ),
        ]


class Review(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    approval = models.ForeignKey("organisations.Approval", on_delete=models.PROTECT)
    reviewed_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    reviewed_on = models.DateField("Reviewed")
    outcome = models.CharField("Review Outcome", max_length=400)

    class Meta:
        ordering = ["-reviewed_on", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(outcome=""), name="staffing_review_has_outcome"),
        ]


class Report(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    demand = models.ForeignKey(Demand, on_delete=models.PROTECT, related_name="reports")
    reported_on = models.DateField("Reported")
    reported_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT)
    reported_to = models.CharField("Reported To", max_length=200)
    action = models.CharField("Action Taken", max_length=400)
    needed = models.DecimalField(max_digits=7, decimal_places=1)
    employed = models.DecimalField(max_digits=7, decimal_places=1)
    contracted = models.DecimalField(max_digits=7, decimal_places=1)

    class Meta:
        ordering = ["-reported_on", "-id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(needed__gt=0, employed__gte=0, contracted__gte=0)
                & ~Q(action="")
                & ~Q(reported_to=""),
                name="staffing_report_has_hours_recipients_and_action",
            ),
        ]


class AbsenceType(models.TextChoices):
    HOLIDAY = "Holiday", "Holiday"
    SICKNESS = "Sickness", "Sickness"
    TRAINING = "Training", "Training"
    JURY_SERVICE = "Jury Service", "Jury Service"


class Absence(Record):
    organisation = models.ForeignKey("organisations.Organisation", on_delete=models.PROTECT)
    person = models.ForeignKey("people.Person", on_delete=models.PROTECT)
    kind = models.CharField("Absence", choices=AbsenceType.choices, max_length=20)
    starts_on = models.DateField("From")
    ends_on = models.DateField("To")

    class Meta:
        ordering = ["starts_on", "person__full_name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_on__gte=F("starts_on"), kind__in=AbsenceType.values),
                name="staffing_absence_has_valid_dates_and_kind",
            ),
        ]
