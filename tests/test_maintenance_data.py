"""Maintenance data (REQ-080 to REQ-089, hazard H-005).

The data is that of design-system/SampleData.md, Documentation. Today in
the sample world is 18 November 2026.
"""

from datetime import date

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.maintenance_data import services
from airworthiness_plus.maintenance_data.models import (
    AmendmentCheck,
    DataSet,
    Evidence,
    Holding,
    Kind,
    Revision,
)
from airworthiness_plus.sample import build
from airworthiness_rules.programme import Flag
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    call,
    page,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db

GROB, PA38, C172 = build.GROB, build.PA38, build.C172


class Day:
    def __init__(self) -> None:
        self.today = TODAY

    def __call__(self) -> date:
        return self.today


@pytest.fixture(autouse=True)
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    moving = Day()
    monkeypatch.setattr(aircraft_services, "today", moving)
    return moving


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    return add_sample_fleet(sample)


@pytest.fixture
def data(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, DataSet]:
    """SampleData.md, Documentation, Maintenance data."""
    return build.add_maintenance_data(sample)


def lines(sample: Sample, today: date = TODAY) -> dict[str, services.DataLine]:
    with working_for(sample.ours.id, sample.reader.id):
        return {line.data_set.title: line for line in services.data_lines(sample.ours, today)}


# What is held


