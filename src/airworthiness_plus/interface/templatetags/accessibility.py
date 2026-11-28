"""The error summary at the top of a form (REQ-397; WCAG 2.2 SC 3.3.1, 3.3.3).

The summary follows the GOV.UK pattern: a heading, then one link for each
field with an error, which moves focus to that field. The field's own message
sits beside it with the identifier Django names in the field's
``aria-describedby``, so a screen reader reads the message with the field.
Errors that belong to no one field stay where each form already says them.

The tag is a builtin of the templates (settings.TEMPLATES), so a form page
writes ``{% error_summary form %}`` with nothing to load.
"""

from typing import Any

from django import forms, template

register = template.Library()


@register.inclusion_tag("interface/error_summary.html")
def error_summary(form: Any) -> dict[str, object]:
    """Give the summary every field of ``form`` that has an error, in the form's order."""
    if not isinstance(form, forms.BaseForm) or not form.is_bound or not form.errors:
        return {"items": [], "title": ""}
    items = []
    for field in form:
        if field.errors and not field.is_hidden:
            items.append(
                {
                    "target": field.id_for_label or field.auto_id,
                    "label": field.label,
                    "messages": ", ".join(str(message) for message in field.errors),
                }
            )
    return {"items": items, "title": f"error-summary-{form.prefix or 'form'}"}
