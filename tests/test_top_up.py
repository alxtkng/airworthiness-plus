"""The test site's top-up adds what is missing, once, and changes nothing (REQ-218).

Independent review of 24 November 2026, finding 3. At every start the test
site gives a sample seeded before person records the people it lacks
(``operations/test-site.md``). The top-up found people by name and
completed any record that said little, so once anyone had edited a person
it changed and duplicated people: a person renamed was added again at
every start, a reporting line taken off was put back past the check for
circles, and an edit was wiped.

It now adds the people once, records that it has, and after that does
nothing. Nobody is found by name. The people are those of
design-system/SampleData.md.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from django.db import DatabaseError, connection, transaction

from airworthiness_plus.accounts import users
from airworthiness_plus.accounts.models import User
from airworthiness_plus.accounts.roles import Role
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import APPLICATION_ROLE
from airworthiness_plus.organisations.models import Organisation, Privilege
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.people import services
from airworthiness_plus.people.models import Employment, Person, StaffGroup
from airworthiness_plus.sample import build
from airworthiness_plus.sample.management.commands import prepare_test_site
from airworthiness_plus.sample.management.commands.seed_sample_organisation import ADMINISTRATOR
from airworthiness_plus.sample.models import Added
from tests.conftest import as_owner, as_owner_who_is_not_a_superuser
from tests.support import TODAY, Sample, make_sample

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def sample_day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


def state(organisation: Organisation, user: User) -> tuple[list[Any], int]:
    """Return every person of the organisation as recorded, and how many history entries."""
    with working_for(organisation.id, user.id):
        people = [
            (
                one.pk,
                one.full_name,
                one.role,
                one.staff_group,
                one.reports_to_id,
                one.employment,
                one.licence,
                one.joined_on,
                one.left_on,
                one.user_id,
            )
            for one in Person.objects.order_by("id")
        ]
        return people, Event.objects.count()


def change(sample: Sample, name: str, **values: object) -> None:
    """Change one person on the Staff page's own service, as the Administrator."""
    with working_for(sample.ours.id, sample.administrator.id):
        one = Person.objects.get(full_name=name)
        current: dict[str, object] = {
            "full_name": one.full_name,
            "role": one.role,
            "staff_group": StaffGroup(one.staff_group),
            "reports_to": one.reports_to,
            "employment": Employment(one.employment),
            "licence": one.licence,
            "joined_on": one.joined_on,
            "left_on": one.left_on,
        }
        services.change_person(one, by=sample.administrator, **{**current, **values})  # type: ignore[arg-type]


def edit_as_the_review_did(sample: Sample) -> None:
    """The edits of the independent review: Lucy Grant reports to nobody, the manager
    reports to Lucy Grant, Chris Moore is renamed, the Read Only person is given
    details, and the Accountable Manager's role is taken off."""
    change(sample, "Lucy Grant", reports_to=None)
    with working_for(sample.ours.id, sample.administrator.id):
        lucy = Person.objects.get(full_name="Lucy Grant")
    change(sample, "[Continuing Airworthiness Manager]", reports_to=lucy)
    change(sample, "Chris Moore", full_name="[Chris Moore Renamed]")
    change(sample, "[Read Only Name]", role="Auditor", licence="[Licence]")
    change(sample, "[Accountable Manager]", role="")


def test_a_top_up_after_people_were_edited_changes_and_adds_nothing() -> None:
    """Finding 3. Every edit of the review, then the top-up, twice: 15 people before
    and after, each exactly as edited, and not one entry more in the history."""
    sample = make_sample()
    edit_as_the_review_did(sample)
    before = state(sample.ours, sample.administrator)
    assert len(before[0]) == 15
    for _ in range(2):
        assert prepare_test_site.complete_the_people(sample.administrator) == 0
        assert state(sample.ours, sample.administrator) == before
    with working_for(sample.ours.id, sample.reader.id):
        # No Chris Moore was added again, and no circle was written.
        assert not Person.objects.filter(full_name="Chris Moore").exists()
        lucy = Person.objects.get(full_name="Lucy Grant")
        assert lucy.reports_to is None
        assert Person.objects.get(full_name="[Read Only Name]").role == "Auditor"


