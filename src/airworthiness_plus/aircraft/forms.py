"""Forms for aircraft records. Labels follow design-system/Writing.md."""

import uuid

from django import forms

from airworthiness_plus.aircraft.models import Counter, CounterKind, Regime, UtilisationEntry


class AddAircraftForm(forms.Form):
    """Add an aircraft to the Fleet, or as a Transfer In."""

    registration = forms.CharField(label="Aircraft Registration", max_length=10)
    type_rating = forms.CharField(label="Type Rating", max_length=200, strip=False)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)
    owner = forms.CharField(label="Owned By", max_length=200)
    regime = forms.ChoiceField(label="Regime", choices=Regime.choices)
    dated = forms.DateField(label="Date of Airframe Hours", required=False)
    hours = forms.DecimalField(
        label="Airframe Hours", max_digits=8, decimal_places=1, min_value=0, required=False
    )
    cycles = forms.IntegerField(label="Airframe Cycles", min_value=0, required=False)
    records_expected = forms.IntegerField(
        label="Records Expected, for a Transfer In", min_value=1, required=False
    )

    def clean(self) -> dict[str, object]:
        """Hours, cycles and their date are given together or not at all."""
        cleaned = super().clean() or {}
        given = [cleaned.get(name) is not None for name in ("dated", "hours", "cycles")]
        if any(given) and not all(given):
            raise forms.ValidationError("Give the Date, Hours and Cycles Together")
        return cleaned


class UtilisationForm(forms.Form):
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
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        counters = Counter.objects.filter(aircraft_id=aircraft_id)
        self.fields["counter"].queryset = counters  # type: ignore[attr-defined]
        self.fields["supersedes"].queryset = UtilisationEntry.objects.filter(  # type: ignore[attr-defined]
            counter__in=counters, superseded_by__isnull=True
        )


class UnserviceableForm(forms.Form):
    """Record an aircraft as Unserviceable."""

    reason = forms.CharField(label="Reason", max_length=200)
    since = forms.DateField(label="Unserviceable Since")


class CounterForm(forms.Form):
    """Add an engine or a propeller as a counter."""

    kind = forms.ChoiceField(
        label="Counter",
        choices=[(CounterKind.ENGINE, "Engine"), (CounterKind.PROPELLER, "Propeller")],
    )
    position = forms.CharField(label="Position", max_length=40)
    serial_number = forms.CharField(label="Serial Number", max_length=60, required=False)


class RecordsReceivedForm(forms.Form):
    """Update the count of records received for a Transfer In."""

    received = forms.IntegerField(label="Records Received", min_value=0)
