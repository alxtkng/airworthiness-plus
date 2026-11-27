"""Roster forms, with time entered in the United Kingdom."""

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.people.models import Person
from airworthiness_plus.planning.models import WorkPackage
from airworthiness_plus.staffing.forms import ApprovalChoice
from airworthiness_plus.staffing.models import Function

LOCAL_TIME = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")


class ShiftForm(Form):
    approval = ApprovalChoice(label="Approval", queryset=Approval.objects.all())
    person = forms.ModelChoiceField(label="Person", queryset=Person.objects.all())
    area = forms.CharField(label="Area", max_length=100)
    shift_name = forms.CharField(label="Shift", max_length=100)
    starts_at = forms.DateTimeField(label="Starts", widget=LOCAL_TIME)
    ends_at = forms.DateTimeField(label="Ends", widget=LOCAL_TIME)
    break_minutes = forms.IntegerField(label="Break in Minutes", min_value=0, max_value=1439)
    other_minutes = forms.IntegerField(
        label="Other Work in Minutes That Day", min_value=0, max_value=1440, initial=0
    )
    maintenance = forms.BooleanField(label="Performs Maintenance", required=False)
    critical_at = forms.DateTimeField(label="Critical Task Time", widget=LOCAL_TIME, required=False)
    mitigation = forms.CharField(
        label="Risk Assessment or Mitigation", max_length=400, required=False
    )
    permission = forms.CharField(
        label="Civil Aviation Authority Permission Reference", max_length=200, required=False
    )


class PublicationForm(Form):
    week = forms.DateField(label="Week Beginning")
    note = forms.CharField(label="Changes and Agreement", max_length=400, widget=forms.Textarea)


class WithdrawShiftForm(Form):
    reason = forms.CharField(label="Reason Withdrawn", max_length=300)


class HandoverForm(Form):
    package = forms.ModelChoiceField(
        label="Work Package", queryset=WorkPackage.objects.all(), required=False
    )
    outgoing = forms.ModelChoiceField(label="Handed Over By", queryset=Person.objects.all())
    incoming = forms.ModelChoiceField(label="Handed Over To", queryset=Person.objects.all())
    handed_at = forms.DateTimeField(label="Handed Over", widget=LOCAL_TIME)
    stage = forms.CharField(
        label="Stage Reached and Open Tasks", max_length=500, widget=forms.Textarea
    )
    parts = forms.CharField(
        label="Parts, Tools and Warnings", max_length=500, widget=forms.Textarea
    )


class SettingsForm(Form):
    annual_leave_days = forms.IntegerField(
        label="Annual Leave Allowance in Days", min_value=0, max_value=366
    )
    load_margin_percent = forms.IntegerField(
        label="Load Warning Percentage", min_value=1, max_value=100
    )
    other_hours_weekly = forms.DecimalField(
        label="Other Hours per Week", max_digits=6, decimal_places=1, min_value=0
    )
    maximum_shift_minutes = forms.IntegerField(
        label="Longest Shift in Minutes", min_value=1, max_value=1440
    )
    minimum_rest_minutes = forms.IntegerField(
        label="Minimum Rest in Minutes", min_value=0, max_value=10080
    )
    maximum_week_minutes = forms.IntegerField(
        label="Weekly Limit in Minutes", min_value=1, max_value=10080
    )
    critical_first_half = forms.BooleanField(
        label="Critical Tasks in the First Half of a Shift", required=False
    )
    publish_days = forms.IntegerField(
        label="Publish This Many Days Ahead", min_value=0, max_value=365
    )
    overlap_minutes = forms.IntegerField(
        label="Handover Overlap in Minutes", min_value=0, max_value=1440
    )
    standard_break_minutes = forms.IntegerField(
        label="Standard Break in Minutes", min_value=0, max_value=1439
    )


class BankHolidayForm(Form):
    on = forms.DateField(label="Date")
    name = forms.CharField(label="Bank Holiday", max_length=120)


class ShiftPatternForm(Form):
    name = forms.CharField(label="Shift Pattern", max_length=100)
    area = forms.CharField(label="Area", max_length=100)
    days = forms.CharField(label="Days", max_length=120)
    starts_at = forms.TimeField(label="Starts")
    ends_at = forms.TimeField(label="Ends")
    break_minutes = forms.IntegerField(label="Break in Minutes", min_value=0, max_value=1439)

    def clean(self) -> dict[str, object]:
        values = super().clean() or {}
        start = self.cleaned_data.get("starts_at")
        end = self.cleaned_data.get("ends_at")
        pause = self.cleaned_data.get("break_minutes")
        if start is not None and end is not None and pause is not None:
            elapsed = (60 * (end.hour - start.hour) + end.minute - start.minute) % 1440
            if not 0 <= pause < elapsed:
                self.add_error("break_minutes", "The Break Must Be Shorter Than the Shift")
        return values


class StaffingMinimumForm(Form):
    approval = ApprovalChoice(label="Approval", queryset=Approval.objects.all())
    function = forms.ChoiceField(label="Function", choices=Function.choices)
    minimum = forms.IntegerField(label="Minimum", min_value=0, max_value=32767)
    normal = forms.IntegerField(label="Normal", min_value=0, max_value=32767)
    applies_on = forms.CharField(label="Applies On", max_length=200)

    def clean_normal(self) -> int:
        normal: int = self.cleaned_data["normal"]
        minimum = self.cleaned_data.get("minimum")
        if minimum is not None and normal < minimum:
            raise forms.ValidationError("The Normal Number Is at Least the Minimum")
        return normal
