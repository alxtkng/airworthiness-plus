"""Forms for the maintenance programme. Labels follow design-system/Writing.md."""

import uuid

from django import forms

from airworthiness_plus.aircraft.models import Counter
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.models import Person
from airworthiness_plus.programme.models import TASK_KINDS, Basis, InspectionCategory, Task
from airworthiness_rules.intervals import TaskKind

# An airworthiness directive is recorded under Airworthiness Directives.
PROGRAMME_TASK_KINDS = [
    choice for choice in TASK_KINDS if choice[0] != TaskKind.AIRWORTHINESS_DIRECTIVE.value
]


class ProgrammeForm(Form):
    """Record or change the programme of an aircraft."""

    basis = forms.ChoiceField(label="Basis", choices=Basis.choices)
    inspection_category = forms.ChoiceField(
        label="Minimum Inspection Programme For",
        choices=[("", "Not on the Minimum Inspection Programme"), *InspectionCategory.choices],
        required=False,
    )
    reference = forms.CharField(label="Programme Reference", max_length=200)
    hours_per_day = forms.DecimalField(
        label="Planning Hours a Day", max_digits=4, decimal_places=1, min_value=0, required=False
    )
    cycles_per_day = forms.DecimalField(
        label="Planning Cycles a Day", max_digits=5, decimal_places=1, min_value=0, required=False
    )


class TaskForm(Form):
    """Add a task to the programme."""

    title = forms.CharField(label="Task", max_length=200)
    kind = forms.ChoiceField(label="Kind", choices=PROGRAMME_TASK_KINDS)
    counter = forms.ModelChoiceField(label="Runs Against", queryset=Counter.objects.none())
    source = forms.CharField(label="Source", max_length=200)
    interval_hours = forms.DecimalField(
        label="Every Hours", max_digits=7, decimal_places=1, min_value=0, required=False
    )
    interval_cycles = forms.IntegerField(label="Every Cycles", min_value=1, required=False)
    interval_months = forms.IntegerField(label="Every Months", min_value=1, required=False)
    interval_days = forms.IntegerField(label="Every Days", min_value=1, required=False)
    first_hours = forms.DecimalField(
        label="First at Hours", max_digits=7, decimal_places=1, min_value=0, required=False
    )
    first_cycles = forms.IntegerField(label="First at Cycles", min_value=1, required=False)
    first_months = forms.IntegerField(label="First at Months", min_value=1, required=False)
    first_days = forms.IntegerField(label="First at Days", min_value=1, required=False)
    starts_dated = forms.DateField(label="Counted From, If Never Yet Done", required=False)
    starts_hours = forms.DecimalField(
        label="Hours Then", max_digits=8, decimal_places=1, min_value=0, required=False
    )
    starts_cycles = forms.IntegerField(label="Cycles Then", min_value=0, required=False)

    def __init__(self, *args: object, aircraft_id: uuid.UUID, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["counter"].queryset = Counter.objects.filter(  # type: ignore[attr-defined]
            aircraft_id=aircraft_id
        )


class WorkForm(Form):
    """Record work done on an aircraft."""

    task = forms.ModelChoiceField(
        label="Programme Task, If It Was One", queryset=Task.objects.none(), required=False
    )
    description = forms.CharField(label="Work", max_length=200)
    dated = forms.DateField(label="Completed")
    hours = forms.DecimalField(label="Hours", max_digits=8, decimal_places=1, min_value=0)
    cycles = forms.IntegerField(label="Cycles", min_value=0)
    performed_by = forms.ModelChoiceField(
        label="Performed By",
        queryset=Person.objects.all(),
        required=False,
        empty_label="Not Recorded",
    )
    by_pilot_owner = forms.BooleanField(label="Pilot-Owner Maintenance", required=False)
    pilot_owner_told_on = forms.DateField(label="Organisation Told", required=False)
    instruction_reference = forms.CharField(
        label="Issued Instruction Reference", max_length=200, required=False
    )
    instruction_revision = forms.CharField(
        label="Issued Instruction Revision", max_length=80, required=False
    )
    completion_measurements = forms.CharField(
        label="Completion Measurements and Units", max_length=500, required=False
    )

    def __init__(self, *args: object, aircraft_id: uuid.UUID, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["task"].queryset = Task.objects.filter(  # type: ignore[attr-defined]
            programme__aircraft_id=aircraft_id, retired=False
        )


class ReviewForm(Form):
    """Record the annual review of the programme."""

    reviewed_on = forms.DateField(label="Reviewed")


class DepartureForm(Form):
    """Record a departure from the design approval holder's recommendations."""

    task = forms.CharField(label="Task", max_length=200)
    manufacturer = forms.CharField(label="Manufacturer", max_length=200)
    programme_says = forms.CharField(label="Programme", max_length=200)
    compensating_measures = forms.CharField(label="Compensating Measures", max_length=300)
    justification = forms.CharField(label="Justification", max_length=300)
    recorded_on = forms.DateField(label="Recorded")
    owner_copy_sent_on = forms.DateField(label="Owner Copy Sent", required=False)


class DepartureDateForm(Form):
    """The day a copy of a departure went to the owner, or the day it was withdrawn."""

    on = forms.DateField(label="Date")


class AnnualReviewForm(Form):
    """What was found on each point of the annual review, AMC1 ML.A.302(c)(9)."""

    results_note = forms.CharField(
        label="Maintenance Results This Year", max_length=300, required=False
    )
    results_done = forms.BooleanField(
        label="Maintenance Results This Year, Complete", required=False
    )
    airworthiness_review_note = forms.CharField(
        label="Last Airworthiness Review", max_length=300, required=False
    )
    airworthiness_review_done = forms.BooleanField(
        label="Last Airworthiness Review, Complete", required=False
    )
    revisions_note = forms.CharField(
        label="Minimum Inspection Programme and Manufacturer's Revisions",
        max_length=300,
        required=False,
    )
    revisions_done = forms.BooleanField(
        label="Minimum Inspection Programme and Manufacturer's Revisions, Complete",
        required=False,
    )
    configuration_note = forms.CharField(
        label="Configuration, Type and Operation", max_length=300, required=False
    )
    configuration_done = forms.BooleanField(
        label="Configuration, Type and Operation, Complete", required=False
    )
    pilot_owners_note = forms.CharField(label="Pilot-Owners", max_length=300, required=False)
    pilot_owners_done = forms.BooleanField(label="Pilot-Owners, Complete", required=False)
    mandatory_note = forms.CharField(
        label="Directives, Airworthiness Limitations and Data Sheet",
        max_length=300,
        required=False,
    )
    mandatory_done = forms.BooleanField(
        label="Directives, Airworthiness Limitations and Data Sheet, Complete", required=False
    )


class CompleteReviewForm(Form):
    """Complete the annual review of the programme."""

    completed_on = forms.DateField(label="Completed")
