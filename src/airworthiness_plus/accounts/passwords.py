"""Words a password may not be built on (OWASP ASVS 5.0, 6.1.2 and 6.2.11).

Django already refuses a password that is like the user's own name or
user name, and one of 20,000 common passwords.
This adds the words anyone attacking this system would try first: the
name of the product, the regulator and the approval, and the name and
approval reference of the user's own organisation.
"""

import re

from django.core.exceptions import ObjectDoesNotExist, ValidationError

WORDS = (
    "airworthiness",
    "airworthy",
    "aircraft",
    "caa",
    "civilaviation",
    "partcao",
    "partml",
    "password",
)


def _plain(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


class ContextWordsValidator:
    """Refuse a password that contains one of the words, however it is spaced or cased."""

    def validate(self, password: str, user: object = None) -> None:
        """Raise if the password contains a word of the list or of the organisation."""
        plain = _plain(password)
        words = list(WORDS)
        try:
            organisation = getattr(user, "organisation", None) if user is not None else None
        except ObjectDoesNotExist:
            # A user who is not yet saved, or is read outside their organisation.
            organisation = None
        if organisation is not None:
            words += [_plain(word) for word in str(organisation.name).split()]
            words.append(_plain(str(organisation.approval_reference)))
        for word in words:
            if (len(word) >= 4 and word in plain) or (word == "caa" and plain.startswith("caa")):
                raise ValidationError(
                    "This password contains a word that is too easy to guess.",
                    code="password_context_word",
                )

    def get_help_text(self) -> str:
        """Say what the rule is."""
        return (
            "A password does not contain the name of the product, the regulator "
            "or your organisation."
        )
