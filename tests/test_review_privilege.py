"""Airworthiness review is for an organisation whose approval gives the privilege.

Independent review of 24 November 2026, finding 10: nothing checked the
approvals or the privileges an organisation holds, so an organisation
holding Part-CAMO and Part-145, with no privilege recorded, could record
review staff and issue a certificate on pages that cite CAO.A.045.

CAO.A.095(c) gives a Part-CAO the airworthiness review privilege. The
privileges of a Part-CAMO are not recorded until a later phase, so until
then the review pages and actions are for a Part-CAO whose approval
includes airworthiness review, and for no other organisation.
"""

from datetime import date
from decimal import Decimal

import pytest

from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.customers import services as customer_services
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import (
    Approval,
    ApprovalType,
    Organisation,
    Privilege,
)
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.models import Certificate, Review, ReviewStaff
from airworthiness_rules.intervals import Reading
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    add_sample_fleet,
    add_sample_reviews,
    get,
    make_sample,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db

REASON = (
    "Airworthiness Review Is for an Organisation Holding Part-CAO "
    "with the Airworthiness Review Privilege, CAO.A.095(c)"
)


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


def organisation(
    approval: ApprovalType,
    privileges: list[Privilege],
    other: list[tuple[ApprovalType, str]],
    name: str = "name",
) -> tuple[Organisation, User, Aircraft]:
    """An organisation whose one user holds every role, and one aircraft of its own."""
    with as_owner():
        theirs, user = provision_organisation(
            name="[Another Organisation]",
            approval_type=approval,
            approval_reference="UK.[Approval].[Number]",
            other_approvals=other,
            address="[Another Address]",
            privileges=privileges,
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username=f"{name}@another-organisation.example",
            first_user_full_name="[Another Name]",
        )
    with working_for(theirs.id, user.id):
        User.objects.filter(pk=user.pk).update(roles=list(Role.values))
        user.refresh_from_db()
        aircraft = aircraft_services.add_aircraft(
            organisation=theirs,
            registration="G-JNOP",
            type_rating="Piper PA-28 Series (Lycoming)",
            customer=customer_services.add_customer(organisation=theirs, name="[Operator Name]"),
            airframe=Reading(TODAY, Decimal("2406.5"), 0),
        )
    return theirs, user, aircraft


Kind = tuple[ApprovalType, list[Privilege], list[tuple[ApprovalType, str]]]
CAMO_AND_145: Kind = (ApprovalType.PART_CAMO, [], [(ApprovalType.PART_145, "UK.145.[Number]")])
CAO_WITHOUT_REVIEW: Kind = (
    ApprovalType.PART_CAO,
    [Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT],
    [],
)


def test_review_is_open_to_a_part_cao_with_the_privilege_and_to_no_other() -> None:
    """CAO.A.095(c). SampleData.md: the first organisation holds every privilege of a
    Part-CAO; the second holds Part-CAMO and Part-145 and has none recorded."""
    sample = make_sample()
    with working_for(sample.ours.id, sample.reader.id):
        assert approvals.review_refusal(Organisation.objects.get(pk=sample.ours.pk)) == ""
    # A Part-CAO that manages and does not review.
    managing, manager, _ = organisation(*CAO_WITHOUT_REVIEW, name="managing")
    with working_for(managing.id, manager.id):
        assert approvals.review_refusal(managing) == REASON
    theirs, user, _ = organisation(*CAMO_AND_145)
    with working_for(theirs.id, user.id):
        assert approvals.review_refusal(theirs) == REASON
        # Recording Part-CAO as held does not give its privileges: only
        # Airworthiness Limited sets those (REQ-004).
        approvals.record(theirs, approval=ApprovalType.PART_CAO, reference="UK.CAO.[Number]")
        assert approvals.review_refusal(Organisation.objects.get(pk=theirs.pk)) == REASON


def test_a_part_cao_that_no_longer_holds_the_approval_is_refused() -> None:
    """The privilege is of the approval: with Part-CAO ended, nothing gives it."""
    theirs, user, _ = organisation(
        ApprovalType.PART_CAMO, [], [(ApprovalType.PART_CAO, "UK.CAO.[Number]")]
    )
    with as_owner(), working_for(theirs.id):
        Organisation.objects.filter(pk=theirs.pk).update(
            privileges=[
                Privilege.CONTINUING_AIRWORTHINESS_MANAGEMENT,
                Privilege.AIRWORTHINESS_REVIEW,
            ]
        )
    with working_for(theirs.id, user.id):
        theirs.refresh_from_db()
        assert approvals.review_refusal(theirs) == ""
        approvals.end(Approval.objects.get(approval=ApprovalType.PART_CAO), on=TODAY)
        assert approvals.review_refusal(theirs) == REASON


