"""The base for every form: a label is written with nothing after it.

Django puts a colon after each label. Writing.md keeps the colon for
definitions, so it is left out.
"""

from typing import Any

from django import forms


class Form(forms.Form):
    """A form whose labels end where their words end."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)
