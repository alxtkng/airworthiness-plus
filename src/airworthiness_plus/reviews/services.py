"""What can be done with review staff, certificates and extensions. Views check the role first."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Stage
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due
from airworthiness_plus.reviews.models import Certificate, Extension, ReviewStaff
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Unit
from airworthiness_rules.programme import Flag, deadline_flag, limit_flag
from airworthiness_rules.review import (
    EXTENSION_ANTICIPATION_DAYS,
    ExtensionNotPermittedError,
    copy_to_authority_deadline,
    days_to_expiry,
    recency_lapses,
    review_keeps_pattern,
    review_staff_recent,
    valid_to_after_extension,
    valid_to_after_review,
)


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


# Review staff


def add_review_staff(
    *,
    user: User,
    authorisation_reference: str,
    accepted_on: date,
    part_66_qualified: bool = False,
    months_involved: int = 0,
    last_review_before_records: date | None = None,
) -> ReviewStaff:
    """Record a person as airworthiness review staff (CAO.A.045)."""
    return ReviewStaff.objects.create(
        organisation_id=user.organisation_id,
        user=user,
        authorisation_reference=authorisation_reference,
        accepted_on=accepted_on,
        part_66_qualified=part_66_qualified,
        months_involved=months_involved,
        months_recorded_on=aircraft_services.today(),
        last_review_before_records=last_review_before_records,
    )


def last_review(staff: ReviewStaff) -> date | None:
    """Return the date of the person's last airworthiness review, here or before these records."""
    issued = staff.certificates.filter(voided=False).order_by("issued_on").last()
    dates = [
        value
        for value in (issued.issued_on if issued else None, staff.last_review_before_records)
        if value is not None
    ]
    return max(dates) if dates else None


@dataclass(frozen=True)
class StaffLine:
    """One member of review staff and whether their experience is recent (REQ-113, REQ-114)."""

    staff: ReviewStaff
    last_review: date | None
    recent: bool
    restoration_needed: bool
    lapses: date | None
    flag: Flag

    @property
    def state(self) -> str:
        if self.staff.left_on is not None:
            return "Left"
        if self.restoration_needed:
            return "Lapsed, Restoration Needed"
        return "Current" if self.recent else "Lapsed, Restoration Needed"

    @property
    def basis(self) -> str:
        """Return what recency rests on, so that a missing date is never read as all clear."""
        if self.staff.months_involved >= 6:
            return "6 Months of Continuing Airworthiness Management in the 2-Year Period"
        if self.last_review is not None:
            return "A Review in the Last 12 Months"
        return "No Review and Less Than 6 Months of Continuing Airworthiness Management"

    @property
    def current(self) -> bool:
        return self.state == "Current"


def _recent_by_rule(staff: ReviewStaff, today: date) -> bool:
    return review_staff_recent(
        today,
        last_review=last_review(staff),
        months_involved_in_two_years=staff.months_involved,
    )


def _restoration_needed(staff: ReviewStaff) -> bool:
    """Return whether a lapse has been recorded and not yet restored, AMC1 CAO.A.045(d)."""
    if staff.lapsed_on is None:
        return False
    return staff.restored_on is None or staff.restored_on < staff.lapsed_on


def staff_line(staff: ReviewStaff, today: date) -> StaffLine:
    """Work out whether one member of review staff is recent, AMC1 CAO.A.045(c) and (d)."""
    last = last_review(staff)
    recent = _recent_by_rule(staff, today)
    lapses = recency_lapses(last_review=last, months_involved_in_two_years=staff.months_involved)
    flag = Flag.NONE
    if staff.left_on is None and lapses is not None:
        thresholds = due.thresholds_of(staff.organisation)
        flag = limit_flag(Limit(Unit.CALENDAR, lapses, days_between(today, lapses)), thresholds)
    return StaffLine(staff, last, recent, _restoration_needed(staff), lapses, flag)