def test_a_sample_given_its_people_before_the_record_was_kept_is_taken_as_done() -> None:
    """Finding 3. The test site of 24 November 2026: people added by the first top-up,
    and no record that it had run. After edits, the next start records that the
    people were added and adds and changes nobody, whatever was renamed."""
    sample = make_sample()
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE; SET CONSTRAINTS ALL DEFERRED")
        cursor.execute("ALTER TABLE sample_added DISABLE TRIGGER history_refuse_delete")
        cursor.execute("DELETE FROM sample_added")
        cursor.execute("ALTER TABLE sample_added ENABLE TRIGGER history_refuse_delete")
    edit_as_the_review_did(sample)
    people, entries = state(sample.ours, sample.administrator)
    assert prepare_test_site.complete_the_people(sample.administrator) == 0
    after, entries_after = state(sample.ours, sample.administrator)
    assert after == people
    # One entry more: the record that the people of the sample have been added.
    assert entries_after == entries + 1
    with working_for(sample.ours.id, sample.reader.id):
        assert [one.part for one in Added.objects.all()] == ["People"]
    assert prepare_test_site.complete_the_people(sample.administrator) == 0
    assert state(sample.ours, sample.administrator) == (after, entries_after)


@contextmanager
def seeded_before_person_records() -> Iterator[tuple[Organisation, User]]:
    """The first organisation as the database of 20 November 2026 held it after the
    migration: its five sign-ins, each with a person record that says a name alone."""
    with as_owner():
        ours, administrator = provision_organisation(
            name=build.NAME,
            approval_reference=build.APPROVAL_REFERENCE,
            address=build.ADDRESS,
            privileges=list(Privilege),
            scope_of_work=build.SCOPE,
            first_user_username=ADMINISTRATOR,
            first_user_full_name="[Accountable Manager]",
        )
    with working_for(ours.id, administrator.id):
        for name, username in build.SIGN_INS.items():
            if username != ADMINISTRATOR:
                User.objects.create_user(organisation=ours, username=username, full_name=name)
    yield ours, administrator


def test_a_sample_seeded_before_person_records_is_given_its_people_once() -> None:
    """REQ-218. 10 people with no sign-in are added and the 5 records of the sample's
    sign-ins, known by their user names, are completed. A namesake of a sample
    person is not taken for them: a Read Only user named Sam Patel, added before
    the migration, stays a person of their own and is given nothing (finding 4)."""
    with seeded_before_person_records() as (ours, administrator):
        with working_for(ours.id, administrator.id):
            namesake = users.add_user(
                organisation=ours,
                username="sam.patel@your-organisation.example",
                full_name="Sam Patel",
                roles=[Role.READ_ONLY],
                password=users.new_first_password(),
            )
            assert Person.objects.count() == 6
        assert prepare_test_site.complete_the_people(administrator) == 10
        with working_for(ours.id, administrator.id):
            assert Person.objects.count() == 16
            theirs = Person.objects.get(user=namesake)
            assert (theirs.role, theirs.licence, theirs.reports_to) == ("", "", None)
            sams = Person.objects.filter(full_name="Sam Patel")
            assert sams.count() == 2
            sample_sam = sams.get(user__isnull=True)
            assert (sample_sam.role, sample_sam.licence) == ("Certifying Staff", "Part-66 B1.2")
            lucy = Person.objects.get(user__username="lucy.grant@your-organisation.example")
            assert (lucy.role, lucy.staff_group) == (
                "Airworthiness Review Staff",
                "Airworthiness Review Staff",
            )
            assert lucy.reports_to is not None
            assert lucy.reports_to.full_name == "[Continuing Airworthiness Manager]"
            reader = Person.objects.get(user__username="reader@your-organisation.example")
            assert (reader.role, reader.reports_to) == ("", None)
            former = Person.objects.get(full_name="[Former Review Name]")
            assert (former.left_on, former.reports_to) == (build.PEOPLE[-1][7], None)
            assert chain.problems(list(Event.objects.all())) == []
        once = state(ours, administrator)
        assert prepare_test_site.complete_the_people(administrator) == 0
        assert state(ours, administrator) == once


