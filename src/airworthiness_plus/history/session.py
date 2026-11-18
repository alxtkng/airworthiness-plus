"""Tell the database which organisation and user a piece of work is for.

Row-level security shows only the rows of the organisation set on the
database session, and the history names the user set on it (REQ-003,
REQ-130). Both are set for the length of one transaction and are gone when
it ends, so nothing carries over to the next request on the same
connection.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager

from django.db import connection, transaction

from airworthiness_plus.history.sql import ORGANISATION_SETTING, USER_SETTING


def _current() -> tuple[str, str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT current_setting(%s, true), current_setting(%s, true)",
            [ORGANISATION_SETTING, USER_SETTING],
        )
        organisation, user = cursor.fetchone()
    return organisation or "", user or ""


def _set(organisation: str, user: str) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config(%s, %s, true), set_config(%s, %s, true)",
            [ORGANISATION_SETTING, organisation, USER_SETTING, user],
        )


@contextmanager
def working_for(organisation: uuid.UUID | None, user: uuid.UUID | None = None) -> Iterator[None]:
    """Do the enclosed work for ``organisation``, as ``user``.

    Opens a transaction if there is none. On leaving, the session is put
    back as it was; if the work fails, the transaction's own rollback does
    that.
    """
    with transaction.atomic():
        before = _current()
        _set(str(organisation) if organisation else "", str(user) if user else "")
        yield
        _set(*before)
