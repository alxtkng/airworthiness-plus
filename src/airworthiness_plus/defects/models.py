"""Defects of an aircraft, and the action taken on a repeat defect (REQ-220 to REQ-229)."""

from typing import Any

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person
from airworthiness_plus.programme.models import WorkDone
from airworthiness_rules.defects import FIRST_CHAPTER, LAST_CHAPTER, MOST_DAYS


class Decision(models.TextChoices):
    """What was decided of a defect, ML.A.403(a) and (b)."""

    NOT_DEFERRABLE = "Not Deferrable", "Not Deferrable"
    DEFERRED = "Deferred", "Deferred"


class Basis(models.TextChoices):
    """Who deferred the defect, and under which point of ML.A.403(b)."""

    PILOT_NON_REQUIRED = "Pilot-in-Command", "Pilot-in-Command"
    PILOT_LIST = (
        "Pilot-in-Command, Minimum Equipment List",
        "Pilot-in-Command, Minimum Equipment List",
    )
    PILOT_WITH_AGREEMENT = "Pilot-in-Command, With Agreement", "Pilot-in-Command, With Agreement"
    CERTIFYING_STAFF = "Certifying Staff", "Certifying Staff"


# The point of ML.A.403(b) each basis is, as the Settings page gives them (REQ-214).
POINTS = {
    Basis.PILOT_NON_REQUIRED: "ML.A.403(b)(1)",
    Basis.PILOT_LIST: "ML.A.403(b)(2)",
    Basis.PILOT_WITH_AGREEMENT: "ML.A.403(b)(3)",
    Basis.CERTIFYING_STAFF: "ML.A.403(b)(4)",
}