def test_a_sign_in_whose_record_says_more_than_a_name_is_left_as_it_is() -> None:
    """Finding 3. Where the record of a sample sign-in has been filled in by hand before
    the people are added, it is not written over: the top-up completes only a
    record that still says a name and nothing else."""
    with seeded_before_person_records() as (ours, administrator):
        with working_for(ours.id, administrator.id):
            lucy = Person.objects.get(user__username="lucy.grant@your-organisation.example")
            services.change_person(
                lucy,
                full_name="[Lucy Grant Renamed]",
                role="[A Role Typed by Hand]",
                staff_group=StaffGroup.MANAGEMENT,
                reports_to=None,
                employment=Employment.CONTRACTED,
                licence="",
                joined_on=None,
                left_on=None,
                by=administrator,
            )
            before = Event.of(lucy).count()
        assert prepare_test_site.complete_the_people(administrator) == 10
        with working_for(ours.id, administrator.id):
            after = Person.objects.get(pk=lucy.pk)
            assert (after.full_name, after.role, after.staff_group, after.employment) == (
                "[Lucy Grant Renamed]",
                "[A Role Typed by Hand]",
                "Management",
                "Contracted",
            )
            assert after.reports_to is None
            assert Event.of(after).count() == before
            assert not Person.objects.filter(full_name="Lucy Grant").exists()


def test_the_record_that_the_people_were_added_is_never_changed_or_made_twice() -> None:
    """REQ-218. The database holds it: added once for an organisation, never altered."""
    sample = make_sample()
    with working_for(sample.ours.id, sample.administrator.id):
        added = Added.objects.get()
        with pytest.raises(DatabaseError), transaction.atomic():
            Added.objects.filter(pk=added.pk).update(part="Fleet")
        with pytest.raises(DatabaseError, match="sample_part_added_once"), transaction.atomic():
            Added.objects.create(organisation=sample.ours, part="People")
    with working_for(sample.other.id, sample.stranger.id):
        assert not Added.objects.exists()


def test_the_top_up_runs_as_an_owner_of_the_tables_who_is_not_a_superuser() -> None:
    """The test site's owner is not a superuser, and row-level security holds it as it
    holds the application (ADR-0002). Every other test of the owner's work runs
    as a superuser, whom it never holds. Here the top-up is run as the owner of
    every table with no power beyond that, on a sample seeded before person
    records, and then again after an edit."""
    with seeded_before_person_records() as (ours, administrator):
        with as_owner_who_is_not_a_superuser():
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user"
                )
                assert cursor.fetchone() == (False,)
                # Held by row-level security: with no organisation set, nothing is seen.
                cursor.execute("SELECT count(*) FROM people_person")
                assert cursor.fetchone() == (0,)
            found = prepare_test_site.administrator_named(ADMINISTRATOR)
            assert found is not None and found.pk == administrator.pk
            assert prepare_test_site.complete_the_people(found) == 10
            assert prepare_test_site.complete_the_people(found) == 0
        with working_for(ours.id, administrator.id):
            assert Person.objects.count() == 15
            made = Person.objects.get(full_name="Chris Moore")
            entry = Event.of(made).get()
            # The owner's work is recorded against the database role (REQ-004).
            assert entry.actor_id is None and entry.actor_name.startswith("Database Role ")
            with connection.cursor() as cursor:
                cursor.execute("SELECT current_user")
                assert cursor.fetchone() == (APPLICATION_ROLE,)
        change_name = "[Chris Moore Renamed]"
        with working_for(ours.id, administrator.id):
            services.change_person(
                made,
                full_name=change_name,
                role=made.role,
                staff_group=StaffGroup(made.staff_group),
                reports_to=made.reports_to,
                employment=Employment(made.employment),
                licence=made.licence,
                joined_on=None,
                left_on=None,
                by=administrator,
            )
        before = state(ours, administrator)
        with as_owner_who_is_not_a_superuser():
            found = prepare_test_site.administrator_named(ADMINISTRATOR)
            assert found is not None
            assert prepare_test_site.complete_the_people(found) == 0
        assert state(ours, administrator) == before
