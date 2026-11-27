"""What can be done with person records. Views check the role first."""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Value
from django.db.models.functions import Lower

from airworthiness_plus.accounts import users
from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history.models import Event
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import (
    Employment,
    ExperienceEvidence,
    ExperienceKind,
    ExperienceWithdrawal,
    MaintenanceAuthorisation,
    Person,
    RecurrentTraining,
    StaffGroup,
)
from airworthiness_plus.reviews.models import ReviewStaff
from airworthiness_rules.dates import add_days
from airworthiness_rules.maintenance_experience import (
    DaysOfExperience,
    ExperienceDuration,
    duration,
)
from airworthiness_rules.personnel import Retention, record_kept_until


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def person_for(user: User, person: Person | None = None) -> Person:
    """Give a new sign-in its person record (REQ-204).

    A person record is made for it, named as the sign-in is. Nothing is
    joined by name: two people may share one, and a sign-in joined to the
    wrong person would be given that person's record (independent review
    of 24 November 2026, finding 4). The sign-in is given to a person
    already recorded only when that person is chosen: one of the same
    organisation, who has no sign-in and has not left.
    """
    if person is None:
        return Person.objects.create(
            organisation_id=user.organisation_id, user=user, full_name=user.full_name
        )
    # Read again under a lock, so that two sign-ins cannot be given one person.
    chosen = Person.objects.select_for_update().filter(pk=person.pk).first()
    if chosen is None or chosen.organisation_id != user.organisation_id:
        raise RefusedError("The Person Chosen Is a Person of the Same Organisation")
    if chosen.user_id is not None:
        raise RefusedError("The Person Chosen Already Has a Sign-In")
    if chosen.left_on is not None:
        raise RefusedError("A Person Recorded as Having Left Is Not Given a Sign-In")
    if chosen.full_name != user.full_name:
        raise RefusedError("A Sign-In Has the Name of Its Person")
    chosen.user = user
    chosen.save(update_fields=["user"])
    return chosen


def _checked(
    organisation: Organisation,
    *,
    full_name: str,
    reports_to: Person | None,
    joined_on: date | None,
    left_on: date | None,
    person: Person | None = None,
) -> str:
    full_name = full_name.strip()
    if not full_name:
        raise RefusedError("A Person Has a Name")
    today = aircraft_services.today()
    if joined_on is not None and joined_on > today:
        raise RefusedError("Joined Is Not After Today")
    if left_on is not None and left_on > today:
        raise RefusedError("Left Is Not After Today")
    if joined_on is not None and left_on is not None and left_on < joined_on:
        raise RefusedError("A Person Does Not Leave Before Joining")
    if reports_to is not None:
        if reports_to.organisation_id != organisation.id:
            raise RefusedError("A Person Reports to a Person of the Same Organisation")
        # Start from the stored manager, so a form read before another edit is safe.
        reports_to = Person.objects.get(pk=reports_to.pk)
        # Up the chain from the person reported to: it must not come back round.
        seen = {person.pk} if person is not None else set()
        above: Person | None = reports_to
        while above is not None:
            if above.pk in seen:
                raise RefusedError("A Chain of Reporting Does Not Come Back to Where It Began")
            seen.add(above.pk)
            above = above.reports_to
    return full_name


@transaction.atomic
def add_person(
    *,
    organisation: Organisation,
    full_name: str,
    role: str = "",
    staff_group: StaffGroup = StaffGroup.OTHER,
    reports_to: Person | None = None,
    employment: Employment = Employment.EMPLOYED,
    licence: str = "",
    joined_on: date | None = None,
    left_on: date | None = None,
) -> Person:
    """Add a person who has no sign-in (REQ-203). A sign-in is given on the Users page."""
    full_name = _checked(
        organisation,
        full_name=full_name,
        reports_to=reports_to,
        joined_on=joined_on,
        left_on=left_on,
    )
    return Person.objects.create(
        organisation=organisation,
        full_name=full_name,
        role=role.strip(),
        staff_group=staff_group,
        reports_to=reports_to,
        employment=employment,
        licence=licence.strip(),
        joined_on=joined_on,
        left_on=left_on,
    )


