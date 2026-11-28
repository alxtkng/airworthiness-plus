"""Fields available to the tool register's writing actions."""

from typing import Any
from uuid import uuid4

from django import forms
from django.db.models import QuerySet

from airworthiness_plus.interface.forms import Form as RecordForm
from airworthiness_plus.organisations.models import ApprovalType
from airworthiness_plus.people.models import Person
from airworthiness_plus.tooling.models import (
    ControlKind,
    EventKind,
    ToolAction,
    ToolControlRevision,
)

MAINTENANCE = [(kind.value, kind.label) for kind in (ApprovalType.PART_CAO, ApprovalType.PART_145)]


def approval_field() -> forms.ChoiceField:
    return forms.ChoiceField(label="Maintenance Approval", choices=MAINTENANCE)


def submission_field() -> forms.UUIDField:
    return forms.UUIDField(label="Submission Reference", widget=forms.HiddenInput, initial=uuid4)


class RegistrationForm(RecordForm):
    approval = approval_field()
    request_id = submission_field()
    asset_id = forms.CharField(label="Asset ID", max_length=50)
    description = forms.CharField(label="Description", max_length=150)
    manufacturer = forms.CharField(label="Manufacturer", max_length=120, required=False)
    model = forms.CharField(label="Model", max_length=100, required=False)
    part_number = forms.CharField(label="Part Number", max_length=100, required=False)
    serial = forms.CharField(label="Serial Number", max_length=100, required=False)
    component_ids = forms.CharField(
        label="Component IDs and Configuration", max_length=240, required=False
    )
    is_assembly = forms.BooleanField(label="Kit with Controlled Components", required=False)
    measurement_range = forms.CharField(
        label="Range or Capacity and Units", max_length=120, required=False
    )
    owner = forms.CharField(label="Owner", max_length=150, required=False)
    lender = forms.CharField(label="Lender", max_length=150, required=False)
    site = forms.CharField(label="Site", max_length=100)
    location = forms.CharField(label="Usual Location", max_length=150)
    notes = forms.CharField(
        label="Identity or Evidence Notes", required=False, widget=forms.Textarea
    )


class DelegationForm(RecordForm):
    approval = approval_field()
    request_id = submission_field()
    person = forms.ModelChoiceField(label="Person", queryset=Person.objects.none())
    action = forms.ChoiceField(label="Delegated Action", choices=ToolAction.choices)
    site = forms.CharField(label="Site", max_length=100)
    starts_on = forms.DateField(label="First Day", widget=forms.DateInput(attrs={"type": "date"}))
    ends_on = forms.DateField(label="Last Day", widget=forms.DateInput(attrs={"type": "date"}))
    procedure = forms.CharField(label="Exposition Procedure, Revision and Clause", max_length=200)
    authority = forms.CharField(
        label="Signed Delegation Reference and Scope", widget=forms.Textarea
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.all()  # type: ignore[attr-defined]


class WithdrawalForm(RecordForm):
    evidence = forms.CharField(label="Withdrawal Evidence", widget=forms.Textarea)


class ControlForm(RecordForm):
    approval = approval_field()
    request_id = submission_field()
    kind = forms.ChoiceField(label="Control", choices=ControlKind.choices)
    interval_months = forms.IntegerField(
        label="Interval in Calendar Months", min_value=1, max_value=1200, required=False
    )
    instruction = forms.CharField(label="Instruction and Reference", max_length=200)
    instruction_revision = forms.CharField(label="Instruction Revision", max_length=80)
    method = forms.CharField(label="Method", widget=forms.Textarea)
    limits = forms.CharField(label="Acceptance Limits", widget=forms.Textarea)
    decision_basis = forms.CharField(
        label="Decision Basis and Interval Evidence", widget=forms.Textarea
    )
    scope = forms.CharField(label="Configuration, Range and Scope Covered", widget=forms.Textarea)
    standard = forms.CharField(
        label="Recognised Calibration Standard", max_length=160, required=False
    )
    loan_task = forms.CharField(
        label="Loan Tool Task and Maintenance Data Revision", max_length=240, required=False
    )
    loan_evidence = forms.CharField(
        label="Actual Loan and Receipt Evidence", max_length=240, required=False
    )
    loan_identity = forms.CharField(
        label="Serials Verified on the Actual Loan",
        max_length=350,
        required=False,
        help_text=(
            "Enter the registered asset serial and any component IDs, separated by a spaced slash."
        ),
    )


class EventForm(RecordForm):
    approval = approval_field()
    request_id = submission_field()
    control = forms.ModelChoiceField(
        label="Applicable Control Revision",
        queryset=ToolControlRevision.objects.none(),
        required=False,
        help_text="Select for completions, pre-use inspections and interim checks.",
    )
    kind = forms.ChoiceField(label="Event", choices=EventKind.choices)
    occurred_on = forms.DateField(
        label="Event Date", widget=forms.DateInput(attrs={"type": "date"})
    )
    evidence = forms.CharField(
        label="Evidence Reference and Findings",
        widget=forms.Textarea,
        help_text="For a completion, cite the evidence you verified against the selected basis.",
    )
    reference_instrument = forms.CharField(
        label="Reference Instrument for Interim Check", max_length=120, required=False
    )
    result = forms.CharField(label="Interim Check Reading", max_length=160, required=False)
    limit = forms.CharField(label="Interim Check Limit", max_length=160, required=False)

    def __init__(self, *args: Any, controls: QuerySet[ToolControlRevision], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = self.fields["control"]
        if isinstance(field, forms.ModelChoiceField):
            field.queryset = controls
