"""Forms for the problem log and the organisation's acceptance records."""

from django import forms

from airworthiness_plus.acceptance.models import NoteKind
from airworthiness_plus.interface.forms import Form


class ProblemForm(Form):
    """Add an entry to the problem log."""

    problem = forms.CharField(label="Problem", widget=forms.Textarea, max_length=2000)


class NoteForm(Form):
    """Add the action, the solution or a note to an entry."""

    kind = forms.ChoiceField(label="Add", choices=[("", "Choose"), *NoteKind.choices])
    text = forms.CharField(label="What Was Done or Found", widget=forms.Textarea, max_length=2000)


class ApprovalForm(Form):
    """Record the written approval to keep records in the system."""

    reference = forms.CharField(label="Approval Reference", max_length=100)
    dated = forms.DateField(label="Approval Dated")


class ParallelRunForm(Form):
    """Record the day the parallel run began."""

    started_on = forms.DateField(label="Parallel Run Started")