@pytest.mark.parametrize("kind", [CAMO_AND_145, CAO_WITHOUT_REVIEW])
def test_every_review_action_is_refused_on_the_server_with_the_reason_and_logged(
    kind: Kind,
) -> None:
    """Finding 10. The user holds every role, so nothing but the approval refuses."""
    theirs, user, aircraft = organisation(*kind)
    client = signed_in(user)
    nothing = "00000000-0000-4000-8000-000000000000"
    actions = [
        ("/review-staff/add/", {"user": str(user.id), "authorisation_reference": "[Reference]",
                                "accepted_on": "2023-06-09"}),
        (f"/review-staff/{nothing}/involvement/", {"months_involved": "12"}),
        (f"/review-staff/{nothing}/restoration/", {"on": "2026-11-18", "under": "[Name]"}),
        (f"/aircraft/{aircraft.id}/review/certificates/", {
            "reference": "[Certificate Reference]", "issued_on": "2026-06-01",
            "valid_to": "2027-06-01", "issued_elsewhere_by": "Civil Aviation Authority"}),
        (f"/aircraft/{aircraft.id}/review/start/", {}),
        (f"/reviews/{nothing}/details/", {}),
        (f"/reviews/{nothing}/issue/", {}),
        (f"/review-items/{nothing}/", {}),
        (f"/review-items/{nothing}/close/", {}),
        (f"/certificates/{nothing}/void/", {"reason": "[Reason]"}),
        (f"/certificates/{nothing}/extend/", {}),
        (f"/certificates/{nothing}/copy-sent/", {"on": "2026-11-18"}),
        (f"/extensions/{nothing}/copy-sent/", {"on": "2026-11-18"}),
    ]  # fmt: skip
    for path, values in actions:
        response = post(client, path, **values)
        assert response.status_code == 403, path
        assert f'<p role="alert">{REASON}</p>' in response.content.decode(), path
    with working_for(theirs.id, user.id):
        assert not ReviewStaff.objects.exists()
        assert not Certificate.objects.exists()
        assert not Review.objects.exists()
        logged = list(AccessEntry.objects.filter(user=user, kind="Action Refused"))
    assert len(logged) == len(actions)
    assert {entry.detail for entry in logged} == {
        "Airworthiness Review Without the Privilege, CAO.A.095(c)"
    }


@pytest.mark.parametrize("kind", [CAMO_AND_145, CAO_WITHOUT_REVIEW])
def test_the_review_pages_say_why_and_offer_nothing(
    kind: Kind,
) -> None:
    """Finding 10. A page is still read: it says the reason and shows no form."""
    _, user, aircraft = organisation(*kind)
    client = signed_in(user)
    for path in ("/review-staff/", "/reviews/", f"/aircraft/{aircraft.id}/review/"):
        response = get(client, path)
        assert response.status_code == 200, path
        body = response.content.decode()
        assert f'<p role="alert">{REASON}</p>' in body, path
        main = body[body.index("<main") :]
        assert "<form" not in main and "<button" not in main, path
        assert "CAO.A.045" not in main, path


def test_the_services_refuse_too_whatever_the_page_does() -> None:
    """Finding 10. The same check below the pages."""
    theirs, user, aircraft = organisation(*CAMO_AND_145)
    with working_for(theirs.id, user.id):
        with pytest.raises(services.RefusedError, match=r"CAO\.A\.095"):
            services.add_review_staff(
                user=user, authorisation_reference="[Reference]", accepted_on=date(2023, 6, 9)
            )
        with pytest.raises(services.RefusedError, match=r"CAO\.A\.095"):
            services.record_certificate(
                aircraft,
                reference="[Certificate Reference]",
                issued_on=date(2026, 6, 1),
                valid_to=date(2027, 6, 1),
                issued_elsewhere_by="Civil Aviation Authority",
            )
        assert not ReviewStaff.objects.exists() and not Certificate.objects.exists()


def test_an_organisation_with_the_privilege_is_offered_the_pages_as_before() -> None:
    """The sample organisation: Part-CAO, every privilege of CAO.A.095."""
    sample = make_sample()
    fleet = add_sample_fleet(sample)
    add_sample_reviews(sample, fleet)
    client = signed_in(sample.lucy)
    for path in ("/review-staff/", "/reviews/", f"/aircraft/{fleet['G-ABCD'].id}/review/"):
        body = get(client, path).content.decode()
        assert REASON not in body, path
    assert "<form" in get(client, f"/aircraft/{fleet['G-ABCD'].id}/review/").content.decode()
    started = post(client, f"/aircraft/{fleet['G-ABCD'].id}/review/start/")
    assert started.status_code == 302
