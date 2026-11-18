"""Airworthiness directives, the decision for each aircraft, and compliance.

Hazard H-002: a directive wrongly marked not applicable. There is no
default. Until a decision is recorded for an aircraft, the directive shows
as Applicability to Assess.
"""

from django.db import models
from django.db.models import Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme.models import Task, WorkDone


class Directive(Record):
    """One airworthiness directive (REQ-060).

    A directive that has been superseded stays in the record, marked with
    the directive that replaced it (REQ-068).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    number = models.CharField("Directive Number", max_length=60)
    authority = models.CharField("Issuing Authority", max_length=100)
    subject = models.CharField("Subject", max_length=200)
    effective_date = models.DateField("Effective Date")
    revision = models.CharField("Revision", max_length=40, blank=True)
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )

    class Meta:
        ordering = ["number", "revision"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "number", "revision"],
                name="directive_one_record_for_each_number_and_revision",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.number} {self.revision}".strip()


class Decision(models.TextChoices):
    """Whether a directive applies to an aircraft. There is no third value and no default."""

    APPLICABLE = "Applicable", "Applicable"
    NOT_APPLICABLE = "Not Applicable", "Not Applicable"


class Applicability(Record):
    """The decision for one directive and one aircraft (REQ-061 to REQ-063).

    The decision carries its basis, the person and the date. Changing it
    changes this record, and the history keeps what it was, who changed it
    and when. An action with a time limit, once or repeating, is a task of
    the aircraft's programme, as ML.A.302(c)(4) requires, and is calculated
    by the same rules with no tolerance (REQ-065).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    directive = models.ForeignKey(Directive, on_delete=models.PROTECT, related_name="decisions")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="+")
    decision = models.CharField("Applicability", max_length=20, choices=Decision.choices)
    basis = models.CharField("Basis", max_length=300)
    decided_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    decided_on = models.DateField("Decided")
    task = models.OneToOneField(
        Task, on_delete=models.PROTECT, null=True, blank=True, related_name="directive_decision"
    )
    terminating_action = models.CharField("Terminating Action", max_length=200, blank=True)
    terminated_on = models.DateField("Terminated", null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["directive", "aircraft"],
                name="applicability_one_decision_for_each_aircraft",
            ),
            models.CheckConstraint(
                condition=Q(decision__in=Decision.values) & ~Q(basis=""),
                name="applicability_is_a_known_decision_with_a_basis",
            ),
            models.CheckConstraint(
                condition=Q(decision=Decision.APPLICABLE) | Q(task__isnull=True),
                name="applicability_only_an_applicable_directive_has_an_action",
            ),
            models.CheckConstraint(
                condition=Q(terminating_action="", terminated_on__isnull=True)
                | (~Q(terminating_action="") & Q(terminated_on__isnull=False)),
                name="applicability_termination_has_an_action_and_a_date",
            ),
        ]


class Compliance(Record):
    """Compliance with a directive on an aircraft (REQ-064).

    The work itself, with its method, date, hours, cycles and release to
    service reference, is a record of work done. This ties it to the
    decision. Earlier compliance is never erased, by a terminating action
    or anything else (REQ-066).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    applicability = models.ForeignKey(
        Applicability, on_delete=models.PROTECT, related_name="compliance"
    )
    work = models.OneToOneField(WorkDone, on_delete=models.PROTECT, related_name="+")
