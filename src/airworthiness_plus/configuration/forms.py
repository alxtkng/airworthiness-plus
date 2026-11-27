"""Forms for a transfer in and the configuration of an aircraft (design-system/Writing.md)."""

from typing import Any

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components.models import Component
from airworthiness_plus.configuration.models import ItemState, Product
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.modifications.models import Change


class ItemForm(Form):
    """Record where an item of a transfer in stands."""

    state = forms.ChoiceField(label="State", choices=ItemState.choices)
    note = forms.CharField(label="Note", max_length=200, required=False)


class PositionForm(Form):
    """Add a position to the configuration of an aircraft."""

    product = forms.ChoiceField(label="Product", choices=Product.choices)
    chapter = forms.IntegerField(label="Chapter", min_value=1, max_value=99)
    name = forms.CharField(label="Position", max_length=100)
    required = forms.BooleanField(label="Required Equipment", required=False)
    tracked = forms.BooleanField(label="Tracked by Serial Number", required=False)
    major = forms.BooleanField(label="Major Item", required=False)
    part_number = forms.CharField(label="Part Number", max_length=60, required=False)
    source = forms.CharField(label="Source", max_length=200, required=False)


class RecordPositionForm(Form):
    """Record what is fitted at a position, and where that was read."""

    part_number = forms.CharField(label="Part Number", max_length=60, required=False)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)
    source = forms.CharField(label="Source", max_length=200)
    needs_change = forms.BooleanField(label="Needs a Recorded Change", required=False)
    change = forms.ModelChoiceField(
        label="Change or Repair",
        queryset=Change.objects.none(),
        required=False,
        empty_label="None",
    )
    component = forms.ModelChoiceField(
        label="Component",
        queryset=Component.objects.none(),
        required=False,
        empty_label="None",
    )

    def __init__(self, *args: Any, aircraft: Aircraft | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if aircraft is not None:
            self.fields["change"].queryset = Change.objects.filter(  # type: ignore[attr-defined]
                aircraft=aircraft
            )
            self.fields["component"].queryset = Component.objects.filter(  # type: ignore[attr-defined]
                installations__aircraft=aircraft, installations__removed_on__isnull=True
            )
