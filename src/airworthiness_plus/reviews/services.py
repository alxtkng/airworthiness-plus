"""What can be done with review staff, certificates and extensions. Views check the role first."""

import uuid
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind, Stage
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.formatting import long_date
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import due
from airworthiness_plus.reviews.checklist import CHECKLIST, SURVEY
from airworthiness_plus.reviews.models import (
    Certificate,
    Extension,
    ProgrammeDiscrepancy,
    Result,
    Review,
    ReviewItem,
    ReviewStaff,
)
from airworthiness_rules.dates import days_between
from airworthiness_rules.intervals import Limit, Unit
from airworthiness_rules.programme import Flag, deadline_flag, limit_flag
from airworthiness_rules.review import (
    COPY_TO_AUTHORITY_DAYS,
    EXTENSION_ANTICIPATION_DAYS,
    MAX_CONSECUTIVE_EXTENSIONS,
    ExtensionNotPermittedError,
    copy_to_authority_deadline,
    days_to_expiry,
    extension_window_opens,
    recency_lapses,
    review_keeps_pattern,
    review_staff_recent,
    review_window_opens,
    valid_to_after_extension,
    valid_to_after_review,
)


class RefusedError(ValueError):
    """What was asked for does not agree with the regulation or the records."""


def _open_to(organisation_id: uuid.UUID) -> Organisation:
    """Return the organisation, or refuse one whose approval does not give the privilege.

    CAO.A.095(c). The pages check first and enter the refusal in the access
    log; this holds whatever the page does.
    """
    organisation = Organisation.objects.get(pk=organisation_id)
    reason = approvals.review_refusal(organisation)
    if reason:
        raise RefusedError(reason)
    return organisation


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
    """Record a person as airworthiness review staff (CAO.A.045).

    Their last review before these records is on or before today, the day
    they are recorded here. Anything later is a review in these records.
    """
    _open_to(user.organisation_id)
    today = aircraft_services.today()
    _check_before_records(last_review_before_records, today)
    return ReviewStaff.objects.create(
        organisation_id=user.organisation_id,
        user=user,
        authorisation_reference=authorisation_reference,
        accepted_on=accepted_on,
        part_66_qualified=part_66_qualified,
        months_involved=months_involved,
        months_recorded_on=today,
        recorded_on=today,
        last_review_before_records=last_review_before_records,
    )


def _check_before_records(last_review_before_records: date | None, recorded_on: date) -> None:
    if last_review_before_records is not None and last_review_before_records > recorded_on:
        raise RefusedError(
            "A Review Before These Records Is Not After "
            f"{long_date(recorded_on)}, When the Person Was Recorded as Review Staff"
        )