@transaction.atomic
def change_person(
    person: Person,
    *,
    full_name: str,
    role: str,
    staff_group: StaffGroup,
    reports_to: Person | None,
    employment: Employment,
    licence: str,
    joined_on: date | None,
    left_on: date | None,
    by: User | None = None,
) -> None:
    """Change what is recorded of a person. Every change is in the history (REQ-203).

    The name of a person with a sign-in is the name of the sign-in, so the
    two are changed together; the page asks for a code first, as the Users
    page does. Recording the day a person left makes their sign-in inactive
    at once, and their sessions end (REQ-010): ``by`` is who is recording
    it, who cannot record themselves as having left. The day is recorded on
    their review staff record too, if they have one and it has none
    (independent review of 24 November 2026, findings 5 and 6).
    """
    organisation = Organisation.objects.select_for_update().get(pk=person.organisation_id)
    full_name = _checked(
        organisation,
        full_name=full_name,
        reports_to=reports_to,
        joined_on=joined_on,
        left_on=left_on,
        person=person,
    )
    user = person.user
    if left_on is not None and user is not None and user.is_active:
        try:
            users.set_active(user, active=False, by=by)
        except users.RefusedError as error:
            raise RefusedError(str(error)) from error
    person.full_name = full_name
    person.role = role.strip()
    person.staff_group = staff_group
    person.reports_to = reports_to
    person.employment = employment
    person.licence = licence.strip()
    person.joined_on = joined_on
    person.left_on = left_on
    person.save()
    if user is not None and user.full_name != full_name:
        user.full_name = full_name
        user.save(update_fields=["full_name"])
    if left_on is not None and user is not None:
        ReviewStaff.objects.filter(user=user, left_on__isnull=True).update(left_on=left_on)


@dataclass(frozen=True)
class FormerLine:
    """A person who has left, and how long their record is kept (REQ-205, REQ-206)."""

    person: Person
    kept: Retention | None
    # The approvals held on the day the person left, and whether the person
    # was ever airworthiness review staff: what the day is worked out from.
    held: tuple[str, ...] = ()
    review_staff: bool = False

    @property
    def kept_text(self) -> str:
        """Return the day and the period, as the Staff board writes them."""
        if self.kept is None:
            return "No Period Given in Part-CAO"
        return f"{formatting.long_date(self.kept.until)}, {self.kept.years} Years After Leaving"

    @property
    def working(self) -> Working | None:
        """Return how the day was worked out (REQ-139)."""
        if self.kept is None or self.person.left_on is None:
            return None
        return Working(
            title=f"How Record Kept Until Was Calculated for {self.person.full_name}",
            figure=formatting.long_date(self.kept.until),
            rule=(
                f"The Day the Person Left and {self.kept.years} Years. "
                "A Person Who Left on 29 February Is Kept Until 1 March. "
                "The System Never Deletes a Record"
            ),
            inputs=(
                ("Left", formatting.long_date(self.person.left_on)),
                ("Approvals Held on That Day", ", ".join(self.held)),
                ("Airworthiness Review Staff", "Yes" if self.review_staff else "No"),
            ),
            source=self.kept.source,
        )


@dataclass(frozen=True)
class Staff:
    """Everyone of an organisation: those here now, and those who have left."""

    current: list[Person]
    former: list[FormerLine]


def _ever_review_staff(former: list[Person]) -> set[uuid.UUID]:
    """Return which of ``former`` were ever airworthiness review staff.

    CAO.A.045(e) covers "all its airworthiness review staff": a person is
    one who has a review staff record, who is in the group now, or whose
    record ever said so. A person moved to another group, before or after
    leaving, does not lose the period (finding 6 of 24 November 2026).
    """
    ever = {person.pk for person in former if person.staff_group == StaffGroup.REVIEW}
    with_record = ReviewStaff.objects.filter(
        user__in=[person.user_id for person in former if person.user_id is not None]
    ).values_list("user_id", flat=True)
    by_user = {person.user_id: person.pk for person in former}
    ever |= {by_user[user_id] for user_id in with_record}
    # The history holds every state the record has been in (REQ-130).
    ever |= set(
        Event.objects.filter(
            record_type=Person._meta.db_table,
            record_id__in=[person.pk for person in former],
            after_json__contains=f'"staff_group": "{StaffGroup.REVIEW.value}"',
        ).values_list("record_id", flat=True)
    )
    return ever


def staff(organisation: Organisation) -> Staff:
    """Return the people of ``organisation`` (REQ-205, REQ-206).

    The day a former person's record is kept until is worked out from the
    approvals the organisation held on the day the person left, not those
    it holds today: an approval given up afterwards does not shorten it.
    """
    every = approvals.every(organisation)
    people = list(
        Person.objects.select_related("reports_to", "user__review_staff").prefetch_related(
            "maintenance_authorisations"
        )
    )
    gone = [person for person in people if person.left_on is not None]
    ever = _ever_review_staff(gone)
    former = []
    for person in gone:
        assert person.left_on is not None  # noqa: S101  filtered above
        held = tuple(one.approval for one in every if one.held_on(person.left_on))
        review_staff = person.pk in ever
        former.append(
            FormerLine(
                person,
                record_kept_until(person.left_on, approvals=set(held), review_staff=review_staff),
                held,
                review_staff,
            )
        )
    return Staff([person for person in people if person.left_on is None], former)


