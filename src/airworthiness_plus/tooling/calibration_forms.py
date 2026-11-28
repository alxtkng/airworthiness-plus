"""Fields for calibration workflow writes."""

from decimal import Decimal, InvalidOperation
from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.logistics.models import Supplier
from airworthiness_plus.tooling.calibration_models import (
    DecisionOutcome,
    MovementKind,
    Phase,
    ProviderService,
    ProviderStatus,
    Statement,
    ToolServiceProviderAuthorisation,
)
from airworthiness_plus.tooling.forms import approval_field, submission_field


def date_field(label: str, *, required: bool = True) -> forms.DateField:
    return forms.DateField(
        label=label, required=required, widget=forms.DateInput(attrs={"type": "date"})
    )


def measurement_field(
    label: str, *, required: bool = True, nonnegative: bool = False
) -> forms.DecimalField:
    return forms.DecimalField(
        label=label,
        required=required,
        max_digits=16,
        decimal_places=6,
        min_value=Decimal("0") if nonnegative else None,
    )


def evidence_field(label: str, *, required: bool = True) -> forms.CharField:
    return forms.CharField(label=label, required=required, max_length=2000, widget=forms.Textarea)


class ProviderForm(Form):
    request_id = submission_field()
    approval = approval_field()
    supplier = forms.ModelChoiceField(label="Supplier", queryset=Supplier.objects.none())
    service = forms.ChoiceField(
        label="Tool Service", choices=ProviderService.choices, required=False
    )
    site = forms.CharField(label="Maintenance Site", max_length=100)
    facility = forms.CharField(label="Laboratory Facility", max_length=150)
    measurement = forms.CharField(label="Measurement Type", max_length=80, required=False)
    method = forms.CharField(label="Method and Revision", max_length=150)
    unit = forms.CharField(label="Measurement Unit", max_length=24, required=False)
    range_from = measurement_field("Range From", required=False)
    range_to = measurement_field("Range To", required=False)
    valid_from = date_field("Valid From")
    valid_to = date_field("Valid To")
    review_on = date_field("Review By", required=False)
    status = forms.ChoiceField(label="Scope Status", choices=ProviderStatus.choices, required=False)
    accreditation = forms.CharField(
        label="Accreditation and Scope Schedule Reference", max_length=150, required=False
    )
    evidence = evidence_field("Scope Evidence and Decision Basis")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = self.fields["supplier"]
        if isinstance(field, forms.ModelChoiceField):
            field.queryset = Supplier.objects.all()

    def clean_service(self) -> str:
        return str(self.cleaned_data.get("service") or ProviderService.CALIBRATION)

    def clean_status(self) -> str:
        return str(self.cleaned_data.get("status") or ProviderStatus.AUTHORISED)