def last_review(staff: ReviewStaff) -> date | None:
    """Return the date of the person's last airworthiness review, here or before these records.

    A review under supervision that restored a lapsed authorisation counts
    (AMC1 CAO.A.045(d)). It has its own date: it is a review in these
    records, not one from before them.
    """
    issued = staff.certificates.filter(voided=False).order_by("issued_on").last()
    dates = [
        value
        for value in (
            issued.issued_on if issued else None,
            staff.last_review_before_records,
            staff.restored_on,
        )
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

    @property
    def working(self) -> Working:
        """Return how the person's recency was worked out (REQ-139)."""
        staff = self.staff
        inputs = [
            (
                "Last Review",
                long_date(self.last_review) if self.last_review else "None Recorded",
            ),
            (
                "Months of Continuing Airworthiness Management in the 2-Year Period",
                f"{staff.months_involved}, Recorded {long_date(staff.months_recorded_on)}",
            ),
            ("Recency Rests On", self.basis),
        ]
        if self.lapses is not None:
            inputs.append(("Last Day the Last Review Counts", long_date(self.lapses)))
        if staff.lapsed_on is not None:
            inputs.append(("Lapse Recorded", long_date(staff.lapsed_on)))
        if staff.restored_on is not None:
            inputs.append(
                ("Restored", f"{long_date(staff.restored_on)} Under {staff.restored_under}")
            )
        return Working(
            title="How Recency Was Worked Out",
            figure=self.state,
            rule=(
                "Recent with 6 Months of Continuing Airworthiness Management in the 2-Year "
                "Period, or with 1 Airworthiness Review in the Last 12 Months. A Review Counts "
                "to the Same Day of the Month 12 Months Later, and That Day Is Taken to Count. "
                "Once Lost, Recency Returns Only by a Review Under Supervision"
            ),
            inputs=tuple(inputs),
            source="AMC1 CAO.A.045(c) and (d)",
        )


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
    # Held while this is decided, so that a certificate from before these
    # records cannot be recorded against the date being replaced.
    staff = ReviewStaff.objects.select_for_update().select_related("user").get(pk=staff.pk)
    _check_before_records(last_review_before_records, staff.recorded_on)
    latest = staff.certificates.filter(from_before_records=True).order_by("issued_on").last()
    if latest is not None and (
        last_review_before_records is None or last_review_before_records < latest.issued_on
    ):
        raise RefusedError(
            "A Certificate of Theirs Recorded From Before These Records Is Dated "
            f"{long_date(latest.issued_on)}"
        )
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
    staff.save(update_fields=["restored_on", "restored_under"])


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
    issued_elsewhere_by: str = "",
    issued_by: ReviewStaff | None = None,
    airframe_hours: Decimal | None = None,
) -> Certificate:
    """Record a certificate that was not issued in these records.

    Either one issued by another organisation or the authority, or one the
    organisation's own review staff issued before these records. Both keep
    the reference they were issued with, and no serial is used.

    One of the organisation's own is dated no later than the last review
    recorded for the person from before these records, which the
    Administrator states. Recording it therefore cannot change whether the
    person has recent experience (REQ-113), and cannot stand in for a review
    carried out in these records (REQ-109).
    """
    _open_to(aircraft.organisation_id)
    elsewhere = issued_elsewhere_by.strip()
    if issued_by is not None and elsewhere:
        raise RefusedError(
            "A Certificate Is Issued by Review Staff of This Organisation or Elsewhere, Not Both"
        )
    if not reference.strip() or (issued_by is None and not elsewhere):
        raise RefusedError("A Certificate Recorded Has Its Reference and Its Issuer")
    if issued_on > aircraft_services.today():
        raise RefusedError("A Certificate Cannot Be Issued After Today")
    if valid_to <= issued_on:
        raise RefusedError("A Certificate Expires After It Is Issued")
    if issued_by is not None:
        if issued_by.organisation_id != aircraft.organisation_id:
            raise RefusedError("Review Staff Belong to Another Organisation")
        last_before = issued_by.last_review_before_records
        if last_before is None or issued_on > last_before:
            raise RefusedError(
                "A Certificate From Before These Records Is Dated No Later Than the Person's "
                "Last Review Before These Records"
            )
    certificate = Certificate.objects.create(
        organisation_id=aircraft.organisation_id,
        aircraft=aircraft,
        reference=reference.strip(),
        issued_on=issued_on,
        valid_to=valid_to,
        issued_by=issued_by,
        issued_elsewhere_by=elsewhere,
        from_before_records=issued_by is not None,
        airframe_hours=airframe_hours,
    )
    # The database writes what one of the organisation's own shows of who
    # issued it, as it stands today, and never lets it be altered (REQ-110).
    certificate.refresh_from_db()
    return certificate


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
    day of issue. What it shows of the organisation and the person is written
    by the database as they stand at issue, and is never altered afterwards
    (independent review of 24 November 2026, finding 1). The last day of
    validity comes from the rules: a year
    after the previous one if the review is within the 90 days before it
    (ML.A.903(d)), otherwise a year after issue (ML.A.901(a)). The serial
    and reference are set by the database.
    """
    _open_to(aircraft.organisation_id)
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
    organisation = _open_to(certificate.organisation_id)
    if extended_by.organisation_id != organisation.id:
        raise RefusedError("A Certificate Is Extended by a User of the Same Organisation")
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
    airframe = certificate.aircraft.counters.filter(kind=CounterKind.AIRFRAME).first()
    reading = aircraft_services.current_reading(airframe) if airframe is not None else None
    extension = Extension.objects.create(
        organisation_id=certificate.organisation_id,
        certificate=certificate,
        extended_on=on,
        valid_to=expiry,
        extended_by=extended_by,
        airframe_hours=reading.hours if reading is not None else None,
        managed_for_12_months=True,
        maintained_by_approved_organisations=True,
        no_evidence_not_airworthy=True,
    )
    # The database writes who extended it and the organisation's name and
    # approval reference, as they stand today (REQ-110).
    extension.refresh_from_db()
    return extension


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


def issued_in_these_records(certificate: Certificate) -> bool:
    """Return whether the organisation issued the certificate in these records."""
    return certificate.issued_by_id is not None and not certificate.from_before_records


def _copies(certificate: Certificate | None, today: date) -> tuple[CopyLine, ...]:
    """Return the copies owed for a certificate and for each extension of it.

    The copy of a certificate is tracked when it was issued in these
    records. The copy of an extension is owed whoever issued the
    certificate, because the extension is this organisation's (ML.A.903(f)).
    """
    if certificate is None:
        return ()
    owed = []
    if issued_in_these_records(certificate) and certificate.copy_sent_on is None:
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
    thresholds = due.certificate_thresholds(aircraft.organisation)
    flag = limit_flag(Limit(Unit.CALENDAR, expiry, days), thresholds)
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


# How each figure of the schedule was worked out (REQ-139)

ANNIVERSARY = "The Last Day Is Taken as the Anniversary, Which Is To Be Confirmed"


def _validity_working(certificate: Certificate) -> Working:
    """Return how the last day of validity of a certificate was reached.

    A rule is given only where it gives the date recorded. Anything else is
    shown as what the certificate says, never as a calculation.
    """
    expiry = valid_to(certificate)
    title = f"How Valid to {long_date(expiry)} Was Calculated"
    inputs = [
        ("Certificate Reference", certificate.reference),
        ("Date of Issue", long_date(certificate.issued_on)),
    ]
    extensions = list(certificate.extensions.order_by("extended_on"))
    if extensions:
        inputs.append(("Date of Expiry Before Any Extension", long_date(certificate.valid_to)))
        inputs.extend(
            (
                f"Extension {number}",
                f"Made {long_date(one.extended_on)}, Valid to {long_date(one.valid_to)}",
            )
            for number, one in enumerate(extensions, start=1)
        )
        return Working(
            title=title,
            figure=long_date(expiry),
            rule=f"Each Extension Adds 1 Year to the Date of Expiry Before It. {ANNIVERSARY}",
            inputs=tuple(inputs),
            source="ML.A.901(c) and (d)",
        )
    if issued_in_these_records(certificate):
        previous = (
            Certificate.objects.filter(
                aircraft_id=certificate.aircraft_id,
                voided=False,
                issued_on__lt=certificate.issued_on,
            )
            .order_by("issued_on")
            .last()
        )
        before = valid_to(previous) if previous is not None else None
        if (
            previous is not None
            and before is not None
            and review_keeps_pattern(certificate.issued_on, before)
            and valid_to_after_review(certificate.issued_on, before) == expiry
        ):
            inputs.extend(
                (
                    ("Certificate Before It", previous.reference),
                    ("Its Date of Expiry", long_date(before)),
                    ("90-Day Window Opened", long_date(review_window_opens(before))),
                )
            )
            return Working(
                title=title,
                figure=long_date(expiry),
                rule=(
                    "A Review in the 90 Days Before the Date of Expiry Keeps the Pattern: "
                    f"Valid for 1 Year From the Date of Expiry Before It. {ANNIVERSARY}"
                ),
                inputs=tuple(inputs),
                source="ML.A.903(d)",
            )
        outside = before is None or not review_keeps_pattern(certificate.issued_on, before)
        if outside and valid_to_after_review(certificate.issued_on, None) == expiry:
            if before is not None and previous is not None:
                inputs.extend(
                    (
                        ("Certificate Before It", previous.reference),
                        ("Its Date of Expiry", long_date(before)),
                    )
                )
            return Working(
                title=title,
                figure=long_date(expiry),
                rule=(
                    "Valid for 1 Year From the Review, Which Was Not in the 90 Days Before "
                    f"a Date of Expiry. {ANNIVERSARY}"
                ),
                inputs=tuple(inputs),
                source="ML.A.901(a)",
            )
    inputs.append(("Date of Expiry", long_date(certificate.valid_to)))
    return Working(
        title=f"Where Valid to {long_date(expiry)} Comes From",
        figure=long_date(expiry),
        rule=(
            "The Date of Expiry Set When the Certificate Was Issued. The Certificates Recorded "
            "Before It Have Changed Since, So the Rule Is Not Shown Again"
            if issued_in_these_records(certificate)
            else "The Date of Expiry Written on the Certificate, as Recorded. It Is Not Calculated"
        ),
        inputs=tuple(inputs),
        source="The Certificate, CAA Form 15c",
    )


def working(line: ScheduleLine, today: date) -> tuple[Working, ...]:
    """Return how each figure shown for an aircraft's review was worked out (REQ-139)."""
    certificate = line.certificate
    if certificate is None or line.valid_to is None or line.days is None:
        return ()
    expiry = line.valid_to
    remaining = formatting.amount(Unit.CALENDAR, line.days)
    limit = due.certificate_thresholds(line.aircraft.organisation).days
    found = [
        _validity_working(certificate),
        Working(
            title=f"How {remaining} Remaining Was Calculated",
            figure=remaining,
            rule=(
                "An Exact Count of Days From Today to the Last Day of Validity. "
                f"Due Soon at {limit} Days or Fewer, Which This Organisation Has Set"
            ),
            inputs=(("Today", long_date(today)), ("Valid To", long_date(expiry))),
            source="ML.A.901(a); the Count and the Due Soon Limit Are the System's Own",
        ),
        Working(
            title="How the 90-Day Window Was Calculated",
            figure="Inside" if line.in_review_window else "Outside",
            rule=(
                "A Review From 90 Days Before the Date of Expiry, up to That Date, Keeps the "
                "Pattern: the New Certificate Runs 1 Year From the Old Date of Expiry"
            ),
            inputs=(
                ("Valid To", long_date(expiry)),
                ("Window Opens", long_date(review_window_opens(expiry))),
                ("Today", long_date(today)),
            ),
            source="ML.A.903(d)",
        ),
        Working(
            title=f"How {line.extensions} of {MAX_CONSECUTIVE_EXTENSIONS} Extensions Was Counted",
            figure=f"{line.extensions} of {MAX_CONSECUTIVE_EXTENSIONS}",
            rule=(
                "At Most 2 Extensions in a Row Since the Last Review, 1 Year Each, Made From "
                "30 Days Before the Date of Expiry up to That Date"
            ),
            inputs=(
                ("Extensions Since the Last Review", str(line.extensions)),
                ("Valid To", long_date(expiry)),
                (
                    ("An Extension Can Be Made From", long_date(extension_window_opens(expiry)))
                    if line.extensions < MAX_CONSECUTIVE_EXTENSIONS
                    else ("Next", "No Further Extension: a Review Is Needed")
                ),
            ),
            source="ML.A.901(c) and (d)",
        ),
    ]
    for copy in line.copies:
        of_extension = copy.extension is not None
        started = copy.extension.extended_on if copy.extension else copy.certificate.issued_on
        found.append(
            Working(
                title=f"How the Copy by {long_date(copy.deadline)} Was Calculated",
                figure=long_date(copy.deadline),
                rule="A Copy Goes to the Civil Aviation Authority Within 10 Days of the Date "
                "of Issue or Extension",
                inputs=(
                    ("Date of Extension" if of_extension else "Date of Issue", long_date(started)),
                    ("Days Allowed", str(COPY_TO_AUTHORITY_DAYS)),
                ),
                source="ML.A.903(f)",
            )
        )
    return tuple(found)


