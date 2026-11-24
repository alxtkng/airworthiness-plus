"""The approvals an organisation holds (REQ-200).

Decisions.md, Canvas Build, decision 1: an organisation may hold Part-CAMO
and Part-145 as well as Part-CAO. Each approval held is a record with its
reference, and nothing is removed: an approval that ends is marked with
the day it ended.
"""

from datetime import date

import pytest
from django.db import IntegrityError, ProgrammingError, connection, transaction

from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.history.sql import for_each_organisation
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Approval, ApprovalType, Organisation
from airworthiness_plus.organisations.provisioning import provision_organisation
from airworthiness_plus.organisations.sql import APPROVAL_FOR_EACH_ORGANISATION
from tests.conftest import as_owner
from tests.support import Sample, make_sample

pytestmark = pytest.mark.django_db

EARLIER = "5f1e7d0a-0000-4000-8000-000000000001"


@pytest.fixture
def sample() -> Sample:
    return make_sample()


def held(organisation: Organisation) -> list[tuple[str, str]]:
    return [(one.approval, one.reference) for one in approvals.held(organisation)]


def test_an_organisation_is_set_up_with_the_approval_it_holds(sample: Sample) -> None:
    """REQ-200. SampleData.md, Organisation: Part-CAO, UK.CAO.[Number]."""
    with working_for(sample.ours.id, sample.administrator.id):
        assert held(sample.ours) == [("Part-CAO", "UK.CAO.[Number]")]
        first = Approval.objects.get()
        entry = Event.of(first).get()
    # Setting up is the owner's work, and is recorded against the database role (REQ-004).
    assert (entry.action, entry.actor_id) == ("Created", None)
    assert entry.actor_name.startswith("Database Role ")


def test_an_organisation_may_hold_part_camo_and_part_145_and_not_part_cao() -> None:
    """REQ-200, decision 1. SampleData.md, Second Organisation."""
    with as_owner():
        second, administrator = provision_organisation(
            name="[Second Organisation]",
            approval_type=ApprovalType.PART_CAMO,
            approval_reference="UK.CAMO.[Number]",
            other_approvals=[(ApprovalType.PART_145, "UK.145.[Number]")],
            privileges=[],
            scope_of_work="Aeroplanes 2,730 Kilograms Maximum Take-Off Mass or Less",
            first_user_username="accountable.manager@second-organisation.example",
            first_user_full_name="[Accountable Manager]",
        )
    with working_for(second.id, administrator.id):
        assert held(second) == [("Part-CAMO", "UK.CAMO.[Number]"), ("Part-145", "UK.145.[Number]")]
        assert approvals.types_held(second) == {"Part-CAMO", "Part-145"}
        assert Organisation.objects.get().approval_reference == "UK.CAMO.[Number]"


def test_the_part_cao_privileges_are_asked_only_of_an_organisation_set_up_as_part_cao(
    sample: Sample,
) -> None:
    """REQ-001, REQ-200. CAO.A.095 gives the privileges of a Part-CAO and of no other approval."""
    with (
        working_for(sample.ours.id, sample.administrator.id),
        pytest.raises(IntegrityError, match="organisation_has_known_privileges"),
        transaction.atomic(),
    ):
        Organisation.objects.filter(pk=sample.ours.pk).update(privileges=[])
    with (
        as_owner(),
        pytest.raises(IntegrityError, match="organisation_has_known_privileges"),
        transaction.atomic(),
    ):
        provision_organisation(
            name="[Second Organisation]",
            approval_type=ApprovalType.PART_CAMO,
            approval_reference="UK.CAMO.[Number]",
            privileges=["Design"],  # type: ignore[list-item]
            scope_of_work="Aeroplanes",
            first_user_username="name@second-organisation.example",
            first_user_full_name="[Name]",
        )


def test_the_administrator_records_another_approval_and_it_is_in_the_history(
    sample: Sample,
) -> None:
    """REQ-200. Who recorded it and when is in the history, as for every record."""
    with working_for(sample.ours.id, sample.administrator.id):
        added = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference=" UK.145.[Number] "
        )
        assert held(sample.ours) == [
            ("Part-CAO", "UK.CAO.[Number]"),
            ("Part-145", "UK.145.[Number]"),
        ]
        entry = Event.of(added).get()
        assert (entry.action, entry.actor_name) == ("Created", "[Accountable Manager]")
        assert chain.problems(list(Event.of(added))) == []


def test_an_approval_is_held_once_and_is_one_of_the_three(sample: Sample) -> None:
    """REQ-200. The service refuses with the reason; the database refuses whoever asks."""
    with working_for(sample.ours.id, sample.administrator.id):
        with pytest.raises(approvals.RefusedError, match="Part-CAO Is Already Recorded"):
            approvals.record(sample.ours, approval=ApprovalType.PART_CAO, reference="UK.CAO.2")
        with pytest.raises(approvals.RefusedError, match="An Approval Has Its Reference"):
            approvals.record(sample.ours, approval=ApprovalType.PART_145, reference="  ")
        with pytest.raises(IntegrityError, match="approval_held_once"), transaction.atomic():
            Approval.objects.create(
                organisation=sample.ours, approval="Part-CAO", reference="UK.CAO.2"
            )
        with pytest.raises(IntegrityError, match="approval_is_known"), transaction.atomic():
            Approval.objects.create(
                organisation=sample.ours, approval="Part-147", reference="UK.147.[Number]"
            )


