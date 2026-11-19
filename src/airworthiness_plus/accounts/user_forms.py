"""Forms for the Users page and the change of password."""

from django import forms

from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.interface.forms import Form


class AddUserForm(Form):
    """Add a user with their roles and a first password."""

    full_name = forms.CharField(label="Full Name", max_length=200)
    username = forms.EmailField(label="User Name", max_length=254)
    roles = forms.MultipleChoiceField(
        label="Roles", choices=Role.choices, widget=forms.CheckboxSelectMultiple, required=False
    )
    password = forms.CharField(
        label="First Password", widget=forms.PasswordInput, max_length=200, strip=False
    )


class RolesForm(Form):
    """Set the roles a user holds."""

    roles = forms.MultipleChoiceField(
        label="Roles", choices=Role.choices, widget=forms.CheckboxSelectMultiple, required=False
    )


class ResetPasswordForm(Form):
    """Give a user a new first password."""

    password = forms.CharField(
        label="New First Password", widget=forms.PasswordInput, max_length=200, strip=False
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