def schedule(organisation: Organisation, today: date) -> list[ScheduleLine]:
    """Return every aircraft of the Fleet by days remaining to expiry (REQ-116).

    An aircraft with no certificate recorded comes first: nobody knows
    where it stands.
    """
    del organisation
    lines = [schedule_line(a, today) for a in Aircraft.objects.filter(stage=Stage.FLEET)]
    return sorted(lines, key=lambda line: (line.days is not None, line.days or 0))


# The review itself


@transaction.atomic
def start_review(
    aircraft: Aircraft, *, staff: ReviewStaff, started_on: date | None = None
) -> Review:
    """Start a review, with every point of ML.A.903(a) and (c) to be verified (REQ-107, REQ-108)."""
    _open_to(aircraft.organisation_id)
    on = started_on or aircraft_services.today()
    if on > aircraft_services.today():
        raise RefusedError("A Review Cannot Be Started After Today")
    if staff.organisation_id != aircraft.organisation_id:
        raise RefusedError("Review Staff Belong to Another Organisation")
    review = Review.objects.create(
        organisation_id=aircraft.organisation_id, aircraft=aircraft, staff=staff, started_on=on
    )
    ReviewItem.objects.bulk_create(
        ReviewItem(
            organisation_id=aircraft.organisation_id,
            review=review,
            position=position,
            reference=point.reference,
            part=point.part,
            label=point.label,
            may_not_apply=point.may_not_apply,
        )
        for position, point in enumerate(CHECKLIST, start=1)
    )
    return review


