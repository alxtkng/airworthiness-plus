"""What can be done with certificates of release to service. Views check the role first.

ML.A.801 and ML.A.803, read in the UK text on 27 November 2026
(Decisions.md, Regulation Facts in Use): who issues a certificate of
release to service and what it contains. ML.A.305(a): it is entered in
the records not later than 30 days after the maintenance is completed.

The system records a certificate that has been issued. It does not issue
one: certifying staff sign their certificate themselves.
"""

from dataclasses import dataclass
from datetime import date

from django.db import transaction
from django.db.models import QuerySet

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.defects.models import Decision, Defect
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import ApprovalType, Organisation, Privilege
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import MaintenanceAuthorisation, Person, StaffGroup
from airworthiness_plus.programme import due
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import WorkDone
from airworthiness_plus.releases.models import HistoricalReleaseEvidence, IssuedBy, Release
from airworthiness_rules.dates import days_between
from airworthiness_rules.programme import Flag, pilot_owner_notification_deadline

SHOWN_FOR_DAYS = 30
"""The Release to Service board: Issued, Last 30 Days."""

NOT_OPEN = (
    "Certifying Staff Release for an Organisation Holding Part-145, "
    "or Part-CAO with the Maintenance Privilege, ML.A.801(b)(1)"
)


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def maintains(organisation: Organisation) -> bool:
    """Return whether the organisation's own certifying staff may release (REQ-262).

    ML.A.801(b)(1): certifying staff on behalf of the approved maintenance
    organisation. That is an organisation holding Part-145, or Part-CAO
    with the maintenance privilege (CAO.A.095(a), 145.A.75).
    """
    held = approvals.types_held(organisation)
    return ApprovalType.PART_145 in held or (
        ApprovalType.PART_CAO in held and Privilege.MAINTENANCE in organisation.privileges
    )


def _grounding_defects(aircraft: Aircraft, on: date) -> QuerySet[Defect]:
    return Defect.objects.filter(
        aircraft=aircraft,
        decision=Decision.NOT_DEFERRABLE,
        found_on__lte=on,
    ).exclude(closed_on__lte=on)


@transaction.atomic
def retain_historical_evidence(
    work: WorkDone,
    *,
    reference: str,
    issuer_name: str,
    issued_on: date,
    source: str,
) -> HistoricalReleaseEvidence:
    """Retain signed evidence from a grounding period without posting a release."""
    work = WorkDone.objects.select_for_update().get(pk=work.pk)
    if not work.dated <= issued_on < aircraft_services.today():
        raise RefusedError("Give an Earlier Issue Date On or After the Work Was Completed")
    reference, issuer_name, source = reference.strip(), issuer_name.strip(), source.strip()
    if not reference or not issuer_name or not source:
        raise RefusedError("Enter the Signed Release Reference, Issuer and Evidence Reference")
    Aircraft.objects.select_for_update().get(pk=work.aircraft_id)
    grounding = _grounding_defects(work.aircraft, issued_on).select_for_update().first()
    if grounding is None:
        raise RefusedError("No Grounding Defect Was Open on the Date Given")
    if work.historical_releases.filter(reference=reference, issued_on=issued_on).exists():
        raise RefusedError("This Historical Evidence Is Already Retained")
    return HistoricalReleaseEvidence.objects.create(
        organisation_id=work.organisation_id,
        work=work,
        grounding_defect=grounding,
        reference=reference,
        issuer_name=issuer_name,
        issued_on=issued_on,
        source=source,
    )


