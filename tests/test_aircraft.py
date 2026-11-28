"""Aircraft, counters and entries of hours and cycles (REQ-020 to REQ-028).

The fleet is the one in design-system/SampleData.md. Today in the sample
world is 18 November 2026.
"""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client

from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services
from airworthiness_plus.aircraft.models import (
    Aircraft,
    CounterKind,
    Regime,
    Stage,
    Status,
    UtilisationEntry,
)
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface import formatting
from airworthiness_rules.intervals import Reading
from airworthiness_rules.utilisation import EntryRefusedError
from tests.conftest import as_owner
from tests.support import (
    FLEET,
    TODAY,
    Sample,
    add_sample_fleet,
    call,
    dot,
    get,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal


@pytest.fixture(autouse=True)
def sample_today(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(services, "today", lambda: TODAY)


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    return add_sample_fleet(sample)


def airframe(aircraft: Aircraft):  # type: ignore[no-untyped-def]
    return aircraft.counters.get(kind=CounterKind.AIRFRAME)


# Writing


def test_dates_and_numbers_are_written_as_the_writing_rules_say() -> None:
    """REQ-192. 18 November 2026; 6,412.6; 4,236."""
    assert formatting.long_date(date(2026, 11, 18)) == "18 November 2026"
    assert formatting.long_date(date(2026, 12, 6)) == "6 December 2026"
    assert formatting.hours(D("6412.6")) == "6,412.6"
    assert formatting.hours(D("3318")) == "3,318.0"
    assert formatting.hours(D("12.4")) == "12.4"
    assert formatting.whole(4236) == "4,236"


# The Fleet


def test_the_fleet_page_shows_the_sample_fleet(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-020, REQ-021, REQ-054, REQ-191. Six aircraft, each type rating exactly
    as SRG1782 writes it, with airframe hours and the date they were entered for."""
    page = get(signed_in(sample.reader), "/").content.decode()
    for registration, type_rating, owner, hours in FLEET:
        assert registration in page
        assert f"<td>{type_rating}</td>" in page
        assert f"<td>{owner}</td>" in page
        assert f'<td class="number">{formatting.hours(D(hours))}</td>' in page
    assert '<th scope="col">Aircraft Registration</th>' in page
    assert '<td class="number">9,874.3</td>' in page
    assert page.count("<td>18 November 2026</td>") == 6
    assert f"<td>{dot('Unserviceable')}, Stabilator Trim Cable</td>" in page
    assert page.count(f"<td>{dot('Serviceable')}</td>") == 5
    assert "G-HKLM" not in page


def test_a_type_rating_is_stored_byte_for_byte(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-021. Never re-cased or shortened: "Robin DR 400 series (Lycoming)"
    keeps its lower-case s."""
    with working_for(sample.ours.id, sample.lucy.id):
        stored = dict(Aircraft.objects.values_list("registration", "type_rating"))
    for registration, type_rating, _, _ in FLEET:
        assert stored[registration].encode() == type_rating.encode()
    assert stored["G-CDEF"] == "Robin DR 400 series (Lycoming)"


def test_a_transfer_in_stays_out_of_the_fleet_until_its_records_are_complete(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-027. G-HKLM: Records 14 of 18 Received."""
    client = signed_in(sample.lucy)
    transfers = get(client, "/transfers/").content.decode()
    assert "G-HKLM" in transfers
    assert "Records 14 of 18 Received" in transfers
    hklm = fleet["G-HKLM"]
    assert not hklm.calculations_supported
    assert (
        "No Due Items Until Records Are Complete"
        in get(client, f"/aircraft/{hklm.id}/").content.decode()
    )

    # Moving it to the Fleet early is refused.
    post(client, f"/aircraft/{hklm.id}/records-received/", received="17", complete="Yes")
    assert "G-HKLM" not in get(client, "/").content.decode()
    assert "Records 17 of 18 Received" in get(client, "/transfers/").content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(services.TransferNotCompleteError):
            services.complete_transfer(Aircraft.objects.get(pk=hklm.pk))

    post(client, f"/aircraft/{hklm.id}/records-received/", received="19", complete="Yes")
    assert "Records 17 of 18 Received" in get(client, "/transfers/").content.decode()

    post(client, f"/aircraft/{hklm.id}/records-received/", received="18", complete="Yes")
    assert "G-HKLM" in get(client, "/").content.decode()
    assert "G-HKLM" not in get(client, "/transfers/").content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        assert Aircraft.objects.get(pk=hklm.pk).calculations_supported


def test_a_non_part_21_aircraft_is_recorded_but_not_calculated(sample: Sample) -> None:
    """REQ-022."""
    client = signed_in(sample.lucy)
    added = post(
        client,
        "/aircraft/add/",
        registration="G-NATL",
        type_rating="[Type Rating]",
        owner="[Owner Name]",
        regime="Non-Part 21",
    )
    assert added.status_code == 302
    page = get(client, added["Location"]).content.decode()
    assert "Calculations Not Yet Supported for Non-Part 21 Aircraft" in page
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft = Aircraft.objects.get(registration="G-NATL")
    assert aircraft.regime == Regime.NON_PART_21
    assert not aircraft.calculations_supported


def test_a_registration_is_recorded_once_in_an_organisation(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-020. The same registration may be in another organisation's records."""
    client = signed_in(sample.lucy)
    again = post(
        client,
        "/aircraft/add/",
        registration="G-ABCD",
        type_rating="Piper PA-28 Series (Lycoming)",
        owner="Pilot-Owner",
        regime="Part 21",
    )
    assert again.status_code == 200
    assert "This Aircraft Registration Is Already Recorded" in again.content.decode()
    with working_for(sample.other.id, sample.stranger.id):
        services.add_aircraft(
            organisation=sample.other,
            registration="G-ABCD",
            type_rating="Piper PA-28 Series (Lycoming)",
            owner="Pilot-Owner",
        )


# Status


def test_unserviceable_carries_a_reason_and_a_date(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-023. G-DGHI: Unserviceable, Stabilator Trim Cable, since 14 November 2026."""
    client = signed_in(sample.lucy)
    dghi = fleet["G-DGHI"]
    page = get(client, f"/aircraft/{dghi.id}/").content.decode()
    assert f"{dot('Unserviceable')}, Stabilator Trim Cable, Since 14 November 2026" in page

    with working_for(sample.ours.id, sample.lucy.id):
        for values in (
            {"status": Status.UNSERVICEABLE, "unserviceable_reason": ""},
            {"status": Status.UNSERVICEABLE, "unserviceable_since": None},
            {"status": Status.SERVICEABLE},
        ):
            with pytest.raises(IntegrityError, match="unserviceable"), transaction.atomic():
                Aircraft.objects.filter(pk=dghi.pk).update(**values)

    assert post(client, f"/aircraft/{dghi.id}/serviceable/").status_code == 302
    assert "<dd>Serviceable</dd>" in get(client, f"/aircraft/{dghi.id}/").content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        last = Event.of(dghi).last()
    assert last is not None
    assert last.before_json is not None
    assert "Stabilator Trim Cable" in last.before_json

    abcd = fleet["G-ABCD"]
    post(
        client,
        f"/aircraft/{abcd.id}/unserviceable/",
        reason="Left Landing Light",
        since="2026-11-18",
    )
    assert (
        f"{dot('Unserviceable')}, Left Landing Light, Since 18 November 2026"
        in get(client, f"/aircraft/{abcd.id}/").content.decode()
    )


# Hours and cycles


def test_g_abcd_entries_are_kept_and_the_latest_is_the_total(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-024. 6,375.0 on 2 October 2026, entered late, fits before 6,412.6 on
    18 November 2026; the total stays 6,412.6."""
    with working_for(sample.ours.id, sample.planner.id):
        counter = airframe(fleet["G-ABCD"])
        services.enter_utilisation(counter, Reading(date(2026, 10, 2), D("6375.0"), 0))
        assert services.current_reading(counter) == Reading(TODAY, D("6412.6"), 0)
        assert [entry.hours for entry in counter.entries.all()] == [D("6375.0"), D("6412.6")]
        entry = counter.entries.first()
        assert entry is not None
        created = Event.of(entry).get()
    assert (created.action, created.actor_name) == ("Created", "[Planning and Records Name]")


def test_a_lower_total_is_refused_by_the_rules_and_by_the_database(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-025, hazard H-011. 6,402.6 after 6,412.6. The database refuses it even
    when the application's check is bypassed."""
    with working_for(sample.ours.id, sample.planner.id):
        counter = airframe(fleet["G-ABCD"])
        with pytest.raises(EntryRefusedError, match="Lower than the previous entry"):
            services.enter_utilisation(counter, Reading(TODAY, D("6402.6"), 0))
        with pytest.raises(DatabaseError, match="Lower than the previous entry"):
            with transaction.atomic():
                UtilisationEntry.objects.create(
                    organisation=sample.ours,
                    counter=counter,
                    dated=TODAY,
                    hours=D("6402.6"),
                    cycles=0,
                )
        with pytest.raises(DatabaseError, match="Higher than a later entry"):
            with transaction.atomic():
                UtilisationEntry.objects.create(
                    organisation=sample.ours,
                    counter=counter,
                    dated=date(2026, 11, 10),
                    hours=D("6420.0"),
                    cycles=0,
                )
        assert counter.entries.count() == 1


def test_an_unusual_increase_needs_confirmation_on_the_page(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-025, REQ-026. 6,435.0 the same day as 6,412.6 is 22.4 hours in a day.
    The page names the aircraft and asks; confirmed, the entry is saved and marked."""
    client = signed_in(sample.planner)
    abcd = fleet["G-ABCD"]
    path = f"/aircraft/{abcd.id}/hours-and-cycles/"
    with working_for(sample.ours.id, sample.planner.id):
        counter = airframe(abcd)
    form = {"counter": str(counter.id), "dated": "2026-11-18", "hours": "6435.0", "cycles": "0"}

    blank = get(client, path).content.decode()
    assert blank.count("G-ABCD") >= 3

    asked = post(client, path, **form)
    assert asked.status_code == 200
    assert "Unusual Increase for G-ABCD, Confirm to Save" in asked.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        assert counter.entries.count() == 1

    saved = post(client, path, **form, confirmed="on")
    assert saved.status_code == 302
    page = get(client, f"/aircraft/{abcd.id}/").content.decode()
    assert '<td class="number">6,435.0</td>' in page
    assert "Unusual Increase Confirmed" in page


def test_a_decimal_slip_is_refused_on_the_page(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-025, hazard H-011. 64,126.0 for 6,412.6 cannot be confirmed through."""
    client = signed_in(sample.planner)
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.planner.id):
        counter = airframe(abcd)
    refused = post(
        client,
        f"/aircraft/{abcd.id}/hours-and-cycles/",
        counter=str(counter.id),
        dated="2026-11-18",
        hours="64126.0",
        cycles="0",
        confirmed="on",
    )
    assert refused.status_code == 200
    assert "More hours than there are in the days between entries" in refused.content.decode()
    two_places = post(
        client,
        f"/aircraft/{abcd.id}/hours-and-cycles/",
        counter=str(counter.id),
        dated="2026-11-18",
        hours="6412.65",
        cycles="0",
    )
    assert two_places.status_code == 200
    with working_for(sample.ours.id, sample.planner.id):
        assert counter.entries.count() == 1


def test_a_correction_supersedes_the_wrong_entry_which_stays(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-025. 6,412.6 corrected to 6,410.9: lower, so only a correction can do it."""
    client = signed_in(sample.planner)
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.planner.id):
        counter = airframe(abcd)
        wrong = counter.entries.get()
    corrected = post(
        client,
        f"/aircraft/{abcd.id}/hours-and-cycles/",
        counter=str(counter.id),
        dated="2026-11-18",
        hours="6410.9",
        cycles="0",
        supersedes=str(wrong.id),
    )
    assert corrected.status_code == 302
    page = get(client, f"/aircraft/{abcd.id}/").content.decode()
    assert "<td>Superseded</td>" in page
    assert "<td>Current, Correction</td>" in page
    assert '<td class="number">6,412.6</td>' in page
    with working_for(sample.ours.id, sample.planner.id):
        assert services.current_reading(counter) == Reading(TODAY, D("6410.9"), 0)
        assert counter.entries.count() == 2
        # A superseded entry cannot be superseded a second time.
        with pytest.raises(IntegrityError), transaction.atomic():
            UtilisationEntry.objects.create(
                organisation=sample.ours,
                counter=counter,
                dated=TODAY,
                hours=D("6411.0"),
                cycles=0,
                supersedes=wrong,
            )


def test_an_entry_is_never_changed_or_deleted(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-025, REQ-131. The application's role has no right to update the table."""
    with working_for(sample.ours.id, sample.planner.id):
        entry = airframe(fleet["G-ABCD"]).entries.get()
        entry.hours = D("6000.0")
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.save()
        with pytest.raises(RecordsAreNeverDeletedError):
            entry.delete()
        for statement in (
            "UPDATE aircraft_utilisationentry SET hours = 6000.0",
            "DELETE FROM aircraft_utilisationentry",
        ):
            with (
                pytest.raises(DatabaseError, match="permission denied"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(statement)


def test_engines_and_propellers_have_their_own_hours(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-020, REQ-059. G-CDEF flies on a loan propeller: its hours are its own."""
    client = signed_in(sample.lucy)
    cdef = fleet["G-CDEF"]
    for kind, position in (("Engine", "Engine 1"), ("Propeller", "Propeller 1")):
        added = post(
            client, f"/aircraft/{cdef.id}/counters/", kind=kind, position=position, serial_number=""
        )
        assert added.status_code == 302
    again = post(client, f"/aircraft/{cdef.id}/counters/", kind="Engine", position="Engine 1")
    assert "This Position Is Already Recorded" in again.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        engine = cdef.counters.get(kind=CounterKind.ENGINE)
        propeller = cdef.counters.get(kind=CounterKind.PROPELLER)
        services.enter_utilisation(engine, Reading(TODAY, D("1780.0"), 0))
        services.enter_utilisation(propeller, Reading(TODAY, D("212.4"), 0))
        assert services.current_reading(airframe(cdef)) == Reading(TODAY, D("7731.5"), 0)
        assert services.current_reading(engine) == Reading(TODAY, D("1780.0"), 0)
        assert services.current_reading(propeller) == Reading(TODAY, D("212.4"), 0)
        # A second airframe, or an engine with no position, is refused.
        with pytest.raises(IntegrityError), transaction.atomic():
            services.add_counter(cdef, CounterKind.AIRFRAME)
        with pytest.raises(IntegrityError), transaction.atomic():
            services.add_counter(cdef, CounterKind.ENGINE)
    page = get(client, f"/aircraft/{cdef.id}/").content.decode()
    assert "<h2>Engine 1</h2>" in page
    # A counter is named once (the Dashboard wrote Engine Engine 1): the position
    # alone where it says what it is, the kind before it where it does not.
    with working_for(sample.ours.id, sample.lucy.id):
        left = services.add_counter(cdef, CounterKind.ENGINE, "Left")
        assert (str(engine), str(propeller), str(left)) == (
            "Engine 1",
            "Propeller 1",
            "Engine Left",
        )
        assert str(airframe(cdef)) == "Airframe"
    assert "<dd>1,780.0</dd>" in page


# Other organisations (planned test T-SEC-010) and roles (planned test T-SEC-011)

PAGES = (
    # method, address after /aircraft/<id>, the action it takes
    ("GET", "/", Action.VIEW_RECORDS),
    ("GET", "/hours-and-cycles/", Action.ENTER_UTILISATION),
    ("POST", "/hours-and-cycles/", Action.ENTER_UTILISATION),
    ("GET", "/unserviceable/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ("POST", "/unserviceable/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ("POST", "/serviceable/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ("GET", "/counters/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ("POST", "/counters/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ("POST", "/records-received/", Action.ADD_OR_CHANGE_AIRCRAFT),
)


def test_another_organisations_aircraft_is_not_found_on_any_page(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-003, REQ-004, threats TH-006 and TH-020, planned test T-SEC-010. A user
    with every right in their own organisation, holding the identifier of our
    aircraft, gets Not Found from every page, read and write."""
    stranger = signed_in(sample.stranger)
    abcd = fleet["G-ABCD"]
    for method, tail, _ in PAGES:
        response = call(stranger, method, f"/aircraft/{abcd.id}{tail}")
        assert response.status_code == 404, f"{method} {tail}"
    assert "G-ABCD" not in get(stranger, "/").content.decode()
    assert "G-HKLM" not in get(stranger, "/transfers/").content.decode()
    with as_owner():
        assert Aircraft.objects.get(pk=abcd.pk).status == Status.SERVICEABLE
        assert UtilisationEntry.objects.filter(counter__aircraft=abcd).count() == 1


def test_a_record_cannot_refer_to_another_organisations_record(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-002, threat TH-020. A counter in their organisation naming our
    aircraft, or an entry naming our counter, is refused by the database, for
    the application and for the owner."""
    ours = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        our_counter = airframe(ours)
    insert_counter = (
        "INSERT INTO aircraft_counter (id, organisation_id, aircraft_id, kind, position, "
        "serial_number) VALUES (%s, %s, %s, 'Engine', 'Engine 9', '')"
    )
    insert_entry = (
        "INSERT INTO aircraft_utilisationentry (id, organisation_id, counter_id, dated, hours, "
        "cycles, confirmed_unusual) VALUES (%s, %s, %s, '2026-11-18', 7000.0, 0, false)"
    )
    with working_for(sample.other.id, sample.stranger.id):
        for statement, parent in ((insert_counter, ours.id), (insert_entry, our_counter.id)):
            with (
                pytest.raises(DatabaseError, match="own organisation"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(statement, [uuid.uuid4(), sample.other.id, parent])
    with as_owner(), working_for(sample.other.id):
        with (
            pytest.raises(DatabaseError, match="own organisation"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute(insert_counter, [uuid.uuid4(), sample.other.id, ours.id])


@pytest.mark.parametrize("role", ["Administrator", "Planning and Records", "Read Only"])
def test_every_aircraft_page_follows_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Each page, called directly,
    is refused with 403 for a role the matrix does not allow, and the refusal is
    in the access log; for a role it does allow, the page answers."""
    user = sample.by_role()[role]
    client = signed_in(user)
    target = fleet["G-HKLM"]
    refusals = 0
    for method, tail, action in (*PAGES, ("GET", "add", Action.ADD_OR_CHANGE_AIRCRAFT)):
        path = "/aircraft/add/" if tail == "add" else f"/aircraft/{target.id}{tail}"
        response = call(client, method, path)
        if permitted(user.roles, action):
            # The direct POST omits the required count, which the Transfers form rejects.
            expected_statuses = (400,) if tail == "/records-received/" else (200, 302)
            assert response.status_code in expected_statuses, f"{role} {method} {tail}"
        else:
            assert response.status_code == 403, f"{role} {method} {tail}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        from airworthiness_plus.accounts.models import AccessEntry

        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    expected = {"Administrator": 9, "Planning and Records": 0, "Read Only": 9}
    assert refusals == expected[role]


def test_a_page_asked_for_without_signing_in_goes_to_sign_in(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-008, threat TH-008."""
    client = Client()
    for method, tail, _ in PAGES:
        response = call(client, method, f"/aircraft/{fleet['G-ABCD'].id}{tail}")
        assert response.status_code == 302, f"{method} {tail}"
        assert response["Location"].startswith("/sign-in/")


def test_a_forged_write_is_refused_on_every_aircraft_page(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """Threat TH-003, planned test T-SEC-005."""
    client = Client(enforce_csrf_checks=True)
    client.force_login(
        sample.lucy, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, tail, _ in PAGES:
        if method == "POST":
            response = post(client, f"/aircraft/{fleet['G-ABCD'].id}{tail}")
            assert response.status_code == 403, tail
    assert post(client, "/aircraft/add/").status_code == 403


def test_the_stage_of_the_sample_fleet(sample: Sample, fleet: dict[str, Aircraft]) -> None:
    """REQ-027. Six in the Fleet, one Transfer In."""
    with working_for(sample.ours.id, sample.lucy.id):
        assert Aircraft.objects.filter(stage=Stage.FLEET).count() == 6
        assert [a.registration for a in Aircraft.objects.filter(stage=Stage.TRANSFER_IN)] == [
            "G-HKLM"
        ]