def _open(review: Review) -> None:
    """Refuse a change to a review whose certificate is issued.

    The review is read again under a lock held to the end of the
    transaction, so a change made while the certificate is being issued
    waits for the issue and is then refused.
    """
    locked = Review.objects.select_for_update().only("certificate_id").get(pk=review.pk)
    if locked.certificate_id is not None:
        raise RefusedError("A Review Is Never Altered Once Its Certificate Is Issued")


@transaction.atomic
def record_item(item: ReviewItem, *, result: Result, evidence: str, finding: str = "") -> None:
    """Record the result of one point, with the evidence sampled and any finding (REQ-107)."""
    _open(item.review)
    if not evidence.strip():
        raise RefusedError("A Result Comes with the Evidence Sampled")
    if result == Result.NOT_APPLICABLE and not item.may_not_apply:
        raise RefusedError("This Point Applies to Every Aircraft")
    if result == Result.FINDING and not finding.strip():
        raise RefusedError("A Finding Is Described")
    item.result = result
    item.evidence = evidence.strip()
    item.finding = finding.strip() if result == Result.FINDING else ""
    item.closure = ""
    item.closed_on = None
    item.save(update_fields=["result", "evidence", "finding", "closure", "closed_on"])


@transaction.atomic
def close_finding(item: ReviewItem, *, closure: str, on: date | None = None) -> None:
    """Record how a finding was closed, and when (REQ-109, ML.A.903(e)(2))."""
    _open(item.review)
    closed = on or aircraft_services.today()
    if item.result != Result.FINDING:
        raise RefusedError("Only a Finding Is Closed")
    if not closure.strip():
        raise RefusedError("A Closure Says How the Finding Was Closed")
    if closed > aircraft_services.today() or closed < item.review.started_on:
        raise RefusedError("A Finding Is Closed During the Review, and Not After Today")
    item.closure = closure.strip()
    item.closed_on = closed
    item.save(update_fields=["closure", "closed_on"])


