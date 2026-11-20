"""The base for every form.

A label is written with nothing after it: Django puts a colon after each
label, and Writing.md keeps the colon for definitions, so it is left out.

Every whole number has an upper limit, so that a number too large for the
database is refused on the form, with the reason, and never reaches the
database as a server error (independent review of 20 November 2026,
finding 7). A field may set a lower limit of its own.
"""

from typing import Any

from django import forms
from django.core.validators import MaxValueValidator
from django.forms.forms import DeclarativeFieldsMetaclass

# The largest whole number a PostgreSQL integer column holds.
LARGEST_WHOLE_NUMBER = 2_147_483_647


def _limit_whole_numbers(fields: dict[str, forms.Field]) -> None:
    for field in fields.values():
        if type(field) is not forms.IntegerField:
            continue
        if field.max_value is None or field.max_value > LARGEST_WHOLE_NUMBER:
            field.max_value = LARGEST_WHOLE_NUMBER
            field.validators.append(MaxValueValidator(LARGEST_WHOLE_NUMBER))
            field.widget.attrs["max"] = LARGEST_WHOLE_NUMBER


class _LimitedFields(DeclarativeFieldsMetaclass):
    """Gives each form's whole numbers their limit once the form's fields are known."""

    def __new__(mcs, name: str, bases: tuple[type, ...], attrs: dict[str, Any]) -> Any:
        new_class = super().__new__(mcs, name, bases, attrs)
        _limit_whole_numbers(getattr(new_class, "base_fields", {}))
        return new_class


class Form(forms.Form, metaclass=_LimitedFields):
    """A form whose labels end where their words end, and whose numbers have a limit."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
