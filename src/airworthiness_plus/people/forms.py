"""Forms for person records. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.models import Employment, Person, StaffGroup


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
