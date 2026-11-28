"""Certificates of release to service (REQ-260 to REQ-268)."""

from typing import Any

from django.db import models
from django.db.models import Q

from airworthiness_plus.defects.models import Defect
from airworthiness_plus.history.models import Record, RecordsAreNeverDeletedError
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person
from airworthiness_plus.programme.models import WorkDone


class IssuedBy(models.TextChoices):
    """Who issued the certificate, ML.A.801(b)(1) to (3)."""

    ORGANISATION = "Organisation Certifying Staff", "Organisation Certifying Staff"
    INDEPENDENT = "Independent Certifying Staff", "Independent Certifying Staff"
    PILOT_OWNER = "Pilot-Owner", "Pilot-Owner"


# The point of ML.A.801(b) each is.
POINTS = {
    IssuedBy.ORGANISATION: "ML.A.801(b)(1)",
    IssuedBy.INDEPENDENT: "ML.A.801(b)(2)",
    IssuedBy.PILOT_OWNER: "ML.A.801(b)(3), ML.A.803",
}


class Release(Record):
    """The certificate of release to service for one piece of work done (REQ-260).

    It holds what ML.A.801(e) has a certificate contain: the maintenance,
    the day it was completed, who issued it with the approval reference or
    licence number, and any limitations. The certificate is added and never
    changed. What it says of the work, of the certifying staff and of the
    organisation is written by the database as they stood that day.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    work = models.OneToOneField(WorkDone, on_delete=models.PROTECT, related_name="certificate")
    reference = models.CharField("Certificate Reference", max_length=100)
    kind = models.CharField("Issued By", max_length=40, choices=IssuedBy.choices)
    issued_by = models.ForeignKey(
        Person, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    # For certifying staff of the organisation the database writes these three
    # from the person and the organisation; for anyone else the name and the
    # licence number are as given.
    maintenance_authorisation = models.ForeignKey(
        MaintenanceAuthorisation, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    scope_confirmed = models.BooleanField(default=False)
    legacy_evidence = models.CharField(
        "Signed Legacy Evidence Reference", max_length=160, blank=True
    )
    issuer_name = models.CharField("Name", max_length=200, blank=True)
    licence = models.CharField("Licence Number", max_length=100, blank=True)
    governing_approval = models.ForeignKey(
        "organisations.Approval", on_delete=models.PROTECT, null=True, related_name="+"
    )
    approval_reference = models.CharField(max_length=40, blank=True)
    issued_on = models.DateField("Issued")
    incomplete = models.BooleanField("Maintenance Could Not Be Completed", default=False)
    limitations = models.CharField("Limitations", max_length=200, blank=True)
    # The work as it stood, written by the database.
    registration = models.CharField(max_length=10, blank=True)
    maintenance = models.CharField(max_length=200, blank=True)
    completed_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["issued_on", "id"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(reference="") & Q(kind__in=IssuedBy.values),
                name="release_has_a_reference_and_a_known_issuer",
            ),
            # Certifying staff of the organisation are a person of it; anyone else is named.
            models.CheckConstraint(
                condition=Q(kind=IssuedBy.ORGANISATION, issued_by__isnull=False)
                | (
                    Q(kind__in=[IssuedBy.INDEPENDENT, IssuedBy.PILOT_OWNER], issued_by__isnull=True)
                    & ~Q(issuer_name="")
                ),
                name="release_names_who_issued_it",
            ),
            # ML.A.803(d): the pilot licence number of the pilot-owner.
            models.CheckConstraint(
                condition=~Q(kind=IssuedBy.PILOT_OWNER) | ~Q(licence=""),
                name="release_by_a_pilot_owner_has_the_licence_number",
            ),
            # ML.A.801(f): incomplete maintenance is released with its limitations stated.
            models.CheckConstraint(
                condition=Q(incomplete=False) | ~Q(limitations=""),
                name="release_of_incomplete_maintenance_states_its_limitations",
            ),
        ]

    def __str__(self) -> str:
        return self.reference

    def save(self, *args: Any, **kwargs: Any) -> None:
        """Add the certificate. One that exists is never saved again."""
        if not self._state.adding:
            raise RecordsAreNeverDeletedError("A certificate is added, never changed")
        super().save(*args, **kwargs)

    @property
    def issued_by_text(self) -> str:
        """Return who issued it: Chris Moore, Certifying Staff, or the name and Pilot-Owner."""
        role = "Certifying Staff" if self.kind == IssuedBy.ORGANISATION else str(self.kind)
        return f"{self.issuer_name}, {role}"

    @property
    def identity_text(self) -> str:
        """Return the approval reference or the licence number, as ML.A.801(e)(3) asks."""
        if self.kind == IssuedBy.ORGANISATION:
            return ", ".join(part for part in (self.approval_reference, self.licence) if part)
        return f"Licence {self.licence}" if self.licence else ""

    @property
    def limitations_text(self) -> str:
        """Return the limitations, or None as the Release to Service board writes it."""
        return self.limitations or "None"

    @property
    def point(self) -> str:
        """Return the point of ML.A.801(b) the certificate was issued under."""
        return POINTS[IssuedBy(self.kind)]


class HistoricalReleaseEvidence(Record):
    """A signed source retained separately from a verified release."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    work = models.ForeignKey(WorkDone, on_delete=models.PROTECT, related_name="historical_releases")
    grounding_defect = models.ForeignKey(Defect, on_delete=models.PROTECT, related_name="+")
    reference = models.CharField("Signed Release Reference", max_length=100)
    issuer_name = models.CharField("Issuer Named in the Source", max_length=200)
    issued_on = models.DateField("Date on the Signed Release")
    source = models.CharField("Signed Evidence Reference", max_length=200)

    class Meta:
        ordering = ["-issued_on", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["work", "reference", "issued_on"],
                name="historical_release_once_per_source",
            ),
            models.CheckConstraint(
                condition=~Q(reference="") & ~Q(issuer_name="") & ~Q(source=""),
                name="historical_release_has_evidence",
            ),
        ]