def note_lapse(staff: ReviewStaff, today: date) -> bool:
    """Record that recency has been lost, if it has, and return whether it is lost.

    Called before anything that could make the person look recent again: a
    change to their months or their last review, and an attempt to issue.
    Once recorded, the lapse stands until a restoration is recorded.
    """
    if _restoration_needed(staff):
        return True
    if _recent_by_rule(staff, today):
        return False
    staff.lapsed_on = today
    staff.save(update_fields=["lapsed_on"])
    return True


def may_issue(staff: ReviewStaff, today: date) -> bool:
    """Return whether this person may issue a certificate today (REQ-109, threat TH-009).

    Still with the organisation, an active user, with recent experience,
    and with no lapse awaiting restoration.
    """
    return (
        staff.left_on is None
        and staff.user.is_active
        and not _restoration_needed(staff)
        and _recent_by_rule(staff, today)
    )


def update_involvement(
    staff: ReviewStaff, *, months: int, last_review_before_records: date | None
) -> None:
    """Change the recorded months of involvement, or the last review before these records.

    If recency has already been lost, that is recorded first, so that the
    change cannot stand in for a restoration.
    """
    today = aircraft_services.today()
    if last_review_before_records is not None and last_review_before_records > today:
        raise RefusedError("A Review Cannot Be Dated After Today")
    if not 0 <= months <= 24:
        raise RefusedError("Months in a 2-Year Period Are Between 0 and 24")
    note_lapse(staff, today)
    staff.months_involved = months
    staff.months_recorded_on = today
    staff.last_review_before_records = last_review_before_records
    staff.save(
        update_fields=["months_involved", "months_recorded_on", "last_review_before_records"]
    )


def record_restoration(
    staff: ReviewStaff, *, on: date, supervisor: ReviewStaff | None = None, under: str = ""
) -> None:
    """Record a review under supervision that restores a lapsed authorisation (REQ-114).

    AMC1 CAO.A.045(d): under the supervision of the Civil Aviation
    Authority, or of another currently valid member of review staff of the
    organisation. The review then counts as the person's last review.
    """
    today = aircraft_services.today()
    if on > today:
        raise RefusedError("A Restoration Cannot Be Dated After Today")
    if not note_lapse(staff, on):
        raise RefusedError("Only a Lapsed Authorisation Is Restored")
    if supervisor is not None:
        if supervisor.pk == staff.pk:
            raise RefusedError("Nobody Supervises Their Own Restoration")
        if supervisor.organisation_id != staff.organisation_id or not may_issue(supervisor, on):
            raise RefusedError(
                "The Supervisor Is Currently Valid Review Staff of This Organisation"
            )
        under = f"{supervisor.user.full_name}, {supervisor.authorisation_reference}"
    if not under.strip():
        raise RefusedError("A Restoration Names the Supervision")
    if staff.lapsed_on is not None and on < staff.lapsed_on:
        raise RefusedError("A Restoration Follows the Lapse")
    staff.restored_on = on
    staff.restored_under = under.strip()
    if staff.last_review_before_records is None or on > staff.last_review_before_records:
        staff.last_review_before_records = on
    staff.save(update_fields=["restored_on", "restored_under", "last_review_before_records"])


# Certificates


def certificates(aircraft: Aircraft) -> list[Certificate]:
    """Return every certificate recorded for the aircraft, oldest first, voided ones included."""
    return list(Certificate.objects.filter(aircraft=aircraft).order_by("issued_on", "id"))


def current_certificate(aircraft: Aircraft) -> Certificate | None:
    """Return the latest certificate of the aircraft that has not been voided."""
    found: Certificate | None = (
        Certificate.objects.filter(aircraft=aircraft, voided=False).order_by("issued_on").last()
    )
    return found


def valid_to(certificate: Certificate) -> date:
    """Return the last day of validity, after any extensions."""
    last = certificate.extensions.order_by("extended_on").last()
    return last.valid_to if last is not None else certificate.valid_to


