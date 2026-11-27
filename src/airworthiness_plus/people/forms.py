"""Forms for person records. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.models import Employment, ExperienceKind, Person, StaffGroup


class PersonForm(Form):
    """Add a person, or change what is recorded of one."""

    full_name = forms.CharField(label="Name", max_length=200)
    role = forms.CharField(label="Role", max_length=100, required=False)
    staff_group = forms.ChoiceField(
        label="Staff Group", choices=StaffGroup.choices, initial=StaffGroup.OTHER
    )
    reports_to = forms.ModelChoiceField(
        label="Reports To", queryset=Person.objects.none(), required=False, empty_label="None"
    )
    employment = forms.ChoiceField(
        label="Employment", choices=Employment.choices, initial=Employment.EMPLOYED
    )
    licence = forms.CharField(label="Licence", max_length=100, required=False)
    joined_on = forms.DateField(label="Joined", required=False)
    left_on = forms.DateField(label="Left", required=False)

    def __init__(self, *args: Any, person: Person | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # Anyone of the organisation still here, but not the person themselves.
        here = Person.objects.filter(left_on__isnull=True)
        if person is not None:
            here = here.exclude(pk=person.pk)
        self.fields["reports_to"].queryset = here  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        """Give the choices back as the values the records hold."""
        data = super().clean() or {}
        if "staff_group" in data:
            data["staff_group"] = StaffGroup(data["staff_group"])
        if "employment" in data:
            data["employment"] = Employment(data["employment"])
        return data


class MaintenanceAuthorisationForm(Form):
    """Record the reference and conditions on an existing authorisation."""

    reference = forms.CharField(label="Authorisation Reference", max_length=80)
    scope = forms.CharField(label="Scope and Limitations", max_length=400, widget=forms.Textarea)
    valid_from = forms.DateField(label="Valid From")
    valid_to = forms.DateField(label="Valid To", required=False)


class RecurrentTrainingForm(Form):
    """Record completed training from the organisation's evidence."""

    subject = forms.CharField(label="Training Subject", max_length=160)
    evidence_reference = forms.CharField(label="Evidence Reference", max_length=160)
    completed_on = forms.DateField(label="Completed On")
    due_on = forms.DateField(label="Renewal Due On", required=False)


class ExperienceEvidenceForm(Form):
    """Record only evidence already assessed against the authorisation scope."""

    kind = forms.ChoiceField(label="Evidence Type", choices=ExperienceKind.choices)
    evidence_reference = forms.CharField(label="Evidence Reference", max_length=160)
    qualification_basis = forms.CharField(
        label="Basis for Counting the Experience",
        help_text="Explain how the activity or approved employment covers this authorisation.",
        max_length=500,
        widget=forms.Textarea,
    )
    starts_on = forms.DateField(label="Work Date or First Day of Employment")
    ends_on = forms.DateField(label="Last Day of Employment", required=False)
    days = forms.DecimalField(label="Days Credited", required=False, max_digits=3, decimal_places=2)
    aircraft_type = forms.CharField(label="Aircraft Type", required=False, max_length=150)
    aircraft_registration = forms.CharField(
        label="Aircraft Registration", required=False, max_length=16
    )
    licence_subcategory = forms.CharField(
        label="Licence Category or Subcategory", required=False, max_length=30
    )


class ExperienceWithdrawalForm(Form):
    reason = forms.CharField(label="Reason", max_length=400)