@dataclass
class ReportingLine:
    """A current staff member and their direct reports in the organisation chart."""

    person: Person
    reports: list["ReportingLine"] = field(default_factory=list)


def organisation_chart(
    organisation: Organisation,
) -> tuple[list[ReportingLine], list[Person], list[Person]]:
    """Build the chart from the organisation's current reporting relationships (REQ-295)."""
    people = Person.objects.filter(organisation=organisation, left_on__isnull=True).select_related(
        "reports_to"
    )
    lines = {person.pk: ReportingLine(person) for person in people}
    roots = []
    managers = []
    for line in lines.values():
        person = line.person
        if person.staff_group == StaffGroup.MANAGEMENT:
            managers.append(person)
        parent = lines.get(person.reports_to_id) if person.reports_to_id is not None else None
        if parent is None:
            roots.append(line)
        else:
            parent.reports.append(line)
    roots.sort(key=lambda line: line.person.role != "Accountable Manager")
    placed = set()
    pending = roots.copy()
    while pending:
        line = pending.pop()
        placed.add(line.person.pk)
        pending.extend(line.reports)
    unresolved = [line.person for key, line in lines.items() if key not in placed]
    return roots, managers, unresolved


@transaction.atomic
def record_maintenance_authorisation(
    person: Person, *, reference: str, scope: str, valid_from: date, valid_to: date | None = None
) -> MaintenanceAuthorisation:
    """Keep the evidence supplied by the organisation without issuing an authorisation."""
    person = Person.objects.select_for_update().get(pk=person.pk)
    if person.staff_group != StaffGroup.CERTIFYING:
        raise RefusedError("A Maintenance Authorisation Names Certifying Staff")
    if valid_to is not None and valid_to < valid_from:
        raise RefusedError("Valid To Cannot Be Before Valid From")
    if not reference.strip() or not scope.strip():
        raise RefusedError("Give the Authorisation Reference and Scope")
    if MaintenanceAuthorisation.objects.filter(
        person=person, reference=reference.strip(), valid_from=valid_from
    ).exists():
        raise RefusedError("This Authorisation Is Already Recorded")
    return MaintenanceAuthorisation.objects.create(
        organisation_id=person.organisation_id,
        person=person,
        reference=reference.strip(),
        scope=scope.strip(),
        valid_from=valid_from,
        valid_to=valid_to,
    )


@transaction.atomic
def record_recurrent_training(
    person: Person,
    *,
    subject: str,
    evidence_reference: str,
    completed_on: date,
    due_on: date | None,
) -> RecurrentTraining:
    """Record completed training without changing any earlier evidence."""
    person = Person.objects.select_for_update().get(pk=person.pk)
    subject, evidence_reference = subject.strip(), evidence_reference.strip()
    if not subject or not evidence_reference:
        raise RefusedError("Give the Training Subject and Evidence Reference")
    if completed_on > aircraft_services.today():
        raise RefusedError("Completion Cannot Be in the Future")
    if due_on is not None and due_on <= completed_on:
        raise RefusedError("Renewal Must Be Due After Completion")
    if (
        RecurrentTraining.objects.alias(subject_key=Lower("subject"))
        .filter(person=person, subject_key=Lower(Value(subject)), completed_on=completed_on)
        .exists()
    ):
        raise RefusedError("This Training Completion Is Already Recorded")
    return RecurrentTraining.objects.create(
        organisation_id=person.organisation_id,
        person=person,
        subject=subject,
        evidence_reference=evidence_reference,
        completed_on=completed_on,
        due_on=due_on,
    )


def current_recurrent_training(
    organisation: Organisation,
) -> dict[uuid.UUID, list[RecurrentTraining]]:
    """Return each current staff member's latest completion in each subject."""
    records = RecurrentTraining.objects.filter(
        organisation=organisation, person__left_on__isnull=True
    ).annotate(subject_key=Lower("subject"))
    by_person: dict[uuid.UUID, list[RecurrentTraining]] = {}
    seen: set[tuple[uuid.UUID, str]] = set()
    for course in records:
        key = (course.person_id, course.subject_key)
        if key not in seen:
            seen.add(key)
            by_person.setdefault(course.person_id, []).append(course)
    return by_person