@transaction.atomic
def record_certificate(
    work: WorkDone,
    *,
    reference: str,
    kind: IssuedBy | str,
    issued_on: date,
    issued_by: Person | None = None,
    issuer_name: str = "",
    licence: str = "",
    incomplete: bool = False,
    limitations: str = "",
    recorded_on: date | None = None,
    maintenance_authorisation: MaintenanceAuthorisation | None = None,
    scope_confirmed: bool = False,
    legacy_evidence: str = "",
) -> Release:
    """Record the certificate of release to service for work done (REQ-260 to REQ-263).

    Recording it enters the release in the aircraft's records, on
    ``recorded_on`` or today (REQ-051). One certificate for each piece of
    work: the same form sent twice waits for the first and is refused.
    """
    today = aircraft_services.today()
    reference, issuer_name, licence, limitations = (
        reference.strip(),
        issuer_name.strip(),
        licence.strip(),
        limitations.strip(),
    )
    work = WorkDone.objects.select_for_update().get(pk=work.pk)
    if (
        Release.objects.filter(work=work).exists()
        or Release.objects.filter(work_package__cards__work=work).exists()
    ):
        raise RefusedError("The Certificate for This Work Is Already Recorded")
    if not reference:
        raise RefusedError("A Certificate Has a Reference")
    if work.release_reference and work.release_reference != reference:
        raise RefusedError("The Work Is Already Recorded With Another Release Reference")
    if kind not in IssuedBy.values:
        raise RefusedError("A Certificate Says Who Issued It, ML.A.801(b)")
    if issued_on > today:
        raise RefusedError("A Certificate Is Not Issued After Today")
    if issued_on < work.dated:
        raise RefusedError("A Certificate Is Not Issued Before the Work Was Completed")
    if work.release_recorded_on is not None:
        if recorded_on is not None and recorded_on != work.release_recorded_on:
            raise RefusedError("Use the Day the Release Was Already Entered in the Records")
        recorded_on = work.release_recorded_on
    else:
        recorded_on = recorded_on or today
    if not issued_on <= recorded_on <= today:
        raise RefusedError(
            "A Certificate Is Entered in the Records On or After the Day It Was Issued, "
            "and Not After Today"
        )
    if (kind == IssuedBy.PILOT_OWNER) != work.by_pilot_owner:
        raise RefusedError(
            "Pilot-Owner Maintenance Is Released by the Pilot-Owner, and Nothing Else Is, ML.A.803"
        )
    if kind == IssuedBy.ORGANISATION:
        if not approvals.may_act_on(
            work.aircraft.organisation, issued_on, ApprovalType.PART_145, Privilege.MAINTENANCE
        ):
            raise RefusedError(NOT_OPEN)
        if issued_by is None:
            raise RefusedError("Certifying Staff Who Issue a Certificate Are Named")
        if issued_by.staff_group != StaffGroup.CERTIFYING:
            raise RefusedError("The Person Named Is Not Certifying Staff")
        if issued_by.joined_on is not None and issued_by.joined_on > issued_on:
            raise RefusedError("The Person Named Had Not Joined by the Day of Issue")
        if issued_by.left_on is not None and issued_by.left_on < issued_on:
            raise RefusedError("The Person Named Had Left by the Day of Issue")
        if issuer_name or licence:
            raise RefusedError("The Name and Licence of Certifying Staff Come From Their Record")
    else:
        if issued_by is not None:
            raise RefusedError(
                "Only Certifying Staff of the Organisation Are Chosen From the Staff"
            )
        if not issuer_name:
            raise RefusedError("A Certificate Names Who Issued It, ML.A.801(e)(3)")
        if kind == IssuedBy.PILOT_OWNER and not licence:
            raise RefusedError("A Pilot-Owner Gives the Pilot Licence Number, ML.A.803(d)")
    legacy_evidence = legacy_evidence.strip()
    try:
        people_services.check_certification_evidence(
            person=issued_by if kind == IssuedBy.ORGANISATION else None,
            on=issued_on,
            today=today,
            authorisation=maintenance_authorisation,
            scope_confirmed=scope_confirmed,
            legacy_evidence=legacy_evidence,
        )
    except people_services.RefusedError as error:
        raise RefusedError(str(error)) from error
    if incomplete and not limitations:
        raise RefusedError(
            "Incomplete Maintenance Is Released With Its Limitations Stated, ML.A.801(f)"
        )
    Aircraft.objects.select_for_update().get(pk=work.aircraft_id)
    stops = _grounding_defects(work.aircraft, issued_on).first()
    if stops is not None:
        raise RefusedError(
            f"Open Defect That Is Not Deferrable on the Day of Issue, ML.A.801(g): {stops.title}"
        )
    release = Release.objects.create(
        organisation_id=work.organisation_id,
        work=work,
        reference=reference,
        kind=kind,
        issued_by=issued_by,
        maintenance_authorisation=maintenance_authorisation,
        scope_confirmed=scope_confirmed,
        legacy_evidence=legacy_evidence,
        issuer_name=issuer_name,
        licence=licence,
        issued_on=issued_on,
        incomplete=incomplete,
        limitations=limitations,
    )
    if not work.release_reference:
        programme_services.record_release(work, reference, recorded_on)
    release.refresh_from_db()
    return release


