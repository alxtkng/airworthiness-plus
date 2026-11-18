"""Forms for airworthiness review records. Labels follow design-system/Writing.md."""

from django import forms

from airworthiness_plus.accounts.models import User
from airworthiness_plus.reviews.models import ReviewStaff


class CertificateForm(forms.Form):
    """Record a certificate issued by another organisation or the authority."""

    reference = forms.CharField(label="Certificate Reference", max_length=80)
    issued_elsewhere_by = forms.CharField(label="Issued By", max_length=200)
    issued_on = forms.DateField(label="Date of Issue")
    valid_to = forms.DateField(label="Date of Expiry")
    airframe_hours = forms.DecimalField(
        label="Airframe Flight Hours at the Review",
        max_digits=8,
        decimal_places=1,
        min_value=0,
        required=False,
    )


class ExtensionForm(forms.Form):
    """Confirm each condition of ML.A.901(c) before extending a certificate."""

    managed_for_12_months = forms.BooleanField(
        label="Continuously Managed by This Organisation for the Previous 12 Months",
        required=False,
    )
    maintained_by_approved_organisations = forms.BooleanField(
        label="Maintained for the Previous 12 Months by Approved Maintenance Organisations",
        required=False,
    )
    no_evidence_not_airworthy = forms.BooleanField(
        label="No Evidence or Reason to Believe the Aircraft Is Not Airworthy", required=False
    )


class CopySentForm(forms.Form):
    """Record the day the copy went to the Civil Aviation Authority."""

    on = forms.DateField(label="Copy Sent")


class ReviewStaffForm(forms.Form):
    """Record a person as airworthiness review staff."""

    user = forms.ModelChoiceField(label="Person", queryset=User.objects.none())
    authorisation_reference = forms.CharField(label="Authorisation Reference", max_length=60)
    accepted_on = forms.DateField(label="Accepted")
    part_66_qualified = forms.BooleanField(label="Qualified Under Part-66", required=False)
    months_involved = forms.IntegerField(
        label="Months of Continuing Airworthiness Management in the 2-Year Period",
        min_value=0,
        max_value=24,
        initial=0,
    )
    last_review_before_records = forms.DateField(
        label="Last Review Before These Records", required=False
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["user"].queryset = User.objects.filter(  # type: ignore[attr-defined]
            is_active=True, review_staff__isnull=True
        )


class InvolvementForm(forms.Form):
    """Change the recorded months of involvement or the last review before these records."""

    months = forms.IntegerField(
        label="Months of Continuing Airworthiness Management in the 2-Year Period",
        min_value=0,
        max_value=24,
    )
    last_review_before_records = forms.DateField(
        label="Last Review Before These Records", required=False
    )


class RestorationForm(forms.Form):
    """Record a review under supervision that restores a lapsed authorisation."""

    on = forms.DateField(label="Review Under Supervision")
    supervisor = forms.ModelChoiceField(
        label="Supervised by Review Staff", queryset=ReviewStaff.objects.none(), required=False
    )
    under = forms.CharField(
        label="Or Supervised by the Civil Aviation Authority, Named", max_length=200, required=False
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.fields["supervisor"].queryset = ReviewStaff.objects.filter(  # type: ignore[attr-defined]
            left_on__isnull=True
        )
