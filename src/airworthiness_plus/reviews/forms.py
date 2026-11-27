"""Forms for airworthiness review records. Labels follow design-system/Writing.md."""

from django import forms

from airworthiness_plus.accounts.models import User
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.reviews.models import ProgrammeDiscrepancy, Result, ReviewStaff


def _name_and_authorisation(staff: ReviewStaff) -> str:
    return f"{staff.user.full_name}, {staff.authorisation_reference}"


class CertificateForm(Form):
    """Record a certificate that was not issued in these records.

    One issued by another organisation or the authority, or one the
    organisation's own review staff issued before these records.
    """

    reference = forms.CharField(label="Certificate Reference", max_length=80)
    issued_by = forms.ModelChoiceField(
        label="Issued by Review Staff of This Organisation, Before These Records",
        queryset=ReviewStaff.objects.none(),
        required=False,
    )
    issued_elsewhere_by = forms.CharField(
        label="Or Issued Elsewhere By", max_length=200, required=False
    )
    issued_on = forms.DateField(label="Date of Issue")
    valid_to = forms.DateField(label="Date of Expiry")
    airframe_hours = forms.DecimalField(
        label="Airframe Flight Hours at the Review",
        max_digits=8,
        decimal_places=1,
        min_value=0,
        required=False,
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        # Those who have left are offered too: they issued certificates before they went.
        field = self.fields["issued_by"]
        field.queryset = ReviewStaff.objects.select_related("user")  # type: ignore[attr-defined]
        field.label_from_instance = _name_and_authorisation  # type: ignore[attr-defined]


class ExtensionForm(Form):
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


class CopySentForm(Form):
    """Record the day the copy went to the Civil Aviation Authority."""

    on = forms.DateField(label="Copy Sent")


class ReviewStaffForm(Form):
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
        super().__init__(*args, **kwargs)
        self.fields["user"].queryset = User.objects.filter(  # type: ignore[attr-defined]
            is_active=True, review_staff__isnull=True
        )


class InvolvementForm(Form):
    """Change the recorded months of involvement or the last review before these records."""

    months = forms.IntegerField(
        label="Months of Continuing Airworthiness Management in the 2-Year Period",
        min_value=0,
        max_value=24,
    )
    last_review_before_records = forms.DateField(
        label="Last Review Before These Records", required=False
    )


class RestorationForm(Form):
    """Record a review under supervision that restores a lapsed authorisation."""

    on = forms.DateField(label="Review Under Supervision")
    supervisor = forms.ModelChoiceField(
        label="Supervised by Review Staff", queryset=ReviewStaff.objects.none(), required=False
    )
    under = forms.CharField(
        label="Or Supervised by the Civil Aviation Authority, Named", max_length=200, required=False
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["supervisor"].queryset = ReviewStaff.objects.filter(  # type: ignore[attr-defined]
            left_on__isnull=True
        )


class ItemForm(Form):
    """Record the result of one point of a review. No result is chosen in advance."""

    result = forms.ChoiceField(label="Result", choices=[("", "Choose"), *Result.choices])
    evidence = forms.CharField(label="Evidence Sampled", max_length=300)
    finding = forms.CharField(label="Finding", max_length=300, required=False)

    def __init__(self, *args: object, may_not_apply: bool = True, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        if not may_not_apply:
            result = self.fields["result"]
            assert isinstance(result, forms.ChoiceField)  # noqa: S101  declared above
            result.choices = [
                ("", "Choose"),
                *(
                    (value, label)
                    for value, label in Result.choices
                    if value != Result.NOT_APPLICABLE
                ),
            ]


class ClosureForm(Form):
    """Record how a finding was closed."""

    closure = forms.CharField(label="How It Was Closed", max_length=300)


class DetailsForm(Form):
    """Record who assisted at the survey, the airframe hours and the state of the programme."""

    assisted_by = forms.CharField(label="Assisted at the Survey By", max_length=200, required=False)
    airframe_hours = forms.DecimalField(
        label="Airframe Flight Hours at the Review",
        max_digits=8,
        decimal_places=1,
        min_value=0,
        required=False,
    )
    programme_discrepancy = forms.ChoiceField(
        label="Maintenance Programme",
        choices=[("", "Choose"), *ProgrammeDiscrepancy.choices],
        required=False,
    )


class VoidForm(Form):
    """Void a certificate."""

    reason = forms.CharField(label="Reason", max_length=200)