@transaction.atomic
def record_details(
    review: Review,
    *,
    assisted_by: str,
    airframe_hours: Decimal | None,
    programme_discrepancy: str,
) -> None:
    """Record who assisted at the survey, the airframe hours, and the state of the programme."""
    _open(review)
    review.assisted_by = assisted_by.strip()
    review.airframe_hours = airframe_hours
    review.programme_discrepancy = programme_discrepancy
    review.save(update_fields=["assisted_by", "airframe_hours", "programme_discrepancy"])


def outstanding(review: Review, today: date) -> list[str]:
    """Return everything that stands between the review and its certificate (REQ-109).

    ML.A.903(e): issued only by appropriately authorised review staff,
    when the review has been completely carried out and all findings are
    closed, and when any discrepancy found in the programme has been
    addressed. ML.A.903(b): staff not qualified under Part-66 are assisted
    at the survey. An empty list means the certificate may be issued.
    """
    reasons = []
    items = list(review.items.all())
    unanswered = [item.reference for item in items if not item.result]
    if unanswered:
        reasons.append("No Result Yet for " + ", ".join(unanswered))
    open_findings = [item.reference for item in items if item.open_finding]
    if open_findings:
        reasons.append("Finding Not Closed on " + ", ".join(open_findings))
    survey_done = any(item.part == SURVEY and item.result for item in items)
    if survey_done and not review.staff.part_66_qualified and not review.assisted_by:
        reasons.append("ML.A.903(b): Name Who Assisted at the Survey")
    if review.airframe_hours is None:
        reasons.append("Airframe Flight Hours at the Review Not Entered")
    missing = [
        label
        for label, value in (
            ("Aircraft Manufacturer", review.aircraft.manufacturer),
            (
                "Manufacturer\N{RIGHT SINGLE QUOTATION MARK}s Designation",
                review.aircraft.designation,
            ),
            ("Aircraft Serial Number", review.aircraft.serial_number),
        )
        if not value
    ]
    if missing:
        reasons.append("CAA Form 15c: Not Entered for the Aircraft, " + ", ".join(missing))
    if not review.aircraft.organisation.address:
        reasons.append("CAA Form 15c: The Address of the Organisation Is Not Entered")
    if not review.programme_discrepancy:
        reasons.append(
            "ML.A.903(e)(3): State Whether a Discrepancy Was Found in the Maintenance Programme"
        )
    elif review.programme_discrepancy == ProgrammeDiscrepancy.NOT_ADDRESSED:
        reasons.append("ML.A.903(e)(3): The Maintenance Programme Discrepancy Is Not Yet Addressed")
    if not may_issue(review.staff, today):
        reasons.append("CAO.A.045(c): The Review Staff Member Does Not Have Recent Experience")
    return reasons


@transaction.atomic
def issue_from_review(review: Review) -> Certificate:
    """Issue the certificate for a completed review (REQ-109, REQ-110).

    The review is locked first, so that two requests at the same moment
    cannot each issue a certificate for it.
    """
    review = Review.objects.select_for_update().get(pk=review.pk)
    _open(review)
    today = aircraft_services.today()
    reasons = outstanding(review, today)
    if reasons:
        raise RefusedError("; ".join(reasons))
    certificate = issue_certificate(
        review.aircraft, staff=review.staff, issued_on=today, airframe_hours=review.airframe_hours
    )
    review.certificate = certificate
    review.save(update_fields=["certificate"])
    return certificate
