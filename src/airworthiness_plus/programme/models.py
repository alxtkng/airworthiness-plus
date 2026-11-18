"""The maintenance programme, its tasks and the work done (REQ-040 to REQ-059)."""

from django.db import models
from django.db.models import Q

from airworthiness_plus.aircraft.models import Aircraft, Counter
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation
from airworthiness_rules.intervals import Interval, Reading, TaskKind


class Basis(models.TextChoices):
    """What the programme is based on, ML.A.302(c)(2)."""

    INSTRUCTIONS = "Design Approval Holder's Instructions", "Design Approval Holder's Instructions"
    MINIMUM_INSPECTION_PROGRAMME = "Minimum Inspection Programme", "Minimum Inspection Programme"


class InspectionCategory(models.TextChoices):
    """The two sets of Minimum Inspection Programme intervals, ML.A.302(d)(1)(a) and (b).

    There is none for airships and rotorcraft: their programme is based on
    the design approval holder's instructions (ML.A.302(d)).
    """

    AEROPLANE = (
        "Aeroplane, Touring Motor Glider or Balloon",
        "Aeroplane, Touring Motor Glider or Balloon",
    )
    SAILPLANE = (
        "Sailplane or Powered Sailplane Other Than a Touring Motor Glider",
        "Sailplane or Powered Sailplane Other Than a Touring Motor Glider",
    )


