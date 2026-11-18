"""Forms for maintenance data. Labels follow design-system/Writing.md."""

from django import forms

from airworthiness_plus.maintenance_data.models import Evidence, Kind


class DataSetForm(forms.Form):
    """Record a set of maintenance data."""

    title = forms.CharField(label="Title", max_length=200)
    author = forms.CharField(label="Author", max_length=200)
    kind = forms.ChoiceField(label="Kind", choices=Kind.choices)
    applies_to = forms.CharField(
        label="Applies to Type Ratings, One on Each Line",
        widget=forms.Textarea,
        required=False,
        strip=False,
    )
    mandatory = forms.BooleanField(
        label="Carries Mandatory Instructions or Airworthiness Limitations", required=False
    )
    held = forms.BooleanField(label="Held", required=False, initial=True)
    revision = forms.CharField(label="Revision", max_length=60, required=False)
    revision_date = forms.DateField(label="Revision Date", required=False)
    amendment_service = forms.CharField(label="Amendment Service", max_length=200, required=False)
    check_due = forms.DateField(label="Next Amendment Check By", required=False)
    provided_by = forms.CharField(
        label="Provided By, If Customer-Provided", max_length=200, required=False
    )
    evidence = forms.ChoiceField(
        label="Amendment Status Shown By",
        choices=[("", "Not Customer-Provided"), *Evidence.choices],
        required=False,
    )
    evidence_dated = forms.DateField(label="Shown On", required=False)

    def clean_applies_to(self) -> list[str]:
        """Split into type ratings, each kept exactly as typed."""
        return [
            line.strip() for line in self.cleaned_data["applies_to"].splitlines() if line.strip()
        ]


class RevisionForm(forms.Form):
    """Record a new revision."""

    revision = forms.CharField(label="Revision", max_length=60)
    revision_date = forms.DateField(label="Revision Date")


class CheckForm(forms.Form):
    """Record a check of the amendment status."""

    checked_on = forms.DateField(label="Checked")
    result = forms.CharField(label="Result", max_length=200)
    next_due = forms.DateField(label="Next Amendment Check By")


class CustomerStatusForm(forms.Form):
    """Record how the customer showed the amendment status of their data."""

    evidence = forms.ChoiceField(label="Amendment Status Shown By", choices=Evidence.choices)
    dated = forms.DateField(label="Shown On")


class EndHoldingForm(forms.Form):
    """Mark data as No Longer Held."""

    on = forms.DateField(label="No Longer Held From")
