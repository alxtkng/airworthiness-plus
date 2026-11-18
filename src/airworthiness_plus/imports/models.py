"""An import of records from paper or a spreadsheet, and the check of each value (REQ-170, REQ-171).

Every value that is imported is kept beside the record it made, so that a
person can read the source again and say whether the two agree. A load,
its values and their checks are added and never changed.
"""

from django.db import models
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class LoadKind(models.TextChoices):
    """What a file holds. Each kind has its own columns."""

    AIRCRAFT = "Aircraft and Totals", "Aircraft and Totals"
    DIRECTIVES = "Airworthiness Directive Status", "Airworthiness Directive Status"
    CERTIFICATES = "Airworthiness Review Certificates", "Airworthiness Review Certificates"


class Load(Record):
    """One file imported: what it was, where it came from, who loaded it and when."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    kind = models.CharField(max_length=40, choices=LoadKind.choices)
    source = models.CharField("Source Records", max_length=300)
    file_name = models.CharField(max_length=200)
    file_sha256 = models.CharField(max_length=64)
    rows = models.PositiveIntegerField()
    loaded_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    loaded_on = models.DateField("Loaded")

    class Meta:
        ordering = ["-loaded_on", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(source=""), name="load_names_its_source"),
            models.CheckConstraint(
                condition=Q(kind__in=LoadKind.values), name="load_kind_is_known"
            ),
        ]


class LoadedValue(Record):
    """One value as it was imported: which row, what it is of, which column."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    load = models.ForeignKey(Load, on_delete=models.PROTECT, related_name="values")
    row = models.PositiveIntegerField()
    position = models.PositiveIntegerField()
    subject = models.CharField(max_length=200)
    field = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        ordering = ["row", "position"]
        constraints = [
            models.UniqueConstraint(
                fields=["load", "row", "position"], name="loadedvalue_one_for_each_cell"
            ),
        ]


class ValueCheck(Record):
    """One check of an imported value against its source, by a person, on a day."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    value = models.ForeignKey(LoadedValue, on_delete=models.PROTECT, related_name="checks")
    source_value = models.TextField()
    agrees = models.BooleanField()
    checked_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    checked_on = models.DateField("Checked")
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["value", "position"], name="valuecheck_one_at_each_position"
            ),
        ]
