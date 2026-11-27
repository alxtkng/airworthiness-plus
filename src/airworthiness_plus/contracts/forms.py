"""Forms for contracts and work orders. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.contracts.models import EndReason, OrderedBy, Outcome, Scope
from airworthiness_plus.interface.forms import Form
from airworthiness_plus.programme.models import WorkDone


class ContractForm(Form):
    """Record a contract signed with the owner of an aircraft (Appendix I to Part-ML)."""

    aircraft = forms.ModelChoiceField(
        label="Aircraft Registration", queryset=Aircraft.objects.none()
    )
    scope = forms.ChoiceField(label="Tasks Contracted", choices=Scope.choices)
    tasks = forms.CharField(label="Limited Tasks", max_length=200, required=False)
    type_of_operation = forms.CharField(label="Type of Operation", max_length=100)
    owner_address = forms.CharField(
        label="Owner\N{RIGHT SINGLE QUOTATION MARK}s Address", max_length=300
    )
    signed_on = forms.DateField(label="Signed")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]


class EndContractForm(Form):
    """Record that a contract has ended."""

    ended_on = forms.DateField(label="Ended")
    end_reason = forms.ChoiceField(label="Reason", choices=EndReason.choices)


class AuthorityToldForm(Form):
    """Record the day the organisation told the Civil Aviation Authority."""

    told_on = forms.DateField(label="Civil Aviation Authority Told")


class WorkOrderForm(Form):
    """Record a written request for maintenance."""

    aircraft = forms.ModelChoiceField(
        label="Aircraft Registration", queryset=Aircraft.objects.none()
    )
    work = forms.CharField(label="Work Ordered", max_length=200)
    ordered_by = forms.ChoiceField(label="Ordered By", choices=OrderedBy.choices)
    agreed_on = forms.DateField(label="Agreed")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["aircraft"].queryset = Aircraft.objects.all()  # type: ignore[attr-defined]


class CloseWorkOrderForm(Form):
    """Record that a work order is completed or withdrawn."""

    closed_on = forms.DateField(label="Closed")
    outcome = forms.ChoiceField(label="Outcome", choices=Outcome.choices)
    work_done = forms.ModelChoiceField(
        label="Work Done", queryset=WorkDone.objects.none(), required=False, empty_label="None"
    )

    def __init__(self, *args: Any, aircraft: Aircraft | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if aircraft is not None:
            self.fields["work_done"].queryset = WorkDone.objects.filter(  # type: ignore[attr-defined]
                aircraft=aircraft
            )
