"""Forms for customer records. Labels follow design-system/Writing.md."""

from django import forms

from airworthiness_plus.customers.models import Kind
from airworthiness_plus.interface.forms import Form


class CustomerForm(Form):
    """Add a customer, or change what is recorded of one."""

    name = forms.CharField(label="Customer", max_length=200)
    kind = forms.ChoiceField(
        label="Kind", choices=[("", "Not Recorded"), *Kind.choices], required=False
    )
    members = forms.IntegerField(
        label="Members of the Syndicate", min_value=1, max_value=32767, required=False
    )
    customer_since = forms.DateField(label="Customer Since", required=False)