def test_each_set_shows_its_author_revision_and_last_check(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-080, REQ-081, REQ-082. Title, author, kind, type ratings, revision and
    its date, the amendment service, and who last checked it and when."""
    body = page(signed_in(sample.reader), "/maintenance-data/")
    for text in (
        "Grob G 115 Maintenance Manual</a></td>",
        "<td>[Type Certificate Holder]</td>",
        "<td>Instructions for Continued Airworthiness</td>",
        f"<td>{GROB}</td>",
        "<td>[Revision]</td>",
        "<td>1 March 2026</td>",
        "<td>2 November 2026, [Planning and Records Name]</td>",
        "<td>20 November 2026</td>",
        "<td>Civil Aviation Authority Requirement</td>",
        "<td>Mandatory Instructions or Airworthiness Limitations</td>",
    ):
        assert text in body, text
    assert set(Kind.values) == {
        "Civil Aviation Authority Requirement",
        "Airworthiness Directive",
        "Instructions for Continued Airworthiness",
        "Component Manufacturer's Instructions",
        "Modified Maintenance Instructions",
    }


def test_grob_manual_amendment_check_is_due_by_20_november(
    sample: Sample, data: dict[str, DataSet], day: Day
) -> None:
    """REQ-083, golden. 2 days away on 18 November 2026: Due Soon. Due on the
    20th, Overdue from the 21st, and clear again once the check is recorded."""
    title = "Grob G 115 Maintenance Manual"
    assert lines(sample)[title].flag is Flag.DUE_SOON
    assert lines(sample, date(2026, 11, 20))[title].flag is Flag.DUE
    late = lines(sample, date(2026, 11, 21))[title]
    assert (late.flag, late.state) == (Flag.OVERDUE, "Amendment Check Overdue")

    day.today = date(2026, 11, 21)
    client = signed_in(sample.planner)
    done = post(
        client,
        f"/maintenance-data/{data['grob'].id}/checks/",
        checked_on="2026-11-21",
        result="Amendment Received, Revision [Next Revision]",
        next_due="2026-12-21",
    )
    assert done.status_code == 302
    after = lines(sample, date(2026, 11, 21))[title]
    assert (after.flag, after.state) == (Flag.DUE_SOON, "Held and Current")
    body = page(client, f"/maintenance-data/{data['grob'].id}/")
    assert "<td>21 November 2026</td><td>[Planning and Records Name]</td>" in body
    assert "<td>2 November 2026</td><td>[Planning and Records Name]</td>" in body


def test_backdated_check_keeps_the_latest_deadline(
    sample: Sample, data: dict[str, DataSet], day: Day
) -> None:
    manual = data["grob"]
    day.today = date(2026, 11, 21)
    client = signed_in(sample.planner)
    path = f"/maintenance-data/{manual.id}/"
    response = post(
        client,
        path + "checks/",
        checked_on="2026-11-01",
        result="Earlier Check",
        next_due="2027-01-15",
    )
    assert response.status_code == 302
    assert "Earlier Check" in page(client, path)
    line = lines(sample, day.today)[manual.title]
    assert line.last_check is not None and line.last_check.checked_on == date(2026, 11, 2)
    assert line.data_set.check_due == date(2026, 11, 20)
    assert line.flag is Flag.OVERDUE
    assert manual.title in page(client, "/dashboard/")


def test_overdue_checks_come_first_and_mandatory_data_first_among_them(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-084, AMC1 145.A.45(g). On 5 December 2026 both the Grob manual (due
    20 November) and CAP 747 (due 30 November) are overdue. CAP 747 carries
    mandatory requirements and is shown before the manual. Data not held is
    shown with them."""
    ordered = list(lines(sample, date(2026, 12, 5)))
    assert ordered[:3] == [
        "CAP 747 Mandatory Requirements for Airworthiness",
        "Grob G 115 Maintenance Manual",
        "Piper PA-38 Series Maintenance Manual",
    ]
    today = list(lines(sample))
    assert today[0] == "Piper PA-38 Series Maintenance Manual"


# Revisions


def test_a_new_revision_supersedes_the_old_which_stays_marked(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-085, hazard H-005. Exactly one revision is current."""
    client = signed_in(sample.planner)
    grob = data["grob"]
    added = post(
        client,
        f"/maintenance-data/{grob.id}/revisions/",
        revision="[Next Revision]",
        revision_date="2026-11-15",
    )
    assert added.status_code == 302
    body = page(client, f"/maintenance-data/{grob.id}/")
    assert "<td>[Revision]</td><td>1 March 2026</td><td>Superseded</td>" in body
    assert "<td>[Next Revision]</td><td>15 November 2026</td><td>Current</td>" in body
    listing = page(client, "/maintenance-data/")
    assert "<td>[Next Revision]</td>" in listing
    with working_for(sample.ours.id, sample.planner.id):
        assert Revision.objects.filter(data_set=grob, current=True).count() == 1
        assert Revision.objects.filter(data_set=grob).count() == 2
        for revision, revision_date, message in (
            ("[Next Revision]", date(2026, 11, 16), "Already Recorded"),
            ("[Earlier]", date(2026, 1, 1), "Not Dated Before"),
        ):
            with pytest.raises(services.RefusedError, match=message):
                services.add_revision(grob, revision=revision, revision_date=revision_date)


def test_a_superseded_revision_is_never_made_current_again(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-085, hazard H-005. Refused by the database for the application and for
    the owner; and a second current revision cannot be added beside the first."""
    grob = data["grob"]
    with working_for(sample.ours.id, sample.planner.id):
        services.add_revision(grob, revision="[Next Revision]", revision_date=date(2026, 11, 15))
        old = Revision.objects.get(data_set=grob, current=False)
        with pytest.raises(DatabaseError, match="never made current again"), transaction.atomic():
            Revision.objects.filter(pk=old.pk).update(current=True)
        with pytest.raises(IntegrityError, match="one_current"), transaction.atomic():
            Revision.objects.create(
                organisation=sample.ours,
                data_set=grob,
                revision="[Another]",
                revision_date=date(2026, 11, 16),
            )
    with as_owner(), working_for(sample.ours.id):
        with (
            pytest.raises(DatabaseError, match="never made current again"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(
                "UPDATE maintenance_data_revision SET current = true WHERE id = %s", [old.id]
            )


# Customer-provided data


def test_g_bxyz_owner_provided_data_shows_how_its_amendment_status_is_known(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-086, golden. Confirmed current in writing on 2 June 2026."""
    client = signed_in(sample.planner)
    body = page(client, "/maintenance-data/")
    assert "Provided by Syndicate of 6, Written Confirmation, 2 June 2026" in body
    again = post(
        client,
        f"/maintenance-data/{data['bxyz'].id}/customer-status/",
        evidence="Customer's Amendment List",
        dated="2026-11-17",
    )
    assert again.status_code == 302
    assert "Provided by Syndicate of 6, Customer&#x27;s Amendment List, 17 November 2026" in page(
        client, "/maintenance-data/"
    )
    with working_for(sample.ours.id, sample.planner.id):
        with pytest.raises(services.RefusedError, match="Not Provided by a Customer"):
            services.confirm_customer_status(
                data["grob"], evidence=Evidence.WORK_ORDER, dated=TODAY
            )
        with pytest.raises(services.RefusedError, match="Shows Its Amendment Status"):
            services.record_data(
                organisation=sample.ours,
                title="[Customer Data]",
                author="[Author]",
                kind=Kind.INSTRUCTIONS,
                revision="[Revision]",
                revision_date=TODAY,
                provided_by="[Owner Name]",
            )


def test_customer_data_no_longer_held_stays_in_the_record(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-087, CAO.A.055(a), CAO.A.080. Held while the work is in progress or
    for the contract; then marked No Longer Held with the date, and kept."""
    client = signed_in(sample.planner)
    ended = post(client, f"/maintenance-data/{data['bxyz'].id}/no-longer-held/", on="2026-11-18")
    assert ended.status_code == 302
    assert "<td>No Longer Held, From 18 November 2026</td>" in page(client, "/maintenance-data/")
    with working_for(sample.ours.id, sample.planner.id):
        kept = DataSet.objects.get(pk=data["bxyz"].pk)
        assert (kept.holding, kept.no_longer_held_on) == (Holding.NO_LONGER_HELD, TODAY)
        assert kept.revisions.count() == 1
        with pytest.raises(services.RefusedError, match="No Longer Held"):
            services.add_revision(kept, revision="[Later]", revision_date=TODAY)
        with pytest.raises(services.RefusedError, match="Only Data That Is Held"):
            services.end_holding(kept, TODAY)


# Data for an aircraft


def test_data_needed_but_not_held_is_shown_as_not_held(
    sample: Sample, fleet: dict[str, Aircraft], data: dict[str, DataSet]
) -> None:
    """REQ-088, REQ-089, golden. Piper PA-38 Series manual, needed for G-HKLM."""
    client = signed_in(sample.reader)
    body = page(client, f"/aircraft/{fleet['G-HKLM'].id}/maintenance-data/")
    assert "<p>Not Held</p>" in body
    assert "Piper PA-38 Series Maintenance Manual" in body
    assert "<td>Not Held</td>" in page(client, "/maintenance-data/")

    # When the manual arrives, its first revision makes it Held.
    post(
        signed_in(sample.planner),
        f"/maintenance-data/{data['pa38'].id}/revisions/",
        revision="[Revision]",
        revision_date="2026-10-01",
    )
    body = page(client, f"/aircraft/{fleet['G-HKLM'].id}/maintenance-data/")
    assert "<p>No Amendment Check Recorded</p>" in body


def test_whether_the_data_for_an_aircraft_is_held_and_current(
    sample: Sample, fleet: dict[str, Aircraft], data: dict[str, DataSet], day: Day
) -> None:
    """REQ-089. G-FMNO, Grob: held and current, last checked 2 November 2026;
    after 20 November the check is overdue. G-EJKL: nothing recorded for its type."""
    client = signed_in(sample.reader)
    fmno = page(client, f"/aircraft/{fleet['G-FMNO'].id}/maintenance-data/")
    assert "<p>Held and Current</p>" in fmno
    assert "<td>2 November 2026, [Planning and Records Name]</td>" in fmno
    assert "CAP 747" not in fmno
    assert "<p>No Data Recorded for This Type Rating</p>" in page(
        client, f"/aircraft/{fleet['G-EJKL'].id}/maintenance-data/"
    )
    day.today = date(2026, 11, 21)
    late = page(signed_in(sample.reader), f"/aircraft/{fleet['G-FMNO'].id}/maintenance-data/")
    assert "<p>Amendment Check Overdue</p>" in late


# Recording


def test_data_is_recorded_through_the_page(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-080, REQ-021. Type ratings are kept exactly as typed, one on each line."""
    client = signed_in(sample.planner)
    added = post(
        client,
        "/maintenance-data/add/",
        title="Robin DR 400 Maintenance Manual",
        author="[Type Certificate Holder]",
        kind="Instructions for Continued Airworthiness",
        applies_to="Robin DR 400 series (Lycoming)\r\n",
        held="on",
        revision="[Revision]",
        revision_date="2026-02-01",
        amendment_service="[Amendment Service]",
        check_due="2026-12-02",
    )
    assert added.status_code == 302
    with working_for(sample.ours.id, sample.planner.id):
        recorded = DataSet.objects.get(title="Robin DR 400 Maintenance Manual")
    assert recorded.applies_to == ["Robin DR 400 series (Lycoming)"]
    assert "<p>Held and Current</p>" in page(
        client, f"/aircraft/{fleet['G-CDEF'].id}/maintenance-data/"
    )
    refused = post(
        client,
        "/maintenance-data/add/",
        title="[No Revision]",
        author="[Author]",
        kind="Instructions for Continued Airworthiness",
        held="on",
    )
    assert "Data Held Has a Revision and a Revision Date" in refused.content.decode()


def test_an_amendment_check_is_added_and_never_changed(
    sample: Sample, data: dict[str, DataSet]
) -> None:
    """REQ-082, REQ-131. And a check cannot be dated after today or be its own next."""
    with working_for(sample.ours.id, sample.planner.id):
        check = AmendmentCheck.objects.filter(data_set=data["grob"]).get()
        check.result = "Changed"
        with pytest.raises(RecordsAreNeverDeletedError):
            check.save()
        with (
            pytest.raises(DatabaseError, match="permission denied"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute("UPDATE maintenance_data_amendmentcheck SET result = 'Changed'")
        for checked_on, next_due, message in (
            (date(2026, 11, 19), date(2026, 12, 19), "After Today"),
            (TODAY, TODAY, "After This One"),
        ):
            with pytest.raises(services.RefusedError, match=message):
                services.record_check(
                    data["grob"],
                    checked_by=sample.planner,
                    checked_on=checked_on,
                    result="No Amendment",
                    next_due=next_due,
                )


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(data_set: DataSet, aircraft: Aircraft) -> list[tuple[str, str, Action]]:
    base = f"/maintenance-data/{data_set.id}"
    return [
        ("GET", "/maintenance-data/", Action.VIEW_RECORDS),
        ("GET", f"{base}/", Action.VIEW_RECORDS),
        ("GET", f"/aircraft/{aircraft.id}/maintenance-data/", Action.VIEW_RECORDS),
        ("GET", "/maintenance-data/add/", Action.RECORD_MAINTENANCE_DATA),
        ("POST", "/maintenance-data/add/", Action.RECORD_MAINTENANCE_DATA),
        ("POST", f"{base}/revisions/", Action.RECORD_MAINTENANCE_DATA),
        ("POST", f"{base}/checks/", Action.RECORD_AMENDMENT_CHECK),
        ("POST", f"{base}/customer-status/", Action.RECORD_MAINTENANCE_DATA),
        ("POST", f"{base}/no-longer-held/", Action.RECORD_MAINTENANCE_DATA),
    ]


def test_another_organisations_data_is_not_found_or_shown(
    sample: Sample, fleet: dict[str, Aircraft], data: dict[str, DataSet]
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    for method, path, _ in addresses(data["grob"], fleet["G-FMNO"]):
        if str(data["grob"].id) in path or str(fleet["G-FMNO"].id) in path:
            assert call(stranger, method, path).status_code == 404, f"{method} {path}"
    assert "Grob G 115" not in page(stranger, "/maintenance-data/")
    with as_owner():
        assert Revision.objects.filter(data_set=data["grob"]).count() == 1
        assert DataSet.objects.get(pk=data["grob"].pk).holding == Holding.HELD


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_every_maintenance_data_page_follows_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], data: dict[str, DataSet], role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in addresses(data["bxyz"], fleet["G-BXYZ"]):
        status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status in (200, 302), f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    assert refusals == (0 if role == "Planning and Records" else 6)


def test_maintenance_data_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, fleet: dict[str, Aircraft], data: dict[str, DataSet]
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    pages = addresses(data["grob"], fleet["G-FMNO"])
    anonymous = Client()
    for method, path, _ in pages:
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in pages:
        if method == "POST":
            assert post(forged, path).status_code == 403, path
