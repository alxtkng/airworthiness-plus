"""Forms for timing dispatch work and windows."""

from django import forms

from airworthiness_plus.interface.forms import Form
from airworthiness_plus.planning.models import WorkCard, WorkPackage
from airworthiness_plus.staffing.dispatch import shift_label
from airworthiness_plus.staffing.roster_forms import LOCAL_TIME
from airworthiness_plus.staffing.roster_models import Shift


class ShiftChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: Shift) -> str:
        return shift_label(obj)


class CardChoice(forms.ModelChoiceField):  # type: ignore[type-arg]
    def label_from_instance(self, obj: WorkCard) -> str:
        return f"{obj.package} · {obj.title}"


class TimedForm(forms.Form):
    starts_at = forms.DateTimeField(label="Starts", widget=LOCAL_TIME)
    ends_at = forms.DateTimeField(label="Ends", widget=LOCAL_TIME)


class MoveAssignmentForm(TimedForm, Form):
    field_order = ["shift", "starts_at", "ends_at", "reason"]

    shift = ShiftChoice(
        label="Maintenance Shift",
        queryset=Shift.objects.filter(maintenance=True, withdrawn_on__isnull=True).select_related(
            "person"
        ),
    )
    reason = forms.CharField(label="Planning or Change Reason", max_length=300)


class AssignmentForm(MoveAssignmentForm):
    field_order = ["card", "shift", "starts_at", "ends_at", "reason"]

    card = CardChoice(label="Work Card", queryset=WorkCard.objects.select_related("package"))


class BreakForm(TimedForm, Form):
    field_order = ["shift", "starts_at", "ends_at", "note"]

    shift = ShiftChoice(
        label="Roster Shift",
        queryset=Shift.objects.filter(withdrawn_on__isnull=True).select_related("person"),
    )
    note = forms.CharField(label="Window Note", max_length=300)


class TurnaroundForm(TimedForm, Form):
    field_order = ["package", "starts_at", "ends_at", "note"]

    package = forms.ModelChoiceField(label="Work Package", queryset=WorkPackage.objects.all())
    note = forms.CharField(label="Window Note", max_length=300)