class Programme(Record):
    """The one maintenance programme of an aircraft (REQ-040, AMC1 ML.A.302)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.OneToOneField(Aircraft, on_delete=models.PROTECT, related_name="programme")
    basis = models.CharField("Basis", max_length=60, choices=Basis.choices)
    inspection_category = models.CharField(
        "Minimum Inspection Programme For",
        max_length=80,
        choices=InspectionCategory.choices,
        blank=True,
    )
    reference = models.CharField("Programme Reference", max_length=200)
    # Planning figures, used only to say which limit is expected first (REQ-044).
    hours_per_day = models.DecimalField(
        "Planning Hours a Day", max_digits=4, decimal_places=1, null=True, blank=True
    )
    cycles_per_day = models.DecimalField(
        "Planning Cycles a Day", max_digits=5, decimal_places=1, null=True, blank=True
    )
    last_reviewed = models.DateField("Last Reviewed", null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(basis__in=Basis.values), name="programme_has_a_known_basis"
            ),
            # A programme on the Minimum Inspection Programme says which
            # intervals apply; any other programme does not.
            models.CheckConstraint(
                condition=Q(
                    basis=Basis.MINIMUM_INSPECTION_PROGRAMME,
                    inspection_category__in=InspectionCategory.values,
                )
                | Q(basis=Basis.INSTRUCTIONS, inspection_category=""),
                name="programme_minimum_inspection_names_its_intervals",
            ),
            models.CheckConstraint(
                condition=(Q(hours_per_day__isnull=True) | Q(hours_per_day__gt=0))
                & (Q(cycles_per_day__isnull=True) | Q(cycles_per_day__gt=0)),
                name="programme_planning_figures_above_zero",
            ),
        ]

    def __str__(self) -> str:
        return self.reference


TASK_KINDS = [(kind.value, kind.value) for kind in TaskKind]


class Task(Record):
    """One task of a programme: what repeats, how often, and against which counter.

    A task that is no longer in the programme is retired, never deleted.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    programme = models.ForeignKey(Programme, on_delete=models.PROTECT, related_name="tasks")
    title = models.CharField("Task", max_length=200)
    kind = models.CharField("Kind", max_length=40, choices=TASK_KINDS)
    counter = models.ForeignKey(Counter, on_delete=models.PROTECT, related_name="+")
    source = models.CharField("Source", max_length=200)

    interval_hours = models.DecimalField(
        "Hours", max_digits=7, decimal_places=1, null=True, blank=True
    )
    interval_cycles = models.PositiveIntegerField("Cycles", null=True, blank=True)
    interval_months = models.PositiveIntegerField("Months", null=True, blank=True)
    interval_days = models.PositiveIntegerField("Days", null=True, blank=True)

    # A first threshold that differs from the repeat (REQ-058).
    first_hours = models.DecimalField(
        "First at Hours", max_digits=7, decimal_places=1, null=True, blank=True
    )
    first_cycles = models.PositiveIntegerField("First at Cycles", null=True, blank=True)
    first_months = models.PositiveIntegerField("First at Months", null=True, blank=True)
    first_days = models.PositiveIntegerField("First at Days", null=True, blank=True)

    # Where the count starts for a task never yet done here: since new, or
    # since overhaul (REQ-058).
    starts_dated = models.DateField("Counted From", null=True, blank=True)
    starts_hours = models.DecimalField(
        "Hours Then", max_digits=8, decimal_places=1, null=True, blank=True
    )
    starts_cycles = models.PositiveIntegerField("Cycles Then", null=True, blank=True)

    # An action done once and not repeated, such as a directive complied
    # with by a single inspection: due at its limit, and finished once done.
    once = models.BooleanField(default=False)
    retired = models.BooleanField(default=False)

    class Meta:
        ordering = ["title"]
        constraints = [
            models.CheckConstraint(
                condition=Q(kind__in=[value for value, _ in TASK_KINDS]),
                name="task_has_a_known_kind",
            ),
            models.CheckConstraint(
                condition=Q(interval_hours__gt=0)
                | Q(interval_cycles__gt=0)
                | Q(interval_months__gt=0)
                | Q(interval_days__gt=0),
                name="task_has_an_interval",
            ),
            models.CheckConstraint(
                condition=Q(interval_months__isnull=True) | Q(interval_days__isnull=True),
                name="task_calendar_interval_in_months_or_days",
            ),
            models.CheckConstraint(
                condition=Q(first_months__isnull=True) | Q(first_days__isnull=True),
                name="task_first_calendar_threshold_in_months_or_days",
            ),
            # The start of the count is a date with hours and cycles, or nothing.
            models.CheckConstraint(
                condition=Q(
                    starts_dated__isnull=True, starts_hours__isnull=True, starts_cycles__isnull=True
                )
                | Q(
                    starts_dated__isnull=False,
                    starts_hours__isnull=False,
                    starts_cycles__isnull=False,
                ),
                name="task_start_is_complete_or_absent",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def task_kind(self) -> TaskKind:
        """Return the kind in the form the calculation rules take."""
        return TaskKind(self.kind)

    @property
    def interval(self) -> Interval:
        """Return the repeat interval."""
        return Interval(
            hours=self.interval_hours,
            cycles=self.interval_cycles,
            months=self.interval_months,
            days=self.interval_days,
        )

    @property
    def first_interval(self) -> Interval:
        """Return the first threshold, or the repeat interval if there is none."""
        values = (self.first_hours, self.first_cycles, self.first_months, self.first_days)
        if all(value is None for value in values):
            return self.interval
        return Interval(
            hours=self.first_hours,
            cycles=self.first_cycles,
            months=self.first_months,
            days=self.first_days,
        )

    @property
    def starts(self) -> Reading | None:
        """Return where the count starts for a task never yet done here."""
        if self.starts_dated is None or self.starts_hours is None or self.starts_cycles is None:
            return None
        return Reading(self.starts_dated, self.starts_hours, self.starts_cycles)


class WorkDone(Record):
    """Maintenance carried out: a programme task done, or other work (REQ-050 to REQ-052).

    Each time a task is done is a new record, so earlier ones are kept. The
    hours and cycles are the totals of the task's counter, or of the
    airframe for other work, when the work was completed.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="work_done")
    task = models.ForeignKey(
        Task, on_delete=models.PROTECT, null=True, blank=True, related_name="work_done"
    )
    description = models.CharField("Work", max_length=200)
    dated = models.DateField("Completed")
    hours = models.DecimalField("Hours", max_digits=8, decimal_places=1)
    cycles = models.PositiveIntegerField("Cycles")
    release_reference = models.CharField(
        "Certificate of Release to Service", max_length=100, blank=True
    )
    release_recorded_on = models.DateField("Release Recorded", null=True, blank=True)
    by_pilot_owner = models.BooleanField("Pilot-Owner Maintenance", default=False)
    pilot_owner_told_on = models.DateField("Organisation Told", null=True, blank=True)

    class Meta:
        ordering = ["dated", "hours"]
        constraints = [
            models.CheckConstraint(condition=Q(hours__gte=0), name="work_hours_not_below_zero"),
            # A release has a reference and the date it went into the records, or neither.
            models.CheckConstraint(
                condition=Q(release_reference="", release_recorded_on__isnull=True)
                | (~Q(release_reference="") & Q(release_recorded_on__isnull=False)),
                name="work_release_has_a_reference_and_a_date",
            ),
            models.CheckConstraint(
                condition=Q(by_pilot_owner=True) | Q(pilot_owner_told_on__isnull=True),
                name="work_told_date_only_for_pilot_owner_maintenance",
            ),
        ]

    def __str__(self) -> str:
        return self.description

    @property
    def reading(self) -> Reading:
        """Return when the work was done, in the form the calculation rules take."""
        return Reading(self.dated, self.hours, self.cycles)
