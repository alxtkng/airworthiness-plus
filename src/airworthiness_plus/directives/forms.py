"""Forms for airworthiness directives. Labels follow design-system/Writing.md."""

import uuid

from django import forms

from airworthiness_plus.aircraft.models import Counter
from airworthiness_plus.directives.models import Decision, Directive
from airworthiness_plus.interface.forms import Form


class DirectiveForm(Form):
    """Record a directive."""

    number = forms.CharField(label="Directive Number", max_length=60)
    authority = forms.CharField(label="Issuing Authority", max_length=100)
    subject = forms.CharField(label="Subject", max_length=200)
    effective_date = forms.DateField(label="Effective Date")
    revision = forms.CharField(label="Revision", max_length=40, required=False)
    supersedes = forms.ModelChoiceField(
        label="Supersedes", queryset=Directive.objects.none(), required=False
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["supersedes"].queryset = Directive.objects.filter(  # type: ignore[attr-defined]
            superseded_by__isnull=True
        )


class DecisionForm(Form):
    """Decide whether a directive applies to one aircraft. Nothing is chosen in advance."""

    decision = forms.ChoiceField(label="Applicability", choices=[("", "Choose"), *Decision.choices])
    basis = forms.CharField(label="Basis", max_length=300)
    counter = forms.ModelChoiceField(
        label="Action Runs Against", queryset=Counter.objects.none(), required=False
    )
    starts_dated = forms.DateField(label="Counted From", required=False)
    starts_hours = forms.DecimalField(
        label="Hours Then", max_digits=8, decimal_places=1, min_value=0, required=False
    )
    starts_cycles = forms.IntegerField(label="Cycles Then", min_value=0, required=False)
    first_hours = forms.DecimalField(
        label="First Within Hours", max_digits=7, decimal_places=1, min_value=0, required=False
    )
    first_cycles = forms.IntegerField(label="First Within Cycles", min_value=1, required=False)
    first_months = forms.IntegerField(label="First Within Months", min_value=1, required=False)
    first_days = forms.IntegerField(label="First Within Days", min_value=1, required=False)
    repeat_hours = forms.DecimalField(
        label="Then Every Hours", max_digits=7, decimal_places=1, min_value=0, required=False
    )
    repeat_cycles = forms.IntegerField(label="Then Every Cycles", min_value=1, required=False)
    repeat_months = forms.IntegerField(label="Then Every Months", min_value=1, required=False)
    repeat_days = forms.IntegerField(label="Then Every Days", min_value=1, required=False)

    def __init__(self, *args: object, aircraft_id: uuid.UUID, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["counter"].queryset = Counter.objects.filter(  # type: ignore[attr-defined]
            aircraft_id=aircraft_id
        )


class ComplianceForm(Form):
    """Record compliance with a directive on one aircraft."""

    method = forms.CharField(label="Method of Compliance", max_length=120)
    dated = forms.DateField(label="Completed")
    hours = forms.DecimalField(label="Hours", max_digits=8, decimal_places=1, min_value=0)
    cycles = forms.IntegerField(label="Cycles", min_value=0)
    release_reference = forms.CharField(
        label="Certificate of Release to Service", max_length=100, required=False
    )
    release_recorded_on = forms.DateField(
        label="Release Entered in the Records, If Before Today", required=False
    )


class TerminationForm(Form):
    """Record a terminating action."""

    action = forms.CharField(label="Terminating Action", max_length=200)
    on = forms.DateField(label="Terminated")


class SourceForm(Form):
    """Record a source the organisation checks for new directives."""

    name = forms.CharField(label="Source", max_length=200)
    covers = forms.CharField(label="Covers", max_length=300)
    note = forms.CharField(label="Note", max_length=200, required=False)


class SourceCheckForm(Form):
    """Record that a source was checked, and when it is next checked."""

    checked_on = forms.DateField(label="Last Checked")
    next_check_on = forms.DateField(label="Next Check", required=False)
    next_check_note = forms.CharField(label="Next Check in Words", max_length=100, required=False)
