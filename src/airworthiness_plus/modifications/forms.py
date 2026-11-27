"""Forms for service bulletins, changes, repairs and weighings (design-system/Writing.md)."""

from typing import Any

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.modifications.models import Classification, Data, OwnerDecision, Route
from airworthiness_rules.mass import MOST_MASS

DECISIONS = [
    (OwnerDecision.ACCEPTED.value, OwnerDecision.ACCEPTED.label),
    (OwnerDecision.DECLINED.value, OwnerDecision.DECLINED.label),
]


def _aircraft() -> "forms.ModelChoiceField[Aircraft]":
    return forms.ModelChoiceField(label="Aircraft Registration", queryset=Aircraft.objects.none())


def _of_the_organisation(form: Form) -> None:
    """Offer the aircraft of the organisation that is signed in."""
    form.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]


class BulletinForm(Form):
    """Record a service bulletin sent to the owner, with the decision if it is made."""

    aircraft = _aircraft()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _of_the_organisation(self)

    title = forms.CharField(label="Bulletin", max_length=200)
    reference = forms.CharField(label="Reference", max_length=100)
    classification = forms.ChoiceField(label="Classification", choices=Classification.choices)
    sent_on = forms.DateField(label="Sent to the Owner")
    reminder_on = forms.DateField(label="Reminder", required=False)
    decision = forms.ChoiceField(
        label="Owner Decision", choices=OwnerDecision.choices, required=False
    )
    detail = forms.CharField(label="Decision in Detail", max_length=200, required=False)
    decided_on = forms.DateField(label="Recorded", required=False)

    def clean_decision(self) -> str:
        """Take no decision given as one still awaited."""
        return self.cleaned_data["decision"] or OwnerDecision.AWAITING.value


class DecisionForm(Form):
    """Record what the owner decided of a service bulletin."""

    decision = forms.ChoiceField(label="Owner Decision", choices=DECISIONS)
    detail = forms.CharField(label="Decision in Detail", max_length=200)
    decided_on = forms.DateField(label="Recorded")


class ChangeForm(Form):
    """Record a change or repair (ML.A.304)."""

    aircraft = _aircraft()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _of_the_organisation(self)

    title = forms.CharField(label="Change or Repair", max_length=200)
    route = forms.ChoiceField(label="Approval Route", choices=Route.choices)
    data_kind = forms.ChoiceField(
        label="Data, ML.A.304",
        choices=[("", "As the Approval Route Gives"), *Data.choices],
        required=False,
    )
    reference = forms.CharField(label="Reference", max_length=100, required=False)
    mass_effect = forms.DecimalField(
        label="Mass Effect, Kilograms",
        max_digits=4,
        decimal_places=1,
        min_value=-MOST_MASS,
        max_value=MOST_MASS,
    )
    embodied_on = forms.DateField(label="Embodied, If Not in Progress", required=False)


class EmbodiedForm(Form):
    """Record the day a change or repair in progress was embodied."""

    embodied_on = forms.DateField(label="Embodied")


class WeighingForm(Form):
    """Record a weighing of an aircraft."""

    aircraft = _aircraft()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _of_the_organisation(self)

    weighed_on = forms.DateField(label="Weighed")
    reference = forms.CharField(label="Weighing Report", max_length=100)


class ScheduleForm(Form):
    """Record an issue of an aircraft's weight schedule."""

    aircraft = _aircraft()

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        _of_the_organisation(self)

    issue = forms.IntegerField(label="Issue", min_value=1, max_value=9999)
    issued_on = forms.DateField(label="Issued")