class Defect(Record):
    """One defect of one aircraft (REQ-220).

    The decision is recorded with the defect and is never altered: who
    decided, their licence as it then stood, the day and the limit. The
    database writes the name and the licence itself and refuses any later
    change to them. Closing the defect adds the rectification; after that
    nothing of it changes.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="defects")
    title = models.CharField("Defect", max_length=200)
    note = models.CharField("Note", max_length=200, blank=True)
    found_on = models.DateField("Found")
    chapter = models.PositiveSmallIntegerField("Chapter")
    section = models.CharField("ATA Section", max_length=2, blank=True)
    system = models.CharField("System", max_length=100)

    decision = models.CharField("Decision", max_length=20, choices=Decision.choices)
    basis = models.CharField("Deferred By", max_length=60, choices=Basis.choices, blank=True)
    decided_on = models.DateField("Decided")
    decided_by = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    maintenance_authorisation = models.ForeignKey(
        MaintenanceAuthorisation, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    scope_confirmed = models.BooleanField(default=False)
    legacy_evidence = models.CharField(
        "Signed Legacy Evidence Reference", max_length=160, blank=True
    )
    # As they stood on the day the defect was recorded, written by the database.
    decided_by_name = models.CharField(max_length=200, blank=True)
    decided_by_licence = models.CharField(max_length=100, blank=True)
    # The organisation's default for the decision, as it stood (REQ-214).
    default_days = models.PositiveSmallIntegerField(null=True, blank=True)
    # A limit specified in the maintenance data or the minimum equipment list.
    default_started_on = models.DateField(null=True, editable=False)
    data_limit_on = models.DateField("Limit in the Maintenance Data", null=True, blank=True)
    limit_on = models.DateField("Limit", null=True, blank=True)

    rectification = models.CharField("Rectification", max_length=200, blank=True)
    closed_on = models.DateField("Closed", null=True, blank=True)
    work_done = models.ForeignKey(
        WorkDone, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )

    class Meta:
        ordering = ["found_on", "title", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(title="")
                & ~Q(system="")
                & Q(chapter__gte=FIRST_CHAPTER, chapter__lte=LAST_CHAPTER)
                & Q(decided_on__gte=F("found_on")),
                name="defect_has_a_title_a_system_and_a_decision_not_before_it_was_found",
            ),
            models.CheckConstraint(
                condition=Q(section="") | Q(section__regex=r"^[0-9]{2}$"),
                name="defect_ata_section_is_two_digits_or_blank",
            ),
            # Not Deferrable has no basis and no limit; Deferred has both.
            models.CheckConstraint(
                condition=Q(
                    decision=Decision.NOT_DEFERRABLE,
                    basis="",
                    default_days__isnull=True,
                    data_limit_on__isnull=True,
                    limit_on__isnull=True,
                )
                | Q(
                    decision=Decision.DEFERRED,
                    basis__in=Basis.values,
                    limit_on__isnull=False,
                    limit_on__gte=F("found_on"),
                ),
                name="defect_deferred_has_a_basis_and_a_limit",
            ),
            models.CheckConstraint(
                condition=Q(default_days__isnull=True)
                | Q(default_days__gte=1, default_days__lte=MOST_DAYS),
                name="defect_default_limit_from_1_to_365_days",
            ),
            # The list gives its own limit; every other deferral has the organisation's default.
            models.CheckConstraint(
                condition=~Q(decision=Decision.DEFERRED)
                | Q(basis=Basis.PILOT_LIST, default_days__isnull=True, data_limit_on__isnull=False)
                | (~Q(basis=Basis.PILOT_LIST) & Q(default_days__isnull=False)),
                name="defect_limit_comes_from_the_list_or_the_default",
            ),
            # Certifying staff are named; a pilot is not a person of the organisation.
            models.CheckConstraint(
                condition=Q(basis=Basis.CERTIFYING_STAFF, decided_by__isnull=False)
                | Q(basis="")
                | Q(
                    basis__in=[
                        Basis.PILOT_NON_REQUIRED,
                        Basis.PILOT_LIST,
                        Basis.PILOT_WITH_AGREEMENT,
                    ],
                    decided_by__isnull=True,
                ),
                name="defect_certifying_staff_are_named_and_a_pilot_is_not",
            ),
            models.CheckConstraint(
                condition=Q(closed_on__isnull=True, rectification="", work_done__isnull=True)
                | (Q(closed_on__isnull=False, closed_on__gte=F("found_on")) & ~Q(rectification="")),
                name="defect_closed_has_a_rectification_and_a_day",
            ),
        ]

    def __str__(self) -> str:
        return self.title

    @property
    def open(self) -> bool:
        """Return whether the defect is still to be rectified."""
        return self.closed_on is None

    @property
    def decided_by_text(self) -> str:
        """Return who decided, as recorded: Sam Patel, Part-66 B1.2, or Pilot-in-Command."""
        if self.decided_by_name:
            return ", ".join(
                part for part in (self.decided_by_name, self.decided_by_licence) if part
            )
        return self.basis if self.basis else "Not Recorded"

    @property
    def point(self) -> str:
        """Return the point of ML.A.403 the decision was made under."""
        if self.decision == Decision.NOT_DEFERRABLE:
            return "ML.A.403(a)"
        return POINTS[Basis(self.basis)]

    @property
    def system_text(self) -> str:
        """Return the system as the Repeat Defects board writes it: Chapter 33, Lights."""
        classification = f"{self.chapter:02d}-{self.section}" if self.section else str(self.chapter)
        return f"Chapter {classification}, {self.system}"


class RepeatAction(Record):
    """What was done about the same defect on one type (REQ-227).

    Added and never changed: a later action for the same type and chapter
    takes its place on the page, and the earlier one stays in the record.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    type_rating = models.CharField("Type Rating", max_length=200)
    chapter = models.PositiveSmallIntegerField("Chapter")
    action = models.CharField("Action", max_length=200)
    recorded_on = models.DateField("Recorded")
    # The action this one takes the place of, for the same type rating and chapter.
    supersedes = models.OneToOneField(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="superseded_by"
    )

    class Meta:
        ordering = ["type_rating", "chapter", "recorded_on", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(type_rating="")
                & ~Q(action="")
                & Q(chapter__gte=FIRST_CHAPTER, chapter__lte=LAST_CHAPTER),
                name="repeat_action_has_a_type_a_chapter_and_an_action",
            ),
        ]

    def __str__(self) -> str:
        return self.action

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the action. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("An action is added, never changed")
        super().save(*args, **kwargs)