def test_an_approval_that_ends_is_kept_with_the_day_it_ended(sample: Sample) -> None:
    """REQ-200, REQ-131. Nothing is removed. It can be recorded as held again."""
    with working_for(sample.ours.id, sample.administrator.id):
        added = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]"
        )
        approvals.end(added, on=date(2026, 11, 18))
        assert approvals.types_held(sample.ours) == {"Part-CAO"}
        assert Approval.objects.count() == 2
        with pytest.raises(approvals.RefusedError, match="Already Recorded as No Longer Held"):
            approvals.end(added, on=date(2026, 11, 19))
        again = approvals.record(
            sample.ours, approval=ApprovalType.PART_145, reference="UK.145.[Number]"
        )
        assert again.pk == added.pk
        assert approvals.types_held(sample.ours) == {"Part-CAO", "Part-145"}
        assert [entry.changed for entry in Event.of(added)] == [
            [],
            ["no_longer_held_on"],
            ["no_longer_held_on"],
        ]


def test_the_approval_the_organisation_was_set_up_with_is_not_ended_on_a_page(
    sample: Sample,
) -> None:
    """REQ-200. Its reference is the one the organisation's certificates carry (REQ-110)."""
    with working_for(sample.ours.id, sample.administrator.id):
        first = Approval.objects.get()
        with pytest.raises(approvals.RefusedError, match="Set Up With"):
            approvals.end(first, on=date(2026, 11, 18))
        assert approvals.types_held(sample.ours) == {"Part-CAO"}


def test_another_organisations_approvals_are_not_seen_or_added_to(sample: Sample) -> None:
    """REQ-002, REQ-003. Row-level security: read and write."""
    with working_for(sample.other.id, sample.stranger.id):
        assert held(sample.other) == [("Part-CAO", "UK.CAO.[Other Number]")]
        assert held(sample.ours) == []
        with pytest.raises(ProgrammingError, match="row-level security"), transaction.atomic():
            Approval.objects.create(
                organisation=sample.ours, approval="Part-145", reference="UK.145.[Number]"
            )


def test_an_organisation_from_before_approvals_were_records_is_given_its_own(
    sample: Sample,
) -> None:
    """REQ-200. The migration's own statement, run on an organisation with no approval record.

    The owner of the tables sees no organisation's rows (ADR-0002), so the
    statement goes through the organisations one at a time. It adds what is
    missing and changes nothing that is there.
    """
    with as_owner(), connection.cursor() as cursor:
        # An organisation as the earlier set-up made it: no approval record.
        cursor.execute("SELECT set_config('airworthiness.organisation', %s, true)", [EARLIER])
        cursor.execute(
            "INSERT INTO organisations_organisation (id, name, approval_type, approval_reference,"
            " address, privileges, scope_of_work, due_soon_days, due_soon_hours, due_soon_cycles,"
            " records_approval_reference, certificate_serial_floor)"
            " VALUES (%s, '[Earlier Organisation]', 'Part-CAO', 'UK.CAO.[Earlier]',"
            " '', ARRAY['Maintenance'], 'Aeroplanes', 30, 10.0, 10, '', 0)",
            [EARLIER],
        )
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")

        cursor.execute(for_each_organisation(APPROVAL_FOR_EACH_ORGANISATION))

        # Row-level security is forced again, and no organisation is left set.
        cursor.execute(
            "SELECT relforcerowsecurity FROM pg_class WHERE relname = 'organisations_organisation'"
        )
        assert cursor.fetchone() == (True,)
        cursor.execute("SELECT current_setting('airworthiness.organisation', true)")
        assert cursor.fetchone() == ("",)
        cursor.execute("SELECT set_config('airworthiness.organisation', %s, true)", [EARLIER])
        # The owner may be a superuser, whom row-level security does not hold, so
        # each question names the organisation it is about.
        cursor.execute(
            "SELECT approval, reference FROM organisations_approval WHERE organisation_id = %s",
            [EARLIER],
        )
        assert cursor.fetchall() == [("Part-CAO", "UK.CAO.[Earlier]")]
        cursor.execute(
            "SELECT action, actor_id, actor_name LIKE 'Database Role %%' FROM history_event "
            "WHERE record_type = 'organisations_approval' AND organisation_id = %s",
            [EARLIER],
        )
        assert cursor.fetchall() == [("Created", None, True)]
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")
    # Those that had their record keep it, and are given no second one.
    with working_for(sample.ours.id, sample.administrator.id):
        assert held(sample.ours) == [("Part-CAO", "UK.CAO.[Number]")]
        assert Event.objects.filter(record_type="organisations_approval").count() == 1
