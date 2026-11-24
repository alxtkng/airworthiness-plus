"""Forms for aircraft records. Labels follow design-system/Writing.md."""

import uuid
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from airworthiness_plus.aircraft.models import Counter, CounterKind, Regime, UtilisationEntry
from airworthiness_plus.customers.models import Customer
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.forms import Form
from airworthiness_rules.intervals import Unit


class AddAircraftForm(Form):
    """Add an aircraft to the Fleet, or as a Transfer In."""

    registration = forms.CharField(label="Aircraft Registration", max_length=10)
    type_rating = forms.CharField(label="Type Rating", max_length=200, strip=False)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)
    manufacturer = forms.CharField(label="Aircraft Manufacturer", max_length=100, required=False)
    designation = forms.CharField(
        label="Manufacturer\N{RIGHT SINGLE QUOTATION MARK}s Designation",
        max_length=100,
        required=False,
    )
    customer = forms.ModelChoiceField(
        label="Owned By",
        queryset=Customer.objects.none(),
        required=False,
        empty_label="A New Customer",
    )
    owner = forms.CharField(label="Name of a New Customer", max_length=200, required=False)
    regime = forms.ChoiceField(label="Regime", choices=Regime.choices)
    dated = forms.DateField(label="Date of Airframe Hours", required=False)
    hours = forms.DecimalField(
        label="Airframe Hours", max_digits=8, decimal_places=1, min_value=0, required=False
    )
    cycles = forms.IntegerField(label="Airframe Cycles", min_value=0, required=False)
    records_expected = forms.IntegerField(
        label="Records Expected for a Transfer In", min_value=1, required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.all()  # type: ignore[attr-defined]

    def clean(self) -> dict[str, object]:
        """Hours, cycles and their date are given together or not at all.

        The owner is a customer already recorded or the name of a new one,
        and not both.
        """
        cleaned = super().clean() or {}
        if (cleaned.get("customer") is None) == (not cleaned.get("owner")):
            raise forms.ValidationError("Choose a Customer or Name a New One")
        given = [cleaned.get(name) is not None for name in ("dated", "hours", "cycles")]
        if any(given) and not all(given):
            raise forms.ValidationError("Give the Date, Hours and Cycles Together")
        return cleaned


class DetailsForm(Form):
    """The entries CAA Form 15c carries for the aircraft besides its registration."""

    serial_number = forms.CharField(label="Aircraft Serial Number", max_length=60, required=False)
    manufacturer = forms.CharField(label="Aircraft Manufacturer", max_length=100, required=False)
    designation = forms.CharField(
        label="Manufacturer\N{RIGHT SINGLE QUOTATION MARK}s Designation",
        max_length=100,
        required=False,
    )


class OwnerForm(Form):
    """Record another customer as the owner of an aircraft."""

    customer = forms.ModelChoiceField(label="Owned By", queryset=Customer.objects.none())

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.all()  # type: ignore[attr-defined]


class UtilisationForm(Form):
    """Enter total hours and cycles for one counter on a date."""

    counter = forms.ModelChoiceField(label="Counter", queryset=Counter.objects.none())
    dated = forms.DateField(label="Date")
    hours = forms.DecimalField(label="Total Hours", max_digits=8, decimal_places=1, min_value=0)
    cycles = forms.IntegerField(label="Total Cycles", min_value=0)
    supersedes = forms.ModelChoiceField(
        label="Corrects an Earlier Entry",
        queryset=UtilisationEntry.objects.none(),
        required=False,
    )
    confirmed = forms.BooleanField(label="Confirm This Unusual Increase", required=False)

    def __init__(self, *args: object, aircraft_id: uuid.UUID, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        counters = Counter.objects.filter(aircraft_id=aircraft_id)
        self.fields["counter"].queryset = counters  # type: ignore[attr-defined]
        supersedes = self.fields["supersedes"]
        supersedes.queryset = UtilisationEntry.objects.filter(  # type: ignore[attr-defined]
            counter__in=counters, superseded_by__isnull=True
        ).select_related("counter")
        supersedes.label_from_instance = _entry_label  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        """Refuse a correction of an entry of another counter (REQ-025)."""
        data = super().clean() or {}
        counter, supersedes = data.get("counter"), data.get("supersedes")
        if counter is not None and supersedes is not None and supersedes.counter_id != counter.id:
            raise ValidationError("A Correction Is of an Entry of the Same Counter")
        return data


def _entry_label(entry: UtilisationEntry) -> str:
    """Name an entry as a person reads it: the counter, the date, the totals."""
    return (
        f"{entry.counter}, {formatting.long_date(entry.dated)}, "
        f"{formatting.amount(Unit.HOURS, entry.hours)}, "
        f"{formatting.amount(Unit.CYCLES, entry.cycles)}"
    )


class UnserviceableForm(Form):
    """Record an aircraft as Unserviceable."""

    reason = forms.CharField(label="Reason", max_length=200)
    since = forms.DateField(label="Unserviceable Since")


class CounterForm(Form):
    """Add an engine or a propeller as a counter."""

    kind = forms.ChoiceField(
        label="Counter",
        choices=[(CounterKind.ENGINE, "Engine"), (CounterKind.PROPELLER, "Propeller")],
    )
    position = forms.CharField(label="Position", max_length=40)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)


class RecordsReceivedForm(Form):
    """Update the count of records received for a Transfer In."""

    received = forms.IntegerField(label="Records Received", min_value=0)