def current_valid_to(aircraft: Aircraft) -> date | None:
    """Return the day the aircraft's review certificate is valid to, if it has one (REQ-100)."""
    certificate = current_certificate(aircraft)
    return valid_to(certificate) if certificate is not None else None


def record_certificate(
    aircraft: Aircraft,
    *,
    reference: str,
    issued_on: date,
    valid_to: date,
    issued_elsewhere_by: str,
    airframe_hours: Decimal | None = None,
) -> Certificate:
    """Record a certificate issued by another organisation or the authority.

    It keeps the reference it was issued with. No serial of this
    organisation is used.
    """
    if not reference.strip() or not issued_elsewhere_by.strip():
        raise RefusedError("A Certificate Issued Elsewhere Has Its Reference and Its Issuer")
    if issued_on > aircraft_services.today():
        raise RefusedError("A Certificate Cannot Be Issued After Today")
    if valid_to <= issued_on:
        raise RefusedError("A Certificate Expires After It Is Issued")
    return Certificate.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        reference=reference.strip(),
        issued_on=issued_on,
        valid_to=valid_to,
        issued_elsewhere_by=issued_elsewhere_by.strip(),
        airframe_hours=airframe_hours,
    )


@transaction.atomic
def issue_certificate(
    aircraft: Aircraft,
    *,
    staff: ReviewStaff,
    issued_on: date,
    airframe_hours: Decimal | None = None,
) -> Certificate:
    """Issue a certificate after a review (REQ-101, REQ-102, REQ-109, REQ-110).

    The caller has established that the review is complete. This checks the
    person: review staff of this organisation with recent experience on the
    day of issue. The last day of validity comes from the rules: a year
    after the previous one if the review is within the 90 days before it
    (ML.A.903(d)), otherwise a year after issue (ML.A.901(a)). The serial
    and reference are set by the database.
    """
    if issued_on > aircraft_services.today():
        raise RefusedError("A Certificate Cannot Be Issued After Today")
    if staff.organisation_id != aircraft.organisation_id:
        raise RefusedError("Review Staff Belong to Another Organisation")
    if not may_issue(staff, issued_on):
        raise RefusedError("CAO.A.045(c): The Review Staff Member Does Not Have Recent Experience")
    previous = current_certificate(aircraft)
    if previous is not None and issued_on < previous.issued_on:
        raise RefusedError("A Certificate Is Not Issued Before the One It Follows")
    expiry = valid_to_after_review(issued_on, valid_to(previous) if previous else None)
    certificate = Certificate.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        issued_on=issued_on,
        valid_to=expiry,
        issued_by=staff,
        airframe_hours=airframe_hours,
    )
    certificate.refresh_from_db()
    return certificate


def void_certificate(certificate: Certificate, reason: str) -> None:
    """Void a certificate. It stays in the record and its serial is never used again."""
    if not reason.strip():
        raise RefusedError("A Void Has a Reason")
    certificate.voided = True
    certificate.void_reason = reason.strip()
    certificate.save(update_fields=["voided", "void_reason"])


