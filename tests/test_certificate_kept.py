"""An issued certificate keeps what it showed when it was issued (REQ-110).

Independent review of 24 November 2026, finding 1: the certificate page read
the organisation's name and address and the signatory's name as they stood
on the day the page was opened, so the Administrator could change what an
issued certificate showed. Decisions.md, Roles and Permissions: the
Administrator does not change airworthiness records.

The certificates and people are those of design-system/SampleData.md.
Today in the sample world is 18 November 2026.
"""

from datetime import date

import pytest
from django.db import DatabaseError, connection, transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.organisations import configuration
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.people import services as people_services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews import sql as reviews_sql
from airworthiness_plus.reviews.models import Certificate, Extension, ReviewStaff
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    SampleReviews,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    page,
    signed_in,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    return fleet


@pytest.fixture
def reviews(sample: Sample, fleet: dict[str, Aircraft]) -> SampleReviews:
    return add_sample_reviews(sample, fleet)


def form_15c(body: str) -> str:
    """Return the part of the certificate page that is the certificate."""
    start = body.index("<h1>Airworthiness Review Certificate</h1>")
    return body[start : body.index('<p><a href="/aircraft/', start)]


def extend_ejkl(sample: Sample, fleet: dict[str, Aircraft]) -> Extension:
    """Extend the certificate of G-EJKL, issued elsewhere, as Lucy Grant."""
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.current_certificate(fleet["G-EJKL"])
        assert certificate is not None
        return services.extend_certificate(
            certificate,
            extended_by=sample.lucy,
            managed_for_12_months=True,
            maintained_by_approved_organisations=True,
            no_evidence_not_airworthy=True,
        )


def rename_everything(sample: Sample, address: str = "") -> None:
    """As the Administrator: another name and address for the organisation, and
    another name for Lucy Grant."""
    with working_for(sample.ours.id, sample.administrator.id):
        configuration.change_details(
            Organisation.objects.get(pk=sample.ours.pk),
            name="[Another Organisation]",
            address=address,
        )
        person = Person.objects.get(user=sample.lucy)
        people_services.change_person(
            person,
            full_name="[Another Person]",
            role=person.role,
            staff_group=StaffGroup(person.staff_group),
            reports_to=person.reports_to,
            employment=Employment(person.employment),
            licence=person.licence,
            joined_on=person.joined_on,
            left_on=None,
        )


