"""What a restore from backup relies on (REQ-153, REQ-154; hazards H-007, H-009).

The restore itself is a demonstration, recorded in operations/restore-tests/.
These tests cover the two commands it uses: the check of the records and
their history, and the stating of the highest certificate serial.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DatabaseError, connection, transaction

from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.models import Certificate
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    SampleReviews,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    make_sample,
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(aircraft_services, "today", lambda: TODAY)


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    return fleet


@pytest.fixture
def reviews(sample: Sample, fleet: dict[str, Aircraft]) -> SampleReviews:
    return add_sample_reviews(sample, fleet)


def issue(sample: Sample, reviews: SampleReviews, aircraft: Aircraft) -> int:
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.issue_certificate(
            aircraft, staff=reviews.lucy, issued_on=TODAY, airframe_hours=Decimal("1.0")
        )
    assert certificate.serial_number is not None
    return certificate.serial_number


# The highest serial stated


def test_the_next_serial_follows_the_highest_serial_stated(
    sample: Sample,
    fleet: dict[str, Aircraft],
    reviews: SampleReviews,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-154, hazard H-007. The records hold serial 1. The organisation has in fact
    issued up to serial 4, lost with the server. The next certificate is 5, not 2."""
    with as_owner():
        call_command("set_serial_floor", str(sample.ours.id), "4")
    out = capsys.readouterr().out
    assert "Highest Serial in the Records 1" in out
    assert "Highest Serial Stated 4" in out
    assert "Next Serial 5" in out
    assert issue(sample, reviews, fleet["G-EJKL"]) == 5
    assert issue(sample, reviews, fleet["G-ABCD"]) == 6
    with working_for(sample.ours.id, sample.lucy.id):
        references = set(
            Certificate.objects.exclude(serial_number=None).values_list("reference", flat=True)
        )
    assert references == {
        "UK.CAO.[Number]-ARC-0001",
        "UK.CAO.[Number]-ARC-0005",
        "UK.CAO.[Number]-ARC-0006",
    }
    # The statement is in the history of the organisation.
    with working_for(sample.ours.id, sample.administrator.id):
        organisation = Organisation.objects.get()
        last = Event.of(organisation).order_by("-sequence")[0]
        assert last.changed == ["certificate_serial_floor"]


def test_the_highest_serial_is_never_lowered_and_never_set_by_the_application(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-154, threat TH-023. Lowering it could let a serial be used twice."""
    with as_owner():
        call_command("set_serial_floor", str(sample.ours.id), "4")
        with pytest.raises(CommandError, match="already 4"):
            call_command("set_serial_floor", str(sample.ours.id), "3")
        with pytest.raises(CommandError, match="No such organisation"):
            call_command("set_serial_floor", str(uuid.uuid4()), "9")
        with pytest.raises(CommandError, match="not below zero"):
            call_command("set_serial_floor", str(sample.ours.id), "-1")
        # The database refuses a lower value to the owner as well.
        with working_for(sample.ours.id), connection.cursor() as cursor:
            with pytest.raises(DatabaseError, match="never lowered"), transaction.atomic():
                cursor.execute("UPDATE organisations_organisation SET certificate_serial_floor = 0")
    # The application's role cannot set it at all, up or down.
    with working_for(sample.ours.id, sample.administrator.id):
        with pytest.raises(DatabaseError, match="Only the owner"), transaction.atomic():
            Organisation.objects.update(certificate_serial_floor=99)
        # ...and can still change what it is meant to change.
        Organisation.objects.update(parallel_run_started_on=date(2026, 5, 18))
    # A statement below what the records already hold changes nothing in practice.
    with as_owner():
        call_command("set_serial_floor", str(sample.other.id), "0")
    assert issue(sample, reviews, fleet["G-EJKL"]) == 5


# The check of the records


def test_the_check_reports_each_organisation_and_passes_when_all_is_well(
    sample: Sample,
    fleet: dict[str, Aircraft],
    reviews: SampleReviews,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """REQ-153. Run by a role that sees every organisation; it changes nothing."""
    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM history_event")
        before = cursor.fetchone()
        call_command("check_records")
        cursor.execute("SELECT count(*) FROM history_event")
        assert cursor.fetchone() == before
    out = capsys.readouterr().out
    ours = next(line for line in out.splitlines() if str(sample.ours.id) in line)
    assert "0 Chain Problems" in ours
    assert "0 Record Types Not Matching Their History" in ours
    assert "Highest Certificate Serial 1, Highest Serial Stated 0" in ours
    assert str(sample.other.id) in out
    assert "The Records Agree with Their History" in out


def test_the_check_fails_when_history_is_altered_or_a_record_has_none(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-153, threat TH-025. What a careless or hostile restore would leave behind."""
    with as_owner(), connection.cursor() as cursor:
        # Someone with the owner's access changes a history entry beneath the rules.
        cursor.execute("SET CONSTRAINTS ALL IMMEDIATE")
        cursor.execute("ALTER TABLE history_event DISABLE TRIGGER USER")
        cursor.execute(
            "UPDATE history_event SET after_json = replace(after_json, 'G-EJKL', 'G-XXXX') "
            "WHERE record_type = 'aircraft_aircraft' AND after_json LIKE '%%G-EJKL%%'"
        )
        cursor.execute("ALTER TABLE history_event ENABLE TRIGGER USER")
        with pytest.raises(CommandError, match="do not agree"):
            call_command("check_records")


def test_the_check_sees_nothing_as_the_application_and_says_so(sample: Sample) -> None:
    """REQ-003. The application's own role sees no organisation unless one is set."""
    with pytest.raises(CommandError, match="No organisation can be seen"):
        call_command("check_records")
