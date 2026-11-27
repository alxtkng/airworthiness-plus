"""Forms for components. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components.models import Basis, Component, Installation
from airworthiness_plus.interface.forms import Form
from airworthiness_rules.components import (
    MOST_CYCLES,
    MOST_HOURS,
    MOST_LIMIT_CYCLES,
    MOST_LIMIT_HOURS,
    MOST_LIMIT_MONTHS,
    MOST_REVIEW_HOURS,
)


def _hours(label: str, *, required: bool = True, most: Any = MOST_HOURS) -> forms.DecimalField:
    return forms.DecimalField(
        label=label,
        max_digits=8,
        decimal_places=1,
        min_value=0,
        max_value=most,
        required=required,
    )


def _cycles(label: str, *, most: int = MOST_CYCLES) -> forms.IntegerField:
    return forms.IntegerField(label=label, min_value=0, max_value=most, required=False)


class LimitForm(Form):
    """The limit of a component (ML.A.503)."""

    basis = forms.ChoiceField(label="Limit", choices=Basis.choices)
    source = forms.CharField(label="Source of the Limit", max_length=200, required=False)
    limit_hours = _hours("Limit in Hours", required=False, most=MOST_LIMIT_HOURS)
    limit_cycles = forms.IntegerField(
        label="Limit in Cycles", min_value=1, max_value=MOST_LIMIT_CYCLES, required=False
    )
    limit_months = forms.IntegerField(
        label="Limit in Months", min_value=1, max_value=MOST_LIMIT_MONTHS, required=False
    )
    limit_date = forms.DateField(label="Date on the Component", required=False)
    date_label = forms.CharField(label="What the Date Is", max_length=60, required=False)
    review_hours = _hours(
        "On Condition, Reviewed Every, Hours", required=False, most=MOST_REVIEW_HOURS
    )
    last_review_hours = _hours("Airframe Hours at the Last Review", required=False)
    last_review_on = forms.DateField(label="Last Reviewed", required=False)


class ComponentForm(LimitForm):
    """Add a component with its limit."""

    name = forms.CharField(label="Component", max_length=200)
    part_number = forms.CharField(label="Part Number", max_length=60, required=False)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)

    field_order = ["name", "part_number", "serial_number"]


class FitForm(Form):
    """Record that a component was fitted to an aircraft (ML.A.305(e))."""

    aircraft = forms.ModelChoiceField(
        label="Aircraft Registration", queryset=Aircraft.objects.none()
    )
    position = forms.CharField(label="Position", max_length=100)
    fitted_on = forms.DateField(label="Fitted")
    airframe_hours_fitted = _hours("Airframe Hours When Fitted")
    airframe_cycles_fitted = _cycles("Airframe Cycles When Fitted")
    hours_at_fitting = _hours("Hours Since New or Overhaul When Fitted")
    cycles_at_fitting = _cycles("Cycles Since New or Overhaul When Fitted")
    life_from = forms.DateField(label="New or Last Overhauled", required=False)
    release_document = forms.CharField(label="Release Document", max_length=100, required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        """Take no cycles given as none."""
        values = super().clean() or {}
        for name in ("airframe_cycles_fitted", "cycles_at_fitting"):
            if values.get(name) is None:
                values[name] = 0
        return values


class RemoveForm(Form):
    """Record that a component was removed."""

    removed_on = forms.DateField(label="Removed")
    airframe_hours_removed = _hours("Airframe Hours When Removed")
    airframe_cycles_removed = forms.IntegerField(
        label="Airframe Cycles When Removed", min_value=0, max_value=MOST_CYCLES
    )
    removal_reason = forms.CharField(label="Reason for Removal", max_length=200)
    sent_to = forms.CharField(label="Sent To", max_length=200, required=False)
    due_back_on = forms.DateField(label="Due Back", required=False)


class FittingChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Installation) -> str:
        return f"{obj.aircraft_registration}, {obj.position}, Fitted {obj.fitted_on:%d %B %Y}"


class ReviewForm(Form):
    """Record a review of a component kept on condition."""

    airframe_hours = _hours("Airframe Hours at the Review")
    reviewed_on = forms.DateField(label="Reviewed")
    installation = FittingChoice(
        label="Fitting Used for the Airframe Hours",
        queryset=Installation.objects.none(),
        required=False,
        help_text="Choose the fitting if more than one matches the date and hours",
    )

    def __init__(self, *args: Any, component: Component, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["installation"].queryset = component.installations.all()  # type: ignore[attr-defined]


class LifeFromForm(Form):
    """Record the day a component was new or last overhauled."""

    life_from = forms.DateField(label="New or Last Overhauled")
