"""Forms for certificates of release to service. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.people.forms import CertificationEvidenceForm
from airworthiness_plus.people.models import Person, StaffGroup
from airworthiness_plus.releases.models import IssuedBy


class CertificateForm(CertificationEvidenceForm, Form):
    """Record the certificate of release to service for work done (ML.A.801(e))."""

    reference = forms.CharField(label="Certificate Reference", max_length=100)
    kind = forms.ChoiceField(label="Issued By", choices=IssuedBy.choices)
    issued_by = forms.ModelChoiceField(
        label="Certifying Staff of the Organisation",
        queryset=Person.objects.none(),
        required=False,
        empty_label="Not of the Organisation",
    )
    issuer_name = forms.CharField(
        label="Name of Independent Certifying Staff or Pilot-Owner", max_length=200, required=False
    )
    licence = forms.CharField(label="Licence Number", max_length=100, required=False)
    issued_on = forms.DateField(label="Issued")
    incomplete = forms.BooleanField(label="Maintenance Could Not Be Completed", required=False)
    limitations = forms.CharField(label="Limitations", max_length=200, required=False)
    recorded_on = forms.DateField(label="Entered in the Records, If Before Today", required=False)

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["issued_by"].queryset = Person.objects.filter(  # type: ignore[attr-defined]
            staff_group=StaffGroup.CERTIFYING
        )


class HistoricalReleaseEvidenceForm(Form):
    """Identify the signed source for an unverified historical release."""

    reference = forms.CharField(label="Signed Release Reference", max_length=100)
    issuer_name = forms.CharField(label="Issuer Named in the Source", max_length=200)
    issued_on = forms.DateField(label="Date on the Signed Release")
    source = forms.CharField(label="Signed Evidence Reference", max_length=200)
