"""What of the sample has been added to an organisation (REQ-218).

The test site brings a sample seeded earlier up to date each time it
starts. What it adds, it adds once: this record says that it has, so that
a later start adds nothing again, whatever has been renamed or changed
since (independent review of 24 November 2026, finding 3).
"""

from django.db import models

from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class Part(models.TextChoices):
    """A part of the sample that is added once."""

    PEOPLE = "People", "People"
    # Phase 1 of the canvas build (REQ-294): each part of its sample, added once.
    DEFECTS = "Defects", "Defects"
    CONTRACTS = "Contracts", "Contracts"
    COMPONENTS = "Components", "Components"
    MODIFICATIONS = "Modifications and Weighings", "Modifications and Weighings"
    PROGRAMME = "Departures and Annual Review", "Departures and Annual Review"
    SOURCES = "Sources of Directives", "Sources of Directives"
    SET_UP = "Transfer and Configuration", "Transfer and Configuration"


class Added(Record):
    """That one part of the sample has been added to one organisation. Never changed."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    part = models.CharField("Part of the Sample", max_length=40, choices=Part.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["organisation", "part"], name="sample_part_added_once"),
            models.CheckConstraint(
                condition=models.Q(part__in=Part.values), name="sample_part_is_known"
            ),
        ]

    def __str__(self) -> str:
        return self.part
