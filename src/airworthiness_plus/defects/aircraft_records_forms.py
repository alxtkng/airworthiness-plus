"""Forms for the aircraft damage register and flight technical log."""

import re
from datetime import date
from typing import Any

from django import forms

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components.models import Component
from airworthiness_plus.defects.models import (
    AircraftDrawing,
    DamageEntry,
    Defect,
    FlightEvent,
    FlightReport,
    ReportKind,
)
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.programme.models import Task, WorkDone
from airworthiness_plus.releases.models import Release
from airworthiness_rules.defects import FIRST_CHAPTER, LAST_CHAPTER


class DrawingForm(Form):
    reference = forms.CharField(label="Drawing Reference", max_length=100)
    view = forms.CharField(label="View Name", max_length=100)
    revision = forms.CharField(label="Revision", max_length=40)
    outline = forms.CharField(
        label="Outline Points",
        max_length=1000,
        help_text=(
            "Enter three or more X,Y pairs separated by spaces. "
            "Use whole numbers from 0 to 100, measured from the top left."
        ),
    )

    def clean_outline(self) -> str:
        points = self.cleaned_data["outline"].split()
        if len(set(points)) < 3 or not all(
            re.fullmatch(r"(?:100|[0-9]{1,2}),(?:100|[0-9]{1,2})", point) for point in points
        ):
            raise forms.ValidationError("Enter at least three distinct points within the view.")
        return " ".join(points)


class DamageForm(Form):
    title = forms.CharField(label="Finding", max_length=200)
    found_on = forms.DateField(
        label="Found On", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    frame_or_zone = forms.CharField(label="Physical Frame or Zone", max_length=150)
    dimensions = forms.CharField(label="Dimensions and Units", max_length=150)
    evidence = forms.CharField(label="Finding Evidence Reference", max_length=200)
    applicable_reference = forms.CharField(
        label="Applicable Reference and Revision", max_length=200
    )
    disposition = forms.CharField(label="Disposition", max_length=200)
    marker_x = forms.IntegerField(label="Marker X", min_value=0, max_value=100)
    marker_y = forms.IntegerField(label="Marker Y", min_value=0, max_value=100)
    defect = forms.ModelChoiceField(
        label="Linked Defect", queryset=Defect.objects.none(), required=False
    )
    repair = forms.ModelChoiceField(
        label="Repair Work Done", queryset=WorkDone.objects.none(), required=False
    )
    follow_up = forms.ModelChoiceField(
        label="Follow-up Programme Task", queryset=Task.objects.none(), required=False
    )
    drawing = forms.ModelChoiceField(
        label="Drawing Revision", queryset=AircraftDrawing.objects.none()
    )

    def __init__(self, *args: Any, aircraft: Aircraft, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["drawing"].queryset = AircraftDrawing.objects.filter(  # type: ignore[attr-defined]
            aircraft=aircraft, superseded_by__isnull=True
        )
        self.fields["defect"].queryset = Defect.objects.filter(aircraft=aircraft)  # type: ignore[attr-defined]
        self.fields["repair"].queryset = WorkDone.objects.filter(aircraft=aircraft)  # type: ignore[attr-defined]
        self.fields["follow_up"].queryset = Task.objects.filter(programme__aircraft=aircraft)  # type: ignore[attr-defined]

    def clean_found_on(self) -> date:
        found_on: date = self.cleaned_data["found_on"]
        if found_on > aircraft_services.today():
            raise forms.ValidationError("A finding cannot be recorded as found after today.")
        return found_on

    @classmethod
    def for_revision(cls, entry: DamageEntry) -> "DamageForm":
        initial = {field: getattr(entry, field) for field in cls.base_fields}
        drawing = AircraftDrawing.objects.filter(supersedes=entry.drawing).first()
        if drawing:
            while newer := AircraftDrawing.objects.filter(supersedes=drawing).first():
                drawing = newer
            initial["drawing"] = drawing
        return cls(aircraft=entry.aircraft, initial=initial)


class FlightForm(Form):
    reference = forms.CharField(label="Flight Reference", max_length=100)
    flown_on = forms.DateField(
        label="Flight Date", widget=forms.DateInput(format="%Y-%m-%d", attrs={"type": "date"})
    )
    departure = forms.CharField(label="Departure", max_length=100)
    arrival = forms.CharField(label="Arrival", max_length=100)

    def clean_flown_on(self) -> date:
        flown_on: date = self.cleaned_data["flown_on"]
        if flown_on > aircraft_services.today():
            raise forms.ValidationError("A flight cannot be recorded as flown after today.")
        return flown_on


class ComponentChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Component) -> str:
        return ", ".join(part for part in (obj.name, obj.identity) if part)


class FlightReportForm(Form):
    kind = forms.ChoiceField(label="Report Type", choices=ReportKind.choices)
    chapter = forms.IntegerField(
        label="ATA Chapter", min_value=FIRST_CHAPTER, max_value=LAST_CHAPTER
    )
    section = forms.RegexField(r"^[0-9]{2}$", label="ATA Section", max_length=2, required=False)
    component = ComponentChoice(
        label="Linked Component", queryset=Component.objects.none(), required=False
    )
    defect = forms.ModelChoiceField(
        label="Linked Defect", queryset=Defect.objects.none(), required=False
    )
    source_reference = forms.CharField(label="Source Reference", max_length=150)
    reporter = forms.CharField(label="Original Reporter", max_length=200)
    report = forms.CharField(
        label="Original Report", max_length=4000, strip=False, widget=forms.Textarea
    )
    confirmed = forms.BooleanField(label="I checked the attribution and report against the source")

    def __init__(self, *args: Any, flight: FlightEvent, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["component"].queryset = Component.objects.filter(  # type: ignore[attr-defined]
            organisation=flight.organisation
        )
        self.fields["defect"].queryset = Defect.objects.filter(aircraft=flight.aircraft)  # type: ignore[attr-defined]

    def clean_report(self) -> str:
        report: str = self.cleaned_data["report"]
        if not report.strip():
            raise forms.ValidationError("Enter the original report.")
        return report

    def clean(self) -> dict[str, Any]:
        values = super().clean() or {}
        defect = values.get("defect")
        if defect and (defect.chapter, defect.section) != (
            values.get("chapter"),
            values.get("section"),
        ):
            self.add_error("defect", "The ATA classification must match the linked defect.")
        return values


class LogFilter(forms.Form):
    chapter = forms.RegexField(
        r"^[0-9]{1,2}(?:-[0-9]{2})?$", label="ATA Chapter or Section", required=False
    )
    part = forms.CharField(label="Linked Part Number", max_length=60, required=False)


class ReportReleaseForm(Form):
    release = forms.ModelChoiceField(
        label="Existing Certificate of Release to Service", queryset=Release.objects.none()
    )

    def __init__(self, *args: Any, report: FlightReport, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if (defect := report.defect) and defect.work_done_id:
            self.fields["release"].queryset = Release.objects.filter(  # type: ignore[attr-defined]
                work_id=defect.work_done_id,
                issued_on__gte=report.flight.flown_on,
            )