class OrderForm(Form):
    request_id = submission_field()
    provider = forms.ModelChoiceField(
        label="Provider and Authorised Scope",
        queryset=ToolServiceProviderAuthorisation.objects.none(),
    )
    reference = forms.CharField(label="Order Reference", max_length=60)
    measurement = forms.CharField(label="Measurement Type", max_length=80)
    unit = forms.CharField(label="Measurement Unit", max_length=24)
    range_from = measurement_field("Range From")
    range_to = measurement_field("Range To")
    points = forms.CharField(
        label="Required Test Points",
        max_length=1000,
        help_text="Separate numerical test points with commas.",
    )
    configuration = forms.CharField(label="Direction and Configuration", max_length=150)
    error_limit = measurement_field("Maximum Absolute Error", nonnegative=True)
    error_unit = forms.CharField(label="Error and Uncertainty Unit", max_length=30)
    limits_source = forms.CharField(label="Limits Source and Revision", max_length=200)
    uncertainty_required = forms.BooleanField(
        label="Require Measurement Uncertainty", required=False
    )
    reported_due_on = date_field("Prior Label Deadline", required=False)
    reported_label_source = forms.CharField(
        label="Prior Label Source", max_length=200, required=False
    )
    requested_rule = forms.CharField(
        label="Requested Decision Rule", max_length=200, required=False
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = self.fields["provider"]
        if isinstance(field, forms.ModelChoiceField):
            field.queryset = ToolServiceProviderAuthorisation.objects.filter(
                service=ProviderService.CALIBRATION
            ).select_related("supplier")

    def clean_points(self) -> list[str]:
        validator = measurement_field("Test Point")
        try:
            points = {
                validator.clean(value.strip()) for value in self.cleaned_data["points"].split(",")
            }
            return [format(point, "f") for point in sorted(points)]
        except (InvalidOperation, forms.ValidationError, TypeError) as error:
            raise forms.ValidationError(
                "Give valid numerical test points separated by commas"
            ) from error

    def clean_error_limit(self) -> Decimal:
        limit = self.cleaned_data["error_limit"]
        if not isinstance(limit, Decimal) or limit <= 0:
            raise forms.ValidationError("The error limit must be greater than zero")
        return limit


class MovementForm(Form):
    request_id = submission_field()
    kind = forms.ChoiceField(label="Movement", choices=MovementKind.choices)
    occurred_on = date_field("Movement Date")
    expected_on = date_field("Expected Return", required=False)
    evidence = evidence_field("Custody Evidence")


class CertificateForm(Form):
    request_id = submission_field()
    number = forms.CharField(label="Certificate Number", max_length=100)
    revision = forms.CharField(label="Certificate Revision", max_length=80)
    source = forms.CharField(label="Certificate Evidence Reference", max_length=240)
    calibrated_on = date_field("Calibration Date")
    received_on = date_field("Certificate Receipt Date")
    serial = forms.CharField(label="Serial Number Shown", max_length=100, required=False)
    component_ids = forms.CharField(
        label="Controlled Component IDs Shown", max_length=240, required=False
    )
    facility = forms.CharField(label="Performing Facility", max_length=150, required=False)
    standard = forms.CharField(label="Recognised Standard", max_length=160, required=False)
    method = forms.CharField(label="Method and Revision", max_length=150, required=False)
    configuration = forms.CharField(
        label="Direction and Configuration", max_length=150, required=False
    )
    traceability = evidence_field("Metrological Traceability Evidence", required=False)
    rule = evidence_field("Laboratory Decision Rule and Source", required=False)
    adjustment = evidence_field("Adjustment Evidence", required=False)


class ResultForm(Form):
    request_id = submission_field()
    phase = forms.ChoiceField(label="Phase", choices=Phase.choices)
    reference_value = measurement_field("Reference Value")
    measured_value = measurement_field("Measured Value", required=False)
    error = measurement_field("Signed Error", required=False)
    uncertainty = measurement_field("Expanded Uncertainty", required=False, nonnegative=True)
    coverage = forms.CharField(
        label="Coverage Factor or Probability", max_length=100, required=False
    )
    convention = forms.CharField(label="Signed Error Convention", max_length=150, required=False)
    statement = forms.ChoiceField(label="Reported Statement", choices=Statement.choices)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if (
            cleaned.get("error") is None
            and cleaned.get("measured_value") is None
            and cleaned.get("statement")
            not in {
                Statement.FAILS,
                Statement.INCONCLUSIVE,
            }
        ):
            self.add_error(
                "measured_value", "Record the measurement, signed error or reported finding"
            )
        return cleaned


class DecisionForm(Form):
    request_id = submission_field()
    outcome = forms.ChoiceField(label="Decision", choices=DecisionOutcome.choices)
    reason = evidence_field("Decision Reason and Scope")
    internal_rule = forms.CharField(
        label="Internal Conformity Rule and Source", max_length=240, required=False
    )


class ReinstateForm(Form):
    request_id = submission_field()
    evidence = evidence_field("Reinstatement Evidence and Applicable Interim Actions")
