"""Forms for the import of records."""

from django import forms

from airworthiness_plus.imports.models import LoadKind
from airworthiness_plus.interface.forms import Form


class LoadForm(Form):
    """Choose what the file holds, say where it came from, and give the file."""

    kind = forms.ChoiceField(
        label="What the File Holds", choices=[("", "Choose"), *LoadKind.choices]
    )
    source = forms.CharField(label="Source Records", max_length=300)
    file = forms.FileField(label="File")
