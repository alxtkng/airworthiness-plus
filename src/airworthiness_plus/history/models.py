"""The base for every record, and the history of changes to records."""

import uuid
from typing import Any, NoReturn

from django.contrib.postgres.fields import ArrayField
from django.db import models

# SHA-256 over twelve fields, each written as its length, a colon, the value
# and a comma. Described in ``airworthiness_plus.history.chain``.
HASH_ALGORITHM = "sha256-fields-1"


class RecordsAreNeverDeletedError(Exception):
    """Nothing is deleted. A wrong or outdated entry is superseded (REQ-131)."""


class RecordQuerySet[RecordType: models.Model](models.QuerySet[RecordType]):
    """A queryset with no delete operation (REQ-131)."""

    def delete(self) -> NoReturn:
        """Refuse. The database refuses too, whoever asks."""
        raise RecordsAreNeverDeletedError("Records are never deleted")


class Record(models.Model):
    """A record: identified by a value that cannot be guessed, and never deleted.

    The identifier is random, so knowing one record's address says nothing
    about another's (threat TH-006).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    objects = RecordQuerySet.as_manager()

    class Meta:
        abstract = True

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Refuse. The database refuses too, whoever asks."""
        raise RecordsAreNeverDeletedError("Records are never deleted")


class Event(models.Model):
    """One entry in the history of a record (REQ-130).

    Written only by the database, when a record is created or changed. It
    holds who made the change, when, what changed, and the record before
    and after. ``hash`` covers every field and the hash of the entry before
    it for the same record, so an altered or missing entry can be detected
    (threats TH-021, TH-025).
    """

    organisation = models.ForeignKey(
        "organisations.Organisation", on_delete=models.PROTECT, related_name="+"
    )
    record_type = models.CharField(max_length=63)
    record_id = models.UUIDField()
    sequence = models.PositiveIntegerField()
    action = models.CharField(max_length=20)
    actor = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, null=True, related_name="+"
    )
    actor_name = models.CharField(max_length=200)
    at = models.DateTimeField()
    changed = ArrayField(models.CharField(max_length=63), default=list)
    before_json = models.TextField(null=True)
    after_json = models.TextField(null=True)
    previous_hash = models.CharField(max_length=64, blank=True)
    hash = models.CharField(max_length=64)
    # How ``hash`` was made, so that the method can be changed one day without
    # leaving earlier entries unreadable (OWASP ASVS 5.0, 11.2.2). The default
    # is set by the database, which writes every entry.
    hash_algorithm = models.CharField(max_length=40, db_default=HASH_ALGORITHM)

    objects = RecordQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "record_type", "record_id", "sequence"],
                name="history_event_one_entry_for_each_sequence",
            ),
        ]
        ordering = ["record_type", "record_id", "sequence"]

    def save(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Refuse. History is written by the database, not the application."""
        raise RecordsAreNeverDeletedError("History is written only by a change to a record")

    def delete(self, *args: Any, **kwargs: Any) -> NoReturn:
        """Refuse. The database refuses too, whoever asks."""
        raise RecordsAreNeverDeletedError("History is never deleted")

    @classmethod
    def of(cls, record: Record) -> models.QuerySet["Event"]:
        """Return the history of ``record``, oldest entry first."""
        return cls._default_manager.filter(
            record_type=record._meta.db_table, record_id=record.pk
        ).order_by("sequence")
