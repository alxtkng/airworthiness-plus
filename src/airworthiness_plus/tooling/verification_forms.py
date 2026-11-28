"""Fields for physical clearance and tool reconciliation on release forms."""

from typing import Any

from django import forms

from airworthiness_plus.tooling.calibration_forms import date_field, evidence_field
from airworthiness_plus.tooling.forms import MAINTENANCE
from airworthiness_plus.tooling.release_evidence import Verification


class GeneralVerificationForm(forms.Form):
    approval = forms.ChoiceField(
        label="Governing Maintenance Approval", choices=[("", "—"), *MAINTENANCE], required=False
    )
    performed_on = date_field("Physical General Verification Date", required=False)
    cleared = forms.BooleanField(
        label=(
            "After Maintenance, Verified Clear of Tools, Equipment, Extraneous Parts and Material"
        ),
        required=False,
    )
    panels = forms.ChoiceField(
        label="Physical Access Panel Findings",
        choices=[
            ("", "—"),
            ("All refitted", "All Removed Panels Refitted"),
            ("None removed", "No Panels Removed"),
        ],
        required=False,
    )
    signed_evidence = forms.CharField(
        label="Signed Physical General Verification Evidence", max_length=240, required=False
    )
    accountability = evidence_field("Tool Accountability Evidence", required=False)


def take_verification(values: dict[str, Any]) -> Verification:
    fields = ("approval", "performed_on", "cleared", "panels", "signed_evidence", "accountability")
    return Verification(**{key: values.pop(key) for key in fields})
