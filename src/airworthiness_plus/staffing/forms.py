"""Forms for the staffing plan, reviews and absences."""

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.organisations.models import Approval
from airworthiness_plus.people.models import Person
from airworthiness_plus.staffing.models import AbsenceType, Function


class ApprovalChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Approval) -> str:
        return f"{obj.approval}, {obj.reference}"


class DemandForm(Form):
    approval = ApprovalChoice(label="Approval", queryset=Approval.objects.all())
    month = forms.DateField(label="Month Beginning")
    function = forms.ChoiceField(label="Function", choices=Function.choices)
    needed = forms.DecimalField(label="Hours Needed", max_digits=7, decimal_places=1, min_value=0)
    employed = forms.DecimalField(
        label="Employed Hours", max_digits=7, decimal_places=1, min_value=0
    )
    contracted = forms.DecimalField(
        label="Contracted Hours", max_digits=7, decimal_places=1, min_value=0
    )
    basis = forms.CharField(
        label="Work and Availability Basis", widget=forms.Textarea, max_length=400
    )


class ReviewForm(Form):
    approval = ApprovalChoice(label="Approval", queryset=Approval.objects.all())
    reviewed_on = forms.DateField(label="Reviewed")
    outcome = forms.CharField(label="Review Outcome", widget=forms.Textarea, max_length=400)


class ReportForm(Form):
    reported_on = forms.DateField(label="Reported")
    reported_to = forms.CharField(label="Reported To", max_length=200)
    action = forms.CharField(label="Action Taken", widget=forms.Textarea, max_length=400)


class AbsenceForm(Form):
    person = forms.ModelChoiceField(label="Person", queryset=Person.objects.all())
    kind = forms.ChoiceField(label="Absence", choices=AbsenceType.choices)
    starts_on = forms.DateField(label="From")
    ends_on = forms.DateField(label="To")