@dataclass(frozen=True)
class ReleaseLine:
    """One piece of work done, its certificate and whether it is in the records."""

    line: due.WorkLine
    certificate: Release | None
    days_since: int

    @property
    def work(self) -> WorkDone:
        """Return the work done."""
        return self.line.work

    @property
    def in_records(self) -> bool:
        """Return whether the release has been entered in the records."""
        return bool(self.work.release_reference)

    @property
    def status(self) -> str:
        """Return the word of the status mark while the release is not in the records."""
        return "" if self.in_records else self.line.release_flag.value

    @property
    def issued_recently(self) -> bool:
        """Return whether a certificate was issued inside the board's reporting window."""
        if self.certificate is None:
            return False
        days = self.days_since - days_between(self.work.dated, self.certificate.issued_on)
        return 0 <= days <= SHOWN_FOR_DAYS

    @property
    def notice_overdue(self) -> bool:
        """Return whether a pilot-owner told the organisation late, or has not yet and is late."""
        work = self.work
        if not work.by_pilot_owner:
            return False
        if work.pilot_owner_told_on is not None:
            return self.line.told_late
        return self.days_since > days_between(
            work.dated, pilot_owner_notification_deadline(work.dated)
        )


@dataclass(frozen=True)
class Summary:
    """The counts of the Release to Service board."""

    issued: int
    not_in_records: int
    incomplete: int
    notice_overdue: int


def release_lines(today: date) -> list[ReleaseLine]:
    """Return what the Release to Service page lists (REQ-264).

    Every release not yet in the records, the nearest deadline first, and
    then the work completed in the last 30 days, the latest first.
    """
    certificates = {
        release.work_id: release
        for release in Release.objects.select_related(
            "issued_by", "maintenance_authorisation__withdrawal"
        )
    }
    lines = []
    for aircraft in Aircraft.objects.all():
        for line in due.work_lines(aircraft, today):
            if (
                line.work.pk not in certificates
                and getattr(line.work, "work_card", None) is not None
            ):
                continue
            since = days_between(line.work.dated, today)
            outstanding = line.release_flag is not Flag.NONE
            release = ReleaseLine(line, certificates.get(line.work.pk), since)
            if outstanding or 0 <= since <= SHOWN_FOR_DAYS or release.issued_recently:
                lines.append(release)
    return sorted(
        lines,
        key=lambda one: (
            one.in_records,
            one.line.release_deadline if not one.in_records else date.min,
            -one.work.dated.toordinal(),
            one.work.aircraft.registration,
            one.work.description,
        ),
    )


def summary(lines: list[ReleaseLine]) -> Summary:
    """Return the counts of the page (REQ-264)."""
    return Summary(
        issued=sum(one.issued_recently for one in lines),
        not_in_records=sum(1 for one in lines if not one.in_records),
        incomplete=sum(one.certificate is not None and one.certificate.incomplete for one in lines),
        notice_overdue=sum(1 for one in lines if one.notice_overdue),
    )


@dataclass(frozen=True)
class MayRelease:
    """One line of Who May Release: who, on what condition, and the point."""

    issued_by: str
    condition: str
    certificate: str
    point: str


# ML.A.801(b) and (e), ML.A.803 and Appendix I to Part-ML, as read on 27 November 2026.
WHO_MAY_RELEASE = (
    MayRelease(
        "Organisation Certifying Staff",
        "On Behalf of the Approved Maintenance Organisation",
        "Approval Reference of the Organisation and the Certifying Staff",
        "ML.A.801(b)(1), ML.A.801(e)(3)",
    ),
    MayRelease(
        "Independent Certifying Staff",
        "Independent Certifying Staff",
        "Identity and Licence Number Where It Applies",
        "ML.A.801(b)(2), ML.A.801(e)(3)",
    ),
    MayRelease(
        "Pilot-Owner",
        "Holds a Valid Pilot Licence, Owns the Aircraft, Limited Pilot-Owner Maintenance, "
        "Tells the Contracted Organisation Within 30 Days",
        "Identity, Signature and Pilot Licence Number, Entered in the Logbooks",
        "ML.A.801(b)(3), ML.A.803, Appendices I and II to Part-ML",
    ),
)
