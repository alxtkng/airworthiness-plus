"""Read aircraft defect reports, written orders and planning records together."""

from datetime import date
from typing import Any
from uuid import UUID

from django import forms
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from airworthiness_plus.accounts.permissions import requires
from airworthiness_plus.accounts.roles import Action
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts.models import WorkOrder
from airworthiness_plus.defects.models import Defect
from airworthiness_plus.planning.models import WorkPackage


class HistoryForm(forms.Form):
    aircraft = forms.ModelChoiceField(
        queryset=Aircraft.objects.none(), required=False, empty_label="All Aircraft"
    )
    ata = forms.RegexField(
        r"^(?:0[1-9]|[1-9][0-9]?)(?:-[0-9]{2})?$",
        label="ATA Chapter or Section",
        required=False,
        max_length=5,
        help_text="Enter a chapter such as 25 or a section such as 25-21.",
    )
    from_date = forms.DateField(
        label="From", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    to_date = forms.DateField(
        label="To", required=False, widget=forms.DateInput(attrs={"type": "date"})
    )
    state = forms.ChoiceField(
        choices=[("", "Any State"), ("open", "Open"), ("closed", "Closed")], required=False
    )
    source = forms.ChoiceField(
        choices=[
            ("", "Any Source"),
            ("defects", "Defects"),
            ("contracts", "Contracts"),
            ("planning", "Planning"),
        ],
        required=False,
    )
    record_type = forms.ChoiceField(
        choices=[
            ("", "Any Record Type"),
            ("defect", "Defect"),
            ("order", "Written Work Order"),
            ("package", "Work Package"),
        ],
        required=False,
    )
    report = forms.CharField(label="Report Text", required=False, max_length=200)
    rectification = forms.CharField(label="Corrective Action", required=False, max_length=200)

    def __init__(self, data: Any, aircraft: Aircraft | None) -> None:
        super().__init__(data, label_suffix="")
        if aircraft is not None:
            del self.fields["aircraft"]
        else:
            self.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        values = super().clean() or {}
        start, end = values.get("from_date"), values.get("to_date")
        if start and end and start > end:
            self.add_error("to_date", "The End Date Is on or After the Start Date")
        return values


def _date_and_state(values: dict[str, Any], date_field: str, closed_field: str) -> Q:
    filters = Q()
    for label, lookup in (("from_date", "gte"), ("to_date", "lte")):
        value: date | None = values[label]
        if value is not None:
            filters &= Q(**{f"{date_field}__{lookup}": value})
    if values["state"]:
        filters &= Q(**{f"{closed_field}__isnull": values["state"] == "open"})
    return filters


def _defect_filters(values: dict[str, Any], prefix: str = "") -> Q:
    filters = Q()
    if values["ata"]:
        chapter, separator, section = values["ata"].partition("-")
        filters &= Q(**{f"{prefix}chapter": int(chapter)})
        if separator:
            filters &= Q(**{f"{prefix}section": section})
    if values["report"]:
        filters &= Q(**{f"{prefix}title__icontains": values["report"]}) | Q(
            **{f"{prefix}note__icontains": values["report"]}
        )
    if values["rectification"]:
        filters &= Q(**{f"{prefix}rectification__icontains": values["rectification"]})
    return filters


def _chosen(values: dict[str, Any], source: str, record_type: str) -> bool:
    return values["source"] in ("", source) and values["record_type"] in ("", record_type)


@never_cache
@requires(Action.VIEW_RECORDS)
@require_GET
def page(request: HttpRequest, aircraft_id: UUID | None = None) -> HttpResponse:
    aircraft = get_object_or_404(Aircraft, pk=aircraft_id) if aircraft_id else None
    form = HistoryForm(request.GET, aircraft)
    context: dict[str, Any] = {"aircraft": aircraft, "form": form}
    if form.is_valid():
        values = form.cleaned_data
        selected = aircraft or values.get("aircraft")
        scope = Q(aircraft=selected) if selected else Q()
        if _chosen(values, "defects", "defect"):
            context["defects"] = (
                Defect.objects.filter(
                    scope
                    & _date_and_state(values, "found_on", "closed_on")
                    & _defect_filters(values)
                )
                .select_related("aircraft")
                .prefetch_related("work_packages__order")
                .order_by("-found_on", "title", "id")
            )
        if _chosen(values, "contracts", "order"):
            context["orders"] = (
                WorkOrder.objects.filter(
                    scope
                    & _date_and_state(values, "agreed_on", "closed_on")
                    & _defect_filters(values, "packages__defect__")
                )
                .select_related("aircraft")
                .order_by("-agreed_on", "id")
                .distinct()
            )
        if _chosen(values, "planning", "package"):
            context["packages"] = (
                WorkPackage.objects.filter(
                    scope
                    & _date_and_state(values, "starts_on", "released_on")
                    & _defect_filters(values, "defect__")
                )
                .select_related("aircraft", "defect", "order")
                .prefetch_related("cards")
                .order_by("-starts_on", "reference", "id")
            )
    return render(request, "defects/maintenance_history.html", context)
