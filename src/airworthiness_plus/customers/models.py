"""A record for each owner or operator (REQ-207).

Decisions.md, Canvas Build, decision 3: each owner or operator is a
customer record, as the Customers board shows, in place of the free text
Owned By on each aircraft.
"""

from django.db import models
from django.db.models import Q

from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class Kind(models.TextChoices):
    """What kind of owner a customer is (Writing.md, People and Roles; decision 3)."""

    PILOT_OWNER = "Pilot-Owner", "Pilot-Owner"
    SYNDICATE = "Syndicate", "Syndicate"
    FLYING_CLUB = "Flying Club", "Flying Club"
    OPERATOR = "Operator", "Operator"


class Customer(Record):
    """One owner or operator the organisation works for.

    A customer made from what was typed as Owned By before customers were
    records has that text as its name and no kind (REQ-209).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    name = models.CharField("Customer", max_length=200)
    kind = models.CharField("Kind", max_length=20, choices=Kind.choices, blank=True)
    members = models.PositiveSmallIntegerField("Members of the Syndicate", null=True, blank=True)
    customer_since = models.DateField("Customer Since", null=True, blank=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(name="") & Q(kind__in=["", *Kind.values]),
                name="customer_has_a_name_and_a_known_kind",
            ),
            models.CheckConstraint(
                condition=Q(members__isnull=True) | Q(kind=Kind.SYNDICATE, members__gte=1),
                name="customer_members_are_of_a_syndicate",
            ),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def description(self) -> str:
        """Return the kind as the Customers board writes it: Syndicate of 6."""
        if self.kind == Kind.SYNDICATE and self.members is not None:
            return f"Syndicate of {self.members}"
        return str(self.kind)

    @property
    def owned_by(self) -> str:
        """Return what Owned By shows: the kind of owner, or the name where no kind is recorded."""
        return self.description or self.name
