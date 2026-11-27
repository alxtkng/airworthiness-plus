"""Forms for the Users page and the change of password."""

from typing import Any

from django import forms

from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.models import Person


class AddUserForm(Form):
    """Add a user with their roles and a first password.

    The sign-in is for a new person, named here, or for a person already
    recorded who has no sign-in, chosen here. Nobody is found by name
    (REQ-204).
    """

    person = forms.ModelChoiceField(
        label="Recorded Person with No Sign-In",
        queryset=Person.objects.none(),
        required=False,
        empty_label="A New Person",
    )
    full_name = forms.CharField(label="Full Name of a New Person", max_length=200, required=False)
    username = forms.EmailField(label="User Name", max_length=254)
    roles = forms.MultipleChoiceField(
        label="Roles", choices=Role.choices, widget=forms.CheckboxSelectMultiple, required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        # People of the organisation, still here, who have no sign-in.
        without = Person.objects.filter(user__isnull=True, left_on__isnull=True)
        self.fields["person"].queryset = without  # type: ignore[attr-defined]

    def clean(self) -> dict[str, Any]:
        """A new person has a name; a person chosen brings their own."""
        data = super().clean() or {}
        if data.get("person") is None and not (data.get("full_name") or "").strip():
            self.add_error("full_name", "Give a Full Name, or Choose a Person")
        return data


class RolesForm(Form):
    """Set the roles a user holds."""

    roles = forms.MultipleChoiceField(
        label="Roles", choices=Role.choices, widget=forms.CheckboxSelectMultiple, required=False
    )


class ChangePasswordForm(Form):
    """Change the signed-in user's own password."""

    current = forms.CharField(
        label="Current Password", widget=forms.PasswordInput, max_length=200, strip=False
    )
    new = forms.CharField(
        label="New Password", widget=forms.PasswordInput, max_length=200, strip=False
    )
    again = forms.CharField(
        label="New Password Again", widget=forms.PasswordInput, max_length=200, strip=False
    )
    code = forms.CharField(
        label="Code From Your Authenticator Application", max_length=12, required=False
    )