def test_an_issued_certificate_keeps_what_it_showed_when_it_was_issued(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110. The certificate of G-CDEF, and the extension of G-EJKL's, say after
    the organisation and the person are renamed what they said before. Issue
    refuses an organisation with no address; the address cannot be taken off
    the certificate afterwards."""
    client = signed_in(sample.reader)
    extension = extend_ejkl(sample, fleet)
    issued = form_15c(page(client, f"/certificates/{reviews.cdef.id}/"))
    for text in (
        "<dt>Issued By</dt><dd>[Your Organisation], [Organisation Address], UK.CAO.[Number]</dd>",
        "<dt>Airworthiness Review Staff</dt><dd>Lucy Grant</dd>",
    ):
        assert text in issued, text
    extended = form_15c(page(client, f"/certificates/{extension.certificate_id}/"))
    for text in (
        "<dt>Extended By</dt><dd>Lucy Grant</dd>",
        "<dt>Company Name</dt><dd>[Your Organisation]</dd>",
        "<dt>Approval Reference</dt><dd>UK.CAO.[Number]</dd>",
    ):
        assert text in extended, text
    listed = page(client, f"/aircraft/{fleet['G-CDEF'].id}/review/")
    assert "<td>Lucy Grant, [Authorisation Reference 1]</td>" in listed

    rename_everything(sample)
    assert "[Another Person]" in page(client, "/staff/")
    assert "[Another Organisation]" in page(client, "/settings/")
    assert form_15c(page(client, f"/certificates/{reviews.cdef.id}/")) == issued
    assert form_15c(page(client, f"/certificates/{extension.certificate_id}/")) == extended
    # The list of an aircraft's certificates names who signed each, as each says.
    again = page(client, f"/aircraft/{fleet['G-CDEF'].id}/review/")
    assert "<td>Lucy Grant, [Authorisation Reference 1]</td>" in again
    assert "<td>Lucy Grant</td>" in page(client, f"/aircraft/{fleet['G-EJKL'].id}/review/")


def test_a_certificate_issued_after_a_change_says_what_is_so_on_its_day(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110. What is kept is what was so on the day of issue, not on an earlier day."""
    rename_everything(sample, address="[Another Address]")
    with working_for(sample.ours.id, sample.lucy.id):
        later = services.issue_certificate(
            Aircraft.objects.get(pk=fleet["G-EJKL"].pk),
            staff=ReviewStaff.objects.get(pk=reviews.lucy.pk),
            issued_on=TODAY,
        )
    after = form_15c(page(signed_in(sample.reader), f"/certificates/{later.id}/"))
    assert "<dd>[Another Organisation], [Another Address], UK.CAO.[Number]</dd>" in after
    assert "<dt>Airworthiness Review Staff</dt><dd>[Another Person]</dd>" in after


def test_the_database_never_lets_what_a_certificate_showed_be_altered(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110. Whatever the application does."""
    extension = extend_ejkl(sample, fleet)
    with working_for(sample.ours.id, sample.lucy.id):
        for field in (
            "organisation_name",
            "organisation_address",
            "organisation_approval_reference",
            "review_staff_name",
        ):
            with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
                Certificate.objects.filter(pk=reviews.cdef.pk).update(**{field: "[Altered]"})
        for field in ("extended_by_name", "organisation_name", "organisation_approval_reference"):
            with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
                Extension.objects.filter(pk=extension.pk).update(**{field: "[Altered]"})
        # Whatever the application sends, the database writes what the records say.
        direct = Certificate.objects.create(
            organisation_id=sample.ours.id,
            aircraft=fleet["G-EJKL"],
            issued_on=TODAY,
            valid_to=date(2027, 11, 18),
            issued_by=reviews.lucy,
            organisation_name="[Altered]",
            review_staff_name="[Altered]",
        )
        direct.refresh_from_db()
        assert (
            direct.organisation_name,
            direct.organisation_address,
            direct.organisation_approval_reference,
            direct.review_staff_name,
        ) == ("[Your Organisation]", "[Organisation Address]", "UK.CAO.[Number]", "Lucy Grant")
        again = Extension.objects.create(
            organisation_id=sample.ours.id,
            certificate_id=direct.pk,
            extended_on=TODAY,
            valid_to=date(2028, 11, 18),
            extended_by=sample.reviewer,
            extended_by_name="[Altered]",
            managed_for_12_months=True,
            maintained_by_approved_organisations=True,
            no_evidence_not_airworthy=True,
        )
        again.refresh_from_db()
        assert (
            again.extended_by_name,
            again.organisation_name,
            again.organisation_approval_reference,
        ) == ("[Review Name]", "[Your Organisation]", "UK.CAO.[Number]")
        # One recorded as issued elsewhere cannot be made to carry the organisation's name.
        elsewhere = Certificate.objects.create(
            organisation_id=sample.ours.id,
            aircraft=fleet["G-ABCD"],
            reference="[Another Reference]",
            issued_on=date(2025, 1, 1),
            valid_to=date(2026, 1, 1),
            issued_elsewhere_by="[Another Issuer]",
            organisation_name="[Altered]",
            review_staff_name="[Altered]",
        )
        elsewhere.refresh_from_db()
        assert (elsewhere.organisation_name, elsewhere.review_staff_name) == ("", "")


def test_certificates_from_before_are_given_what_they_show_by_the_migration(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """Reviews 0007. A certificate issued before what it shows was kept is given the
    names as they stand on the day of the migration. The entry this writes in
    its history says that the database role did it, and what it set."""
    extension = extend_ejkl(sample, fleet)
    with as_owner(), connection.cursor() as cursor:
        # As the tables were before the migration: nothing kept.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED")
        cursor.execute(
            "ALTER TABLE reviews_certificate DISABLE TRIGGER certificate_fixed;"
            "ALTER TABLE reviews_extension DISABLE TRIGGER extension_fixed;"
            "ALTER TABLE reviews_certificate DROP CONSTRAINT "
            "certificate_issued_here_keeps_what_it_showed;"
            "ALTER TABLE reviews_extension DROP CONSTRAINT extension_keeps_what_it_showed;"
        )
        cursor.execute(
            for_each_organisation(
                """
        UPDATE reviews_certificate SET organisation_name = '', organisation_address = '',
               organisation_approval_reference = '', review_staff_name = ''
         WHERE organisation_id = organisation;
        UPDATE reviews_extension SET organisation_name = '', extended_by_name = '',
               organisation_approval_reference = ''
         WHERE organisation_id = organisation;
"""
            )
        )
    rename_everything(sample)
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(for_each_organisation(reviews_sql.KEEP_WHAT_EACH_SHOWED))
        cursor.execute(
            "ALTER TABLE reviews_certificate ENABLE TRIGGER certificate_fixed;"
            "ALTER TABLE reviews_extension ENABLE TRIGGER extension_fixed;"
        )
    with working_for(sample.ours.id, sample.reader.id):
        cdef = Certificate.objects.get(pk=reviews.cdef.pk)
        assert (
            cdef.organisation_name,
            cdef.organisation_address,
            cdef.organisation_approval_reference,
            cdef.review_staff_name,
        ) == ("[Another Organisation]", "", "UK.CAO.[Number]", "[Another Person]")
        extended = Extension.objects.get(pk=extension.pk)
        assert (
            extended.organisation_name,
            extended.organisation_approval_reference,
            extended.extended_by_name,
        ) == ("[Another Organisation]", "UK.CAO.[Number]", "[Another Person]")
        elsewhere = Certificate.objects.get(pk=extension.certificate_id)
        assert (elsewhere.organisation_name, elsewhere.review_staff_name) == ("", "")
        entry = Event.of(cdef).last()
        assert entry is not None
        assert entry.actor_id is None and entry.actor_name.startswith("Database Role ")
        assert entry.changed == [
            "organisation_approval_reference",
            "organisation_name",
            "review_staff_name",
        ]
    # Run again, it changes nothing: what a certificate shows is set once.
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(for_each_organisation(reviews_sql.KEEP_WHAT_EACH_SHOWED))
    with working_for(sample.ours.id, sample.reader.id):
        assert Event.of(cdef).last() == entry