@transaction.atomic
def record_experience_evidence(
    authorisation: MaintenanceAuthorisation,
    *,
    kind: str,
    evidence_reference: str,
    qualification_basis: str,
    starts_on: date,
    ends_on: date | None,
    days: Decimal | None,
    aircraft_type: str,
    aircraft_registration: str,
    licence_subcategory: str,
) -> ExperienceEvidence:
    """Keep the organisation's evidence assessment for one authorisation."""
    authorisation = MaintenanceAuthorisation.objects.get(pk=authorisation.pk)
    Person.objects.select_for_update().get(pk=authorisation.person_id)
    evidence_reference, qualification_basis = (
        evidence_reference.strip(),
        qualification_basis.strip(),
    )
    if not evidence_reference or not qualification_basis:
        raise RefusedError("Give the Evidence Reference and the Basis for Counting It")
    fields = (aircraft_type, aircraft_registration, licence_subcategory)
    today = aircraft_services.today()
    if starts_on > today or (ends_on is not None and ends_on > today):
        raise RefusedError("Experience Cannot Be After Today")
    if kind == ExperienceKind.EMPLOYMENT:
        if ends_on is None or ends_on < starts_on:
            raise RefusedError("Give the First and Last Days of the Employment Block")
        if days is not None or any(fields):
            raise RefusedError("Leave the Day Credit and Aircraft Fields Blank for Employment")
    elif kind in {ExperienceKind.MAINTENANCE, ExperienceKind.SUBSTITUTE}:
        if ends_on is not None:
            raise RefusedError("A Day of Experience Has One Date")
        if days is None or not days.is_finite() or not 0 < days <= 1:
            raise RefusedError("Give a Day Credit Greater Than Zero and at Most One")
        if not aircraft_type or not licence_subcategory:
            raise RefusedError("Give the Aircraft Type and Licence Category")
        if kind == ExperienceKind.MAINTENANCE and not aircraft_registration:
            raise RefusedError("Give the Aircraft Registration for Direct Maintenance")
    else:
        raise RefusedError("Choose the Evidence Type")
    previous = (
        ExperienceEvidence.objects.filter(
            authorisation=authorisation,
            evidence_reference=evidence_reference,
            replacement__isnull=True,
        )
        .select_related("withdrawal")
        .first()
    )
    if previous is not None and not hasattr(previous, "withdrawal"):
        raise RefusedError("This Evidence Reference Is Already Recorded")
    return ExperienceEvidence.objects.create(
        organisation_id=authorisation.organisation_id,
        authorisation=authorisation,
        kind=kind,
        evidence_reference=evidence_reference,
        qualification_basis=qualification_basis,
        supersedes=previous,
        starts_on=starts_on,
        ends_on=ends_on,
        days=days,
        aircraft_type=aircraft_type,
        aircraft_registration=aircraft_registration,
        licence_subcategory=licence_subcategory,
    )


def assessed_experience(evidence: Iterable[ExperienceEvidence], today: date) -> ExperienceDuration:
    """Calculate duration using only the evidence assessed for one authorisation."""
    days = []
    employment = []
    for item in evidence:
        if hasattr(item, "withdrawal"):
            continue
        if item.kind == ExperienceKind.EMPLOYMENT and item.ends_on is not None:
            employment.append((item.starts_on, add_days(item.ends_on, 1)))
        elif item.days is not None:
            days.append(
                DaysOfExperience(item.starts_on, item.days, item.kind == ExperienceKind.SUBSTITUTE)
            )
    return duration(today, days=days, employment=employment)


@transaction.atomic
def withdraw_experience_evidence(evidence: ExperienceEvidence, *, reason: str) -> None:
    """Withdraw one experience entry from the calculation while keeping its evidence."""
    Person.objects.select_for_update().get(pk=evidence.authorisation.person_id)
    if ExperienceWithdrawal.objects.filter(evidence=evidence).exists():
        raise RefusedError("This Evidence Is Already Withdrawn")
    reason = reason.strip()
    if not reason:
        raise RefusedError("Give a Reason for Withdrawing the Evidence")
    ExperienceWithdrawal.objects.create(
        organisation_id=evidence.organisation_id, evidence=evidence, reason=reason
    )


def contradicts_known_maintenance_term(person: Person, on: date) -> bool:
    """Return whether recorded maintenance terms rule out the supplied date."""
    terms = list(person.maintenance_authorisations.order_by().values_list("valid_from", "valid_to"))
    return bool(terms) and not any(
        first <= on and (last is None or on <= last) for first, last in terms
    )
