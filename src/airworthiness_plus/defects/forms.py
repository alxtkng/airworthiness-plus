"""Forms for defects. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects.models import Basis, Decision
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.forms import CertificationEvidenceForm
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.programme.models import WorkDone
from airworthiness_rules.defects import FIRST_CHAPTER, LAST_CHAPTER


class DefectForm(CertificationEvidenceForm, Form):
    """Record a defect and what was decided of it (ML.A.403)."""

    aircraft = forms.ModelChoiceField(
        label="Aircraft Registration", queryset=Aircraft.objects.none()
    )
    title = forms.CharField(label="Defect", max_length=200)
    note = forms.CharField(label="Note", max_length=200, required=False)
    found_on = forms.DateField(label="Found")
    chapter = forms.IntegerField(label="Chapter", min_value=FIRST_CHAPTER, max_value=LAST_CHAPTER)
    section = forms.RegexField(r"^[0-9]{2}$", label="ATA Section", required=False, max_length=2)
    system = forms.CharField(label="System", max_length=100)
    decision = forms.ChoiceField(label="Decision", choices=Decision.choices)
    basis = forms.ChoiceField(
        label="Deferred By", choices=[("", "Not Deferred"), *Basis.choices], required=False
    )
    decided_on = forms.DateField(label="Decided")
    decided_by = forms.ModelChoiceField(
        label="Certifying Staff",
        queryset=Person.objects.none(),
        required=False,
        empty_label="Not Certifying Staff",
    )
    data_limit_on = forms.DateField(
        label="Limit in the Maintenance Data or the Minimum Equipment List", required=False
    )
    rectification = forms.CharField(
        label="Rectification, If Already Rectified", max_length=200, required=False
    )
    closed_on = forms.DateField(label="Closed, If Already Rectified", required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]
        # Everyone who is or was certifying staff: the service refuses one who had
        # left by the day of the decision.
        self.fields["decided_by"].queryset = Person.objects.filter(  # type: ignore[attr-defined]
            staff_group=StaffGroup.CERTIFYING
        )


class CloseForm(Form):
    """Record that a defect is rectified."""

    rectification = forms.CharField(label="Rectification", max_length=200)
    closed_on = forms.DateField(label="Closed")
    work_done = forms.ModelChoiceField(
        label="Work Done", queryset=WorkDone.objects.none(), required=False, empty_label="None"
    )

    def __init__(self, *args: Any, aircraft: Aircraft | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if aircraft is not None:
            self.fields["work_done"].queryset = WorkDone.objects.filter(  # type: ignore[attr-defined]
                aircraft=aircraft
            )


class RepeatActionForm(Form):
    """Record what was done about the same defect on one type."""

    type_rating = forms.CharField(label="Type Rating", max_length=200, strip=False)
    chapter = forms.IntegerField(label="Chapter", min_value=FIRST_CHAPTER, max_value=LAST_CHAPTER)
    action = forms.CharField(label="Action", max_length=200)
