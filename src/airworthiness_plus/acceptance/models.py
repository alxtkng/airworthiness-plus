"""The problem log (REQ-172).

An entry and its notes are added and never changed or removed: the
application has no permission to change them, and the history would show
it if anyone else did.
"""

from django.db import models
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class Problem(Record):
    """One problem with the system or its records, as it was raised."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    problem = models.TextField("Problem")
    raised_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    raised_on = models.DateField("Raised")

    class Meta:
        ordering = ["-raised_on", "-id"]
        constraints = [
            models.CheckConstraint(condition=~Q(problem=""), name="problem_is_described"),
        ]


class NoteKind(models.TextChoices):
    """What a note adds to an entry."""

    ACTION = "Action", "Action"
    SOLUTION = "Solution", "Solution"
    NOTE = "Note", "Note"


class ProblemNote(Record):
    """Something added to an entry later: the action taken, the solution, or a note."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    problem = models.ForeignKey(Problem, on_delete=models.PROTECT, related_name="notes")
    kind = models.CharField(max_length=20, choices=NoteKind.choices)
    text = models.TextField()
    noted_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    noted_on = models.DateField("Added")
    position = models.PositiveIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.CheckConstraint(condition=~Q(text=""), name="problemnote_says_something"),
            models.CheckConstraint(
                condition=Q(kind__in=NoteKind.values), name="problemnote_kind_is_known"
            ),
            models.UniqueConstraint(
                fields=["problem", "position"], name="problemnote_one_at_each_position"
            ),
        ]
