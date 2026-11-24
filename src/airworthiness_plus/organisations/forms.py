"""Forms for the Settings page. Labels follow design-system/Writing.md."""

from typing import Any

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations.configuration import MOST_CYCLES, MOST_DAYS, MOST_HOURS
from airworthiness_plus.organisations.models import ApprovalType


class DetailsForm(Form):
    """The name and address of the organisation."""

    name = forms.CharField(label="Organisation Name", max_length=200)
    address = forms.CharField(label="Address", max_length=300, required=False)


class ApprovalHeldForm(Form):
    """Record an approval the organisation holds."""

    approval = forms.ChoiceField(label="Approval", choices=ApprovalType.choices)
    reference = forms.CharField(label="Approval Reference", max_length=40)


class EndApprovalForm(Form):
    """Record that an approval is no longer held."""

    on = forms.DateField(label="No Longer Held From")


class LeadTimesForm(Form):
    """How close a limit must be to show as Due Soon (REQ-212, REQ-213)."""

    due_soon_days = forms.IntegerField(
        label="Calendar Checks and Programme Reviews, Days", min_value=0, max_value=MOST_DAYS
    )
    due_soon_hours = forms.DecimalField(
        label="Hour-Based Checks and Life Limits, Hours",
        min_value=0,
        max_value=MOST_HOURS,
        max_digits=5,
        decimal_places=1,
    )
    due_soon_cycles = forms.IntegerField(
        label="Cycle-Based Checks and Life Limits, Cycles", min_value=0, max_value=MOST_CYCLES
    )
    review_alert = forms.BooleanField(
        label="Earlier Alert for Airworthiness Review Certificates", required=False
    )
    review_alert_days = forms.IntegerField(
        label="Earlier Alert, Days Before Expiry", min_value=1, max_value=MOST_DAYS, required=False
    )

    def clean(self) -> dict[str, Any]:
        """An earlier alert has its days, and they are more than the calendar lead time."""
        data = super().clean() or {}
        if not data.get("review_alert"):
            data["review_alert_days"] = None
            return data
        alert, days = data.get("review_alert_days"), data.get("due_soon_days")
        if "review_alert_days" in self.errors:
            return data
        if alert is None:
            raise forms.ValidationError("Give the Days of the Earlier Alert")
        if days is not None and alert <= days:
            raise forms.ValidationError(
                "The Earlier Alert Is More Days Than the Calendar Lead Time"
            )
        return data


class DeferralLimitsForm(Form):
    """The organisation's default limits for a deferred defect, in days (REQ-214)."""

    deferral_days_non_required = forms.IntegerField(
        label="Pilot-in-Command, Defects on Non-Required Equipment, Days",
        min_value=1,
        max_value=MOST_DAYS,
    )
    deferral_days_with_agreement = forms.IntegerField(
        label="Pilot-in-Command, With Agreement, Other Defects, Days",
        min_value=1,
        max_value=MOST_DAYS,
    )
    deferral_days_certifying_staff = forms.IntegerField(
        label="Certifying Staff, Other Defects, Days", min_value=1, max_value=MOST_DAYS
    )
