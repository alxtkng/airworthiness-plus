"""What can be done with person records. Views check the role first."""

from dataclasses import dataclass
from datetime import date

from django.db import transaction

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.interface import formatting
from airworthiness_plus.interface.working import Working
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_rules.personnel import Retention, record_kept_until


class RefusedError(ValueError):
    """What was asked for does not agree with the records."""


def person_for(user: User) -> Person:
    """Give a new sign-in its person record (REQ-204).

    A person of the organisation with exactly the sign-in's name, no
    sign-in and no leaving date is taken to be the same person, when there
    is one and only one. Otherwise a person record is made.
    """
    same_name = list(
        Person.objects.filter(
            organisation_id=user.organisation_id,
            full_name=user.full_name,
            user__isnull=True,
            left_on__isnull=True,
        )[:2]
    )
    if len(same_name) == 1:
        person = same_name[0]
        person.user = user
        person.save(update_fields=["user"])
        return person
    return Person.objects.create(
        organisation_id=user.organisation_id, user=user, full_name=user.full_name
    )


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
) -> None:
    """Change what is recorded of a person. Every change is in the history (REQ-203).

    The name of a person with a sign-in is the name of the sign-in, so the
    two are changed together. A person whose sign-in is active has not
    left: the sign-in is made inactive on the Users page first (REQ-010).
    """
    organisation = Organisation.objects.get(pk=person.organisation_id)
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
        raise RefusedError("A Person with an Active Sign-In Has Not Left")
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


@dataclass(frozen=True)
class FormerLine:
    """A person who has left, and how long their record is kept (REQ-205, REQ-206)."""

    person: Person
    kept: Retention | None

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
                ("Staff Group", str(self.person.staff_group)),
            ),
            source=self.kept.source,
        )


@dataclass(frozen=True)
class Staff:
    """Everyone of an organisation: those here now, and those who have left."""

    current: list[Person]
    former: list[FormerLine]


def staff(organisation: Organisation) -> Staff:
    """Return the people of ``organisation`` (REQ-205)."""
    held = approvals.types_held(organisation)
    people = list(Person.objects.select_related("reports_to", "user"))
    former = [
        FormerLine(
            person,
            record_kept_until(
                person.left_on,
                approvals=held,
                review_staff=person.staff_group == StaffGroup.REVIEW,
            ),
        )
        for person in people
        if person.left_on is not None
    ]
    return Staff([person for person in people if person.left_on is None], former)