@transaction.atomic
def extend_certificate(
    certificate: Certificate,
    *,
    extended_by: User,
    managed_for_12_months: bool,
    maintained_by_approved_organisations: bool,
    no_evidence_not_airworthy: bool,
    extended_on: date | None = None,
) -> Extension:
    """Extend a certificate by a year, ML.A.901(c) and (d) (REQ-104 to REQ-106).

    Each of the three conditions is confirmed. At most two consecutive
    extensions, and not more than 30 days before expiry.
    """
    on = extended_on or aircraft_services.today()
    if on > aircraft_services.today():
        raise RefusedError("An Extension Cannot Be Dated After Today")
    if certificate.voided or current_certificate(certificate.aircraft) != certificate:
        raise RefusedError("Only the Current Certificate of an Aircraft Is Extended")
    if not (
        managed_for_12_months and maintained_by_approved_organisations and no_evidence_not_airworthy
    ):
        raise RefusedError("ML.A.901(c): Every Condition for an Extension Is Confirmed")
    try:
        expiry = valid_to_after_extension(on, valid_to(certificate), certificate.extensions.count())
    except ExtensionNotPermittedError as error:
        raise RefusedError(str(error)) from error
    return Extension.objects.create(
        organisation_id=certificate.organisation_id,
        certificate=certificate,
        extended_on=on,
        valid_to=expiry,
        extended_by=extended_by,
        managed_for_12_months=True,
        maintained_by_approved_organisations=True,
        no_evidence_not_airworthy=True,
    )


def record_copy_sent(item: Certificate | Extension, on: date) -> None:
    """Record the day the copy went to the Civil Aviation Authority, ML.A.903(f) (REQ-111)."""
    started = item.issued_on if isinstance(item, Certificate) else item.extended_on
    if on > aircraft_services.today() or on < started:
        raise RefusedError("The Copy Is Sent On or After the Day of Issue, and Not After Today")
    item.copy_sent_on = on
    item.save(update_fields=["copy_sent_on"])


# The schedule


@dataclass(frozen=True)
class CopyLine:
    """A copy owed to the Civil Aviation Authority (REQ-111)."""

    certificate: Certificate
    extension: Extension | None
    deadline: date
    flag: Flag


@dataclass(frozen=True)
class ScheduleLine:
    """One aircraft on the review schedule (REQ-100, REQ-116)."""

    aircraft: Aircraft
    certificate: Certificate | None
    valid_to: date | None
    days: int | None
    flag: Flag
    in_review_window: bool
    in_extension_window: bool
    extensions: int
    copies: tuple[CopyLine, ...]


def _copies(certificate: Certificate | None, today: date) -> tuple[CopyLine, ...]:
    if certificate is None or certificate.issued_by is None:
        return ()
    owed = []
    if certificate.copy_sent_on is None:
        deadline = copy_to_authority_deadline(certificate.issued_on)
        owed.append(CopyLine(certificate, None, deadline, deadline_flag(today, deadline)))
    for extension in certificate.extensions.filter(copy_sent_on__isnull=True):
        deadline = copy_to_authority_deadline(extension.extended_on)
        owed.append(CopyLine(certificate, extension, deadline, deadline_flag(today, deadline)))
    return tuple(owed)


def schedule_line(aircraft: Aircraft, today: date) -> ScheduleLine:
    """Work out where one aircraft stands on the review schedule."""
    certificate = current_certificate(aircraft)
    if certificate is None:
        return ScheduleLine(aircraft, None, None, None, Flag.NONE, False, False, 0, ())
    expiry = valid_to(certificate)
    days = days_to_expiry(today, expiry)
    flag = limit_flag(Limit(Unit.CALENDAR, expiry, days), due.thresholds_of(aircraft.organisation))
    extended = certificate.extensions.count()
    copies = _copies(certificate, today)
    return ScheduleLine(
        aircraft=aircraft,
        certificate=certificate,
        valid_to=expiry,
        days=days,
        flag=flag,
        in_review_window=review_keeps_pattern(today, expiry),
        in_extension_window=0 <= days <= EXTENSION_ANTICIPATION_DAYS,
        extensions=extended,
        copies=copies,
    )


def schedule(organisation: Organisation, today: date) -> list[ScheduleLine]:
    """Return every aircraft of the Fleet by days remaining to expiry (REQ-116).

    An aircraft with no certificate recorded comes first: nobody knows
    where it stands.
    """
    del organisation
    lines = [schedule_line(a, today) for a in Aircraft.objects.filter(stage=Stage.FLEET)]
    return sorted(lines, key=lambda line: (line.days is not None, line.days or 0))
