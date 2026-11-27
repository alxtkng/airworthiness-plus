"""Transfers and Set Up Configuration (REQ-267 to REQ-279).

The Transfers and Set Up Configuration boards, with G-HKLM of
design-system/SampleData.md. Today in the sample is 18 November 2026.
ML.A.305 and ML.A.307 were read in the UK text on 27 November 2026. The
ten items and the six steps are the boards'; that a baseline is not
signed, and an aircraft not moved to the Fleet, with items open is ours.

By hand, for G-HKLM on 18 November 2026:

- The transfer started on 9 November 2026 and is 4 of 10 complete: items
  1, 2 and 4 are complete and item 3 does not apply. Items 5 and 6 are in
  progress, and 7 to 10 are open.
- 12 positions, all tracked: 7 of the airframe (chapters 23, 25, 33, 34,
  37), 4 of the engine (72, 73, 74), 1 of the propeller (61). 8 are
  recorded.
- 6 items are open: the right magneto, the vacuum pump, the emergency
  locator transmitter battery and the fire extinguisher are not recorded;
  the landing light needs a recorded change; and the propeller's calendar
  limit cannot be worked out until its overhaul date is recorded.
"""

import io
import json
import re
import zipfile
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, transaction

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, Counter, CounterKind, Stage
from airworthiness_plus.components import services as component_services
from airworthiness_plus.components.models import Component
from airworthiness_plus.configuration import services
from airworthiness_plus.configuration.models import (
    Baseline,
    ItemState,
    Position,
    Product,
    Transfer,
    TransferItem,
)
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history.models import RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.modifications import services as modification_services
from airworthiness_plus.modifications.models import Data, Route
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.programme import services as programme_services
from airworthiness_plus.programme.models import Basis
from airworthiness_plus.sample import build, phase1
from airworthiness_rules.intervals import Reading
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, get, make_sample, page, post, signed_in
from tests.test_modifications import rows

pytestmark = pytest.mark.django_db
D = Decimal
PROPELLER_OPEN = (
    "Propeller, Fixed Pitch, Calendar Limit Not Worked Out Until the Day It Was New or Last "
    "Overhauled Is Recorded"
)
OPEN_ITEMS = {
    "Right Magneto, Not Recorded",
    "Vacuum Pump, Not Recorded",
    "Emergency Locator Transmitter Battery, Not Recorded",
    "Fire Extinguisher, Not Recorded",
    "Landing Light, Needs a Recorded Change",
    PROPELLER_OPEN,
}


class Day:
    """Today, as the tests set it."""

    def __init__(self) -> None:
        self.today = TODAY


@pytest.fixture
def day(monkeypatch: pytest.MonkeyPatch) -> Day:
    chosen = Day()
    monkeypatch.setattr(aircraft_services, "today", lambda: chosen.today)
    monkeypatch.setattr(sign_in, "today", lambda: chosen.today)
    return chosen


@pytest.fixture
def sample(day: Day) -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = build.add_fleet(sample)
    phase1.add_contracts(sample.ours, sample.lucy, fleet)
    return fleet


@pytest.fixture
def hklm(sample: Sample, fleet: dict[str, Aircraft]) -> Aircraft:
    phase1.add_set_up(sample.ours, sample.lucy, fleet)
    return fleet["G-HKLM"]


def found(sample: Sample, aircraft: Aircraft) -> services.SetUp:
    with working_for(sample.ours.id, sample.reader.id):
        return services.set_up(Aircraft.objects.get(pk=aircraft.pk), TODAY)


def item(sample: Sample, aircraft: Aircraft, number: int) -> TransferItem:
    with working_for(sample.ours.id, sample.reader.id):
        return TransferItem.objects.get(transfer__aircraft=aircraft, number=number)


def position(sample: Sample, aircraft: Aircraft, name: str) -> Position:
    with working_for(sample.ours.id, sample.reader.id):
        return Position.objects.get(aircraft=aircraft, name=name)


def close_every_open_item(sample: Sample, aircraft: Aircraft) -> None:
    """Record the four positions, the landing light's change and the overhaul date."""
    with working_for(sample.ours.id, sample.lucy.id):
        for name in ("Right Magneto", "Vacuum Pump", "Emergency Locator Transmitter Battery",
                     "Fire Extinguisher"):  # fmt: skip
            services.record_position(
                Position.objects.get(aircraft=aircraft, name=name),
                source="[Logbook]",
                part_number="[Part Number]",
                serial_number="[Serial Number]",
            )
        light = modification_services.record_change(
            Aircraft.objects.get(pk=aircraft.pk),
            title="Light-Emitting Diode Landing Light",
            route=Route.MINOR_CHANGE,
            data_kind=Data.DESIGN_ORGANISATION,
            reference="[Minor Change Reference]",
            mass_effect=D("0.0"),
            embodied_on=date(2024, 3, 1),
        )
        services.record_position(
            Position.objects.get(aircraft=aircraft, name="Landing Light"),
            source="Physical Survey, 12 November 2026",
            part_number="[Part Number]",
            needs_change=True,
            change=light,
        )
        propeller = Component.objects.get(serial_number="[Serial Number Propeller G-HKLM]")
        fitting = component_services.current_installation(propeller)
        assert fitting is not None
        component_services.record_life_from(fitting, date(2019, 5, 2))
        # With its overhaul date the propeller's limit still waits for the airframe hours.
        assert services.set_up(Aircraft.objects.get(pk=aircraft.pk), TODAY).open_items == (
            "Propeller, Fixed Pitch, No Airframe Hours Entered",
        )
        counter = Counter.objects.get(aircraft=aircraft, kind=CounterKind.AIRFRAME)
        aircraft_services.enter_utilisation(counter, Reading(TODAY, D("3410.0"), 0))


# The transfer in

CHECKLIST = [
    ["1", "Type Within Scope of Approval", "Complete", "Piper PA-38 Series (Lycoming)", "",
     "The Type Rating of the Aircraft", ""],
    ["2", "Management Contract", "Complete", "Signed 9 November 2026, [Owner Name G-HKLM]", "",
     "Signed With the Owner", "Signed 9 November 2026"],
    ["3", "Import Checks", "Not Applicable", "United Kingdom Register", "",
     "Where the Aircraft Comes From Another Register", ""],
    ["4", "Records Handover Plan", "Complete", "[Previous Organisation], Sent 12 November 2026",
     "", "Agreed With the Previous Organisation", ""],
    ["5", "Records Received and Checked", "In Progress",
     "Engine Logbook Volume 1 Requested 13 November 2026", "To Assess", "Every Record Expected",
     "14 of 18 Received"],
    ["6", "Continuing Airworthiness Records Review", "In Progress", "Lucy Grant", "To Assess",
     "By Whom", ""],
    ["7", "Records Entered", "Open", "", "",
     "Configuration Baseline, Directives and Life Limits", "Configuration Baseline Not Signed"],
    ["8", "Maintenance Programme", "Open", "", "", "Owner Declared or Organisation Approved",
     "No Maintenance Programme Set Up"],
    ["9", "Bridging Check", "Open", "", "", "With Next 100-Hour Check if Programme Changes", ""],
    ["10", "Exposition Scope of Work", "Open", "", "", "Updated on Completion", ""],
]  # fmt: skip


def test_the_transfer_of_the_sample_on_18_november_2026(sample: Sample, hklm: Aircraft) -> None:
    """REQ-267, REQ-268. Golden: the Transfers board, G-HKLM, 4 of 10 complete, with
    what the records say beside the four items they answer."""
    body = page(signed_in(sample.reader), "/transfers/")
    assert "<p>Started 9 November 2026, 4 of 10 Complete</p>" in body
    assert rows(body, 1) == CHECKLIST
    assert rows(body, 0) == [
        ["G-HKLM", "Piper PA-38 Series (Lycoming)", "Pilot-Owner", "Records 14 of 18 Received",
         "Started 9 November 2026, 4 of 10 Complete", ""],
    ]  # fmt: skip
    assert dot("To Assess") in body
    assert f'<a href="/aircraft/{hklm.id}/set-up-configuration/">Set Up Configuration</a>' in body
    assert "<h2>Transfer Out and Record Export</h2>" in body and "None in Progress" in body
    # The reader may not export; a role that may is given the way to.
    assert "Export the Records of an Aircraft" not in body
    assert '<a href="/records-export/">Export the Records of an Aircraft</a>' in page(
        signed_in(sample.lucy), "/transfers/"
    )
    with working_for(sample.ours.id, sample.reader.id):
        panel = dashboard_services.continuing_airworthiness(
            Organisation.objects.get(pk=sample.ours.pk), TODAY
        )
    transfer = next(row for row in panel.rows if row.page == "Transfers")
    assert (transfer.item, transfer.detail) == (
        "Transfer In, Records 14 of 18 Received",
        "Checklist 4 of 10 Complete",
    )
    # Nothing of an aircraft still being transferred in is shown as due.
    assert not [row for row in panel.rows if row.subject == "G-HKLM" and row.page != "Transfers"]


@pytest.mark.parametrize(
    ("received", "reason"),
    [
        ("999", "Enter 18 or Fewer Records"),
        ("not a number", "Enter a whole number."),
        ("", "This field is required."),
    ],
)
def test_invalid_records_received_shows_the_reason_and_keeps_the_input(
    sample: Sample, hklm: Aircraft, received: str, reason: str
) -> None:
    """REQ-027. Reject an invalid count without discarding the entered value."""
    response = post(
        signed_in(sample.planner),
        f"/aircraft/{hklm.id}/records-received/",
        received=received,
        complete="Yes",
    )
    assert response.status_code == 400
    body = response.content.decode()
    assert reason in body
    form_html = re.search(rf'<input[^>]*id="received-{hklm.id}"[^>]*>', body)
    assert form_html and f'value="{received}"' in form_html[0]
    assert "Records 14 of 18 Received" in body
    with working_for(sample.ours.id, sample.reader.id):
        hklm.refresh_from_db()
    assert hklm.records_received == 14
    assert hklm.stage == Stage.TRANSFER_IN


def test_an_item_the_records_answer_is_complete_only_when_they_bear_it_out(
    sample: Sample, hklm: Aircraft
) -> None:
    """REQ-268. Records Received and Checked waits for 18 of 18; Maintenance
    Programme for a programme; Records Entered for a signed baseline; the
    Management Contract for a contract in force."""
    client = signed_in(sample.planner)

    def record(number: int, state: str, note: str = "") -> tuple[int, str]:
        address = f"/transfers/items/{item(sample, hklm, number).id}/"
        answer = post(client, address, state=state, note=note)
        return answer.status_code, answer.content.decode()

    assert record(5, "Complete")[0] == 409
    assert (
        "Records Received and Checked Is Not Complete: 14 of 18 Received"
        in (record(5, "Complete")[1])
    )
    assert (
        "Maintenance Programme Is Not Complete: No Maintenance Programme Set Up"
        in (record(8, "Complete")[1])
    )
    assert (
        "Records Entered Is Not Complete: Configuration Baseline Not Signed"
        in (record(7, "Complete")[1])
    )
    post(client, f"/aircraft/{hklm.id}/records-received/", received="18")
    assert record(5, "Complete", "All 18 Checked")[0] == 302
    with working_for(sample.ours.id, sample.lucy.id):
        programme_services.set_up_programme(
            Aircraft.objects.get(pk=hklm.pk), basis=Basis.INSTRUCTIONS, reference="[Reference]"
        )
    assert record(8, "Complete", "Organisation Approved")[0] == 302
    # The same state and note sent twice is refused.
    assert "This Is Already Recorded" in record(8, "Complete", "Organisation Approved")[1]
    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
    assert record(7, "Complete")[0] == 302
    # The contract of 9 November 2026 is in force, so the item it answers is borne out.
    with working_for(sample.ours.id, sample.planner.id):
        TransferItem.objects.filter(pk=item(sample, hklm, 2).pk).update(state=ItemState.OPEN)
    assert record(2, "Complete", "Signed")[0] == 302
    body = page(client, "/transfers/")
    # Items 1 to 5, 7 and 8, the third not applicable: 7 of 10.
    assert "7 of 10 Complete" in body


def test_not_applicable_is_for_the_items_that_may_not_apply(sample: Sample, hklm: Aircraft) -> None:
    """REQ-268. Ours: the import checks, the handover plan, the bridging check and the
    exposition's scope may not apply, each with the reason. The others always
    apply. The database holds the same."""
    with working_for(sample.ours.id, sample.planner.id):
        for number in (1, 2, 5, 6, 7, 8):
            with pytest.raises(services.RefusedError, match="Always Applies"):
                services.set_item(
                    item(sample, hklm, number), state=ItemState.NOT_APPLICABLE, note="X"
                )
            with pytest.raises(IntegrityError, match="not_applicable_where_it_may_be"):
                with transaction.atomic():
                    TransferItem.objects.filter(transfer__aircraft=hklm, number=number).update(
                        state=ItemState.NOT_APPLICABLE, note="X"
                    )
        with pytest.raises(services.RefusedError, match="Say Why the Item Does Not Apply"):
            services.set_item(item(sample, hklm, 9), state=ItemState.NOT_APPLICABLE)
        with pytest.raises(IntegrityError, match="not_applicable_where_it_may_be"):
            with transaction.atomic():
                TransferItem.objects.filter(transfer__aircraft=hklm, number=9).update(
                    state=ItemState.NOT_APPLICABLE, note=""
                )
        for number in (9, 10):
            services.set_item(
                item(sample, hklm, number), state=ItemState.NOT_APPLICABLE, note="[Reason]"
            )
        with pytest.raises(services.RefusedError, match="Choose Where the Item Stands"):
            services.set_item(item(sample, hklm, 6), state="[Unknown]")
        for altered, constraint in (
            ({"number": 11}, "keeps its transfer and its number"),
            ({"state": "[Unknown]"}, "one_of_the_ten_in_a_known_state"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                TransferItem.objects.filter(transfer__aircraft=hklm, number=6).update(**altered)
        assert services.transfer_line(Aircraft.objects.get(pk=hklm.pk), TODAY).progress == (  # type: ignore[union-attr]
            "6 of 10 Complete"
        )


def test_an_aircraft_is_not_moved_to_the_fleet_with_an_item_still_open(
    sample: Sample, hklm: Aircraft
) -> None:
    """REQ-269. Ours. With every record received G-HKLM still stays out of the Fleet
    while an item of its checklist is open: the service and the database refuse.
    Once it is in the Fleet its checklist is never altered."""
    client = signed_in(sample.lucy)
    post(client, f"/aircraft/{hklm.id}/records-received/", received="18", complete="Yes")
    assert "G-HKLM" not in page(client, "/")
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft = Aircraft.objects.get(pk=hklm.pk)
        assert set(services.stops_the_fleet(aircraft)) == {
            "Records Received and Checked",
            "Continuing Airworthiness Records Review",
            "Records Entered",
            "Maintenance Programme",
            "Bridging Check",
            "Exposition Scope of Work",
        }
        with pytest.raises(aircraft_services.TransferNotCompleteError):
            aircraft_services.complete_transfer(aircraft)
        with pytest.raises(IntegrityError, match="item of its transfer checklist still open"):
            with transaction.atomic():
                Aircraft.objects.filter(pk=hklm.pk).update(
                    stage=Stage.FLEET, records_received=None, records_expected=None
                )
        programme_services.set_up_programme(
            aircraft, basis=Basis.INSTRUCTIONS, reference="[Reference]"
        )
    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        for number, state, note in (
            (5, ItemState.COMPLETE, ""),
            (6, ItemState.COMPLETE, "Lucy Grant"),
            (7, ItemState.COMPLETE, ""),
            (8, ItemState.COMPLETE, ""),
            (9, ItemState.NOT_APPLICABLE, "Programme Not Changed"),
        ):
            services.set_item(item(sample, hklm, number), state=state, note=note)
        # One item left: still refused.
        with pytest.raises(aircraft_services.TransferNotCompleteError):
            aircraft_services.complete_transfer(Aircraft.objects.get(pk=hklm.pk))
        services.set_item(item(sample, hklm, 10), state=ItemState.COMPLETE, note="Revision 8")
    post(client, f"/aircraft/{hklm.id}/records-received/", received="18", complete="Yes")
    assert "G-HKLM" in page(client, "/")
    last = item(sample, hklm, 10)
    refused = post(client, f"/transfers/items/{last.id}/", state="Open", note="")
    assert refused.status_code == 409
    assert "The Checklist of an Aircraft in the Fleet Is Never Altered" in refused.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(IntegrityError, match="in the Fleet is never altered"):
            with transaction.atomic():
                TransferItem.objects.filter(pk=last.pk).update(note="[Altered]")
        with pytest.raises(services.RefusedError, match="Only an Aircraft Being Transferred In"):
            services.start_transfer(Aircraft.objects.get(pk=hklm.pk))


def test_transfer_requires_the_management_contract_to_still_be_in_force(
    sample: Sample, hklm: Aircraft
) -> None:
    from airworthiness_plus.contracts import services as contract_services
    from airworthiness_plus.contracts.models import EndReason

    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft = Aircraft.objects.get(pk=hklm.pk)
        services.sign_baseline(aircraft, by=sample.lucy)
        programme_services.set_up_programme(
            aircraft, basis=Basis.INSTRUCTIONS, reference="[Reference]"
        )
        aircraft_services.record_received(aircraft, 18)
        for number in range(5, 11):
            services.set_item(item(sample, hklm, number), state=ItemState.COMPLETE)
        contract = contract_services.in_force_on(aircraft, TODAY)
        assert contract is not None
        contract_services.end_contract(
            contract, ended_on=date(2026, 11, 17), end_reason=EndReason.OTHER
        )

    response = post(
        signed_in(sample.lucy),
        f"/aircraft/{hklm.id}/records-received/",
        received="18",
        complete="Yes",
    )
    assert response.status_code == 409
    assert "Management Contract, No Contract in Force" in response.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        assert Aircraft.objects.get(pk=hklm.pk).stage == Stage.TRANSFER_IN


def test_a_checklist_is_started_once_and_an_aircraft_without_one_moves_as_before(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-267, REQ-027. Start the Checklist sent twice makes one checklist of ten
    open items. An aircraft transferred in before checklists, with none, still
    moves to the Fleet once every record is received."""
    hklm = fleet["G-HKLM"]
    client = signed_in(sample.planner)
    assert "Checklist Not Started" in page(client, "/transfers/")
    assert post(client, f"/transfers/{hklm.id}/start/").status_code == 302
    twice = post(client, f"/transfers/{hklm.id}/start/")
    assert twice.status_code == 409 and "Already Started" in twice.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        transfer = Transfer.objects.get()
        assert transfer.started_on == TODAY
        states = list(TransferItem.objects.values_list("number", "state", "note"))
        assert states == [(number, "Open", "") for number in range(1, 11)]
        with pytest.raises(RecordsAreNeverDeletedError):
            transfer.save()
        with pytest.raises(IntegrityError, match="transfer_item_one_of_each_number"):
            with transaction.atomic():
                TransferItem.objects.create(organisation=sample.ours, transfer=transfer, number=10)
        with pytest.raises(services.RefusedError, match="Not Started After Today"):
            services.start_transfer(hklm, started_on=date(2026, 11, 19))
    assert "0 of 10 Complete" in page(client, "/transfers/")
    # An aircraft with no checklist: as REQ-027 has always had it.
    with working_for(sample.ours.id, sample.lucy.id):
        other = aircraft_services.add_aircraft(
            organisation=sample.ours,
            registration="G-NEWT",
            type_rating="[Type Rating]",
            owner="[Owner]",
            records_expected=2,
            records_received=2,
        )
        aircraft_services.complete_transfer(other)
        assert Aircraft.objects.get(pk=other.pk).stage == Stage.FLEET


# Set Up Configuration


def test_the_set_up_of_the_sample_on_18_november_2026(sample: Sample, hklm: Aircraft) -> None:
    """REQ-270 to REQ-272. Golden: the six steps for G-HKLM, worked by hand in the
    heading of this file."""
    body = page(signed_in(sample.reader), f"/aircraft/{hklm.id}/set-up-configuration/")
    for step in ("1 Aircraft", "2 Product Structure Template", "3 Major Items",
                 "4 Tracked Positions", "5 Modifications and Repairs Embodied",
                 "6 Review the Configuration Baseline"):  # fmt: skip
        assert f"<h2>{step}</h2>" in body
    assert rows(body, 0) == [
        ["Airframe", "23, 25, 33, 34, 37", "7", "0", "7"],
        ["Engine", "72, 73, 74", "4", "0", "4"],
        ["Propeller", "61", "1", "0", "1"],
    ]
    major = {row[0]: row for row in rows(body, 1)}
    assert major["Engine, Lycoming O-235"][1:3] == [
        "Engine, Lycoming O-235-L2C",
        "[Serial Number Engine G-HKLM]",
    ]
    assert major["Propeller, Fixed Pitch"][4:] == [
        "Not Recorded",
        "2,000.0 Hours or 72 Months, Manufacturer Recommendation",
        "Calendar Limit Not Worked Out Until the Day It Was New or Last Overhauled Is Recorded",
    ]
    tracked = {row[0]: row[1:6] for row in rows(body, 2)}
    assert len(tracked) == 12
    assert tracked["Right Magneto"] == [
        "[Part Number]", "", "Engine Logbook, Volume 1 Requested", "Not Recorded",
        "Engine, Chapter 74",
    ]  # fmt: skip
    assert tracked["Landing Light"] == [
        "[Part Number]", "", "Physical Survey, 12 November 2026", "Needs a Recorded Change",
        "Airframe, Chapter 33",
    ]  # fmt: skip
    assert tracked["Mode S Transponder"][3] == "Recorded"
    assert sorted(status for *_, status, _ in tracked.values()) == (
        ["Needs a Recorded Change"] + ["Not Recorded"] * 4 + ["Recorded"] * 7
    )
    assert sorted(row[:3] for row in rows(body, 3)) == [
        ["8.33 Kilohertz Radio", "Standard Change, [Standard Change Reference 4]",
         "Very High Frequency Radio, 8.33 Kilohertz"],
        ["Mode S Transponder", "Standard Change, [Standard Change Reference 3]",
         "Mode S Transponder"],
    ]  # fmt: skip
    assert "<dt>Positions Recorded</dt><dd>8 of 12 Tracked, 12 in Template</dd>" in body
    assert "<dt>Changes and Repairs</dt><dd>2</dd>" in body
    assert "<dt>Open Items</dt><dd>6</dd>" in body
    assert "<dt>Baseline Date</dt><dd>18 November 2026</dd>" in body
    review = body.split("<h2>6 Review the Configuration Baseline</h2>", 1)[1]
    assert set(re.findall(r"<li>([^<]+)</li>", review.split("</ul>", 1)[0])) == OPEN_ITEMS
    assert set(found(sample, hklm).open_items) == OPEN_ITEMS
    assert "A Configuration Baseline Is Not Signed With Items Still Open" in body
    # Nobody is offered the signature while an item is open.
    assert "Sign Configuration Baseline" not in page(
        signed_in(sample.lucy), f"/aircraft/{hklm.id}/set-up-configuration/"
    )


def test_a_baseline_is_not_signed_with_items_still_open(
    sample: Sample, hklm: Aircraft, fleet: dict[str, Aircraft]
) -> None:
    """REQ-273. Ours: the signature is refused, naming what is open, by the service
    and by the database. Each kind of open item stops it on its own. An aircraft
    with no position recorded has no baseline to sign."""
    client = signed_in(sample.lucy)
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(services.RefusedError, match="With Positions Recorded"):
            services.sign_baseline(Aircraft.objects.get(pk=fleet["G-ABCD"].pk), by=sample.lucy)
        with pytest.raises(IntegrityError, match="with positions recorded"):
            with transaction.atomic():
                Baseline.objects.create(
                    organisation=sample.ours,
                    aircraft=fleet["G-ABCD"],
                    signed_on=TODAY,
                    signed_by=sample.lucy,
                )
    sign = f"/aircraft/{hklm.id}/set-up-configuration/sign/"
    refused = post(client, sign)
    assert refused.status_code == 409
    assert "Items Still Open:" in refused.content.decode()
    assert "Right Magneto, Not Recorded" in refused.content.decode()
    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(IntegrityError, match="not signed with items still open"):
            with transaction.atomic():
                Baseline.objects.create(
                    organisation=sample.ours, aircraft=hklm, signed_on=TODAY, signed_by=sample.lucy
                )
        assert Baseline.objects.count() == 0
    close_every_open_item(sample, hklm)
    assert found(sample, hklm).open_items == ()
    # Each kind, put back on its own, stops the signature again.
    with working_for(sample.ours.id, sample.lucy.id):
        light = Position.objects.get(aircraft=hklm, name="Landing Light")
        services.record_position(
            light, source=light.source, part_number=light.part_number, needs_change=True
        )
        assert found(sample, hklm).open_items == ("Landing Light, Needs a Recorded Change",)
        with pytest.raises(services.RefusedError, match="Landing Light, Needs a Recorded Change"):
            services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        with pytest.raises(IntegrityError, match="not signed with items still open"):
            with transaction.atomic():
                Baseline.objects.create(
                    organisation=sample.ours, aircraft=hklm, signed_on=TODAY, signed_by=sample.lucy
                )
        services.record_position(
            light, source=light.source, part_number=light.part_number, needs_change=False
        )
        extra = services.add_position(
            Aircraft.objects.get(pk=hklm.pk),
            product=Product.AIRFRAME,
            chapter=34,
            name="[Altimeter]",
            tracked=True,
        )
        with pytest.raises(services.RefusedError, match=r"\[Altimeter\], Not Recorded"):
            services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        services.record_position(extra, source="[Logbook]")
        # A major item with no component recorded is open too.
        engine = Position.objects.get(aircraft=hklm, name="Engine, Lycoming O-235")
        services.record_position(
            engine, source=engine.source, part_number=engine.part_number,
            serial_number=engine.serial_number,
        )  # fmt: skip
        with pytest.raises(services.RefusedError, match="No Component Recorded"):
            services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        assert Baseline.objects.count() == 0


def test_a_baseline_requires_a_component_for_untracked_major_positions(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    with working_for(sample.ours.id, sample.lucy.id):
        aircraft = fleet["G-ABCD"]
        services.add_position(
            aircraft, product=Product.ENGINE, chapter=72, name="Engine", major=True
        )
        with pytest.raises(services.RefusedError, match="Engine, No Component Recorded"):
            services.sign_baseline(aircraft, by=sample.lucy)


def test_a_removed_propeller_cannot_be_signed_as_fitted(sample: Sample, hklm: Aircraft) -> None:
    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        propeller = position(sample, hklm, "Propeller, Fixed Pitch").component
        assert propeller is not None
        fitting = component_services.current_installation(propeller)
        assert fitting is not None
        component_services.remove_component(
            fitting,
            removed_on=TODAY,
            airframe_hours_removed=D("3410.0"),
            airframe_cycles_removed=0,
            removal_reason="Removed for Maintenance",
        )
        with pytest.raises(services.RefusedError, match="Component No Longer Fitted"):
            services.sign_baseline(hklm, by=sample.lucy)
    assert "Component No Longer Fitted" in page(
        signed_in(sample.reader), f"/aircraft/{hklm.id}/configuration/"
    )


def test_a_signed_baseline_keeps_what_it_showed(sample: Sample, hklm: Aircraft) -> None:
    """REQ-274. Signed by Lucy Grant on 18 November 2026 with 12 positions and 3
    changes. The database wrote who signed, the organisation, the aircraft and every
    position and change. Afterwards a position is changed, the aircraft is given
    another registration and the signatory another name: the baseline shows what
    it showed. It is signed once a day, and never changed."""
    close_every_open_item(sample, hklm)
    client = signed_in(sample.lucy)
    sign = f"/aircraft/{hklm.id}/set-up-configuration/sign/"
    assert "Sign Configuration Baseline" in page(
        client, f"/aircraft/{hklm.id}/set-up-configuration/"
    )
    signed = post(client, sign)
    assert signed.status_code == 302
    twice = post(client, sign)
    assert twice.status_code == 409 and "Already Signed for This Aircraft Today" in (
        twice.content.decode()
    )
    with working_for(sample.ours.id, sample.lucy.id):
        baseline = Baseline.objects.get()
        assert (baseline.signed_by_name, baseline.organisation_name) == (
            "Lucy Grant",
            "[Your Organisation]",
        )
        assert (baseline.aircraft_registration, baseline.type_rating, baseline.signed_on) == (
            "G-HKLM",
            "Piper PA-38 Series (Lycoming)",
            TODAY,
        )
        kept = services.signed_positions(baseline)
        assert len(kept) == 12
        magneto = next(one for one in kept if one["name"] == "Right Magneto")
        assert (magneto["serial_number"], magneto["source"], magneto["chapter"]) == (
            "[Serial Number]",
            "[Logbook]",
            74,
        )
        light = next(one for one in kept if one["name"] == "Landing Light")
        assert light["change"] == "Light-Emitting Diode Landing Light"
        assert sorted(str(one["title"]) for one in services.signed_changes(baseline)) == [
            "8.33 Kilohertz Radio",
            "Light-Emitting Diode Landing Light",
            "Mode S Transponder",
        ]
        # What the application sends for them is not what is kept.
        with pytest.raises(IntegrityError, match="baseline_one_for_an_aircraft_on_a_day"):
            with transaction.atomic():
                Baseline.objects.create(
                    organisation=sample.ours, aircraft=hklm, signed_on=TODAY, signed_by=sample.lucy
                )
        other = Baseline.objects.create(
            organisation=sample.ours,
            aircraft=hklm,
            signed_on=date(2026, 11, 17),
            signed_by=sample.lucy,
            signed_by_name="[Somebody Else]",
            organisation_name="[Another]",
            aircraft_registration="G-ZZZZ",
            positions="[]",
            changes="[]",
        )
        other.refresh_from_db()
        assert (other.signed_by_name, other.organisation_name, other.aircraft_registration) == (
            "Lucy Grant",
            "[Your Organisation]",
            "G-HKLM",
        )
        assert len(services.signed_positions(other)) == 12
        # Later changes.
        services.record_position(
            Position.objects.get(aircraft=hklm, name="Right Magneto"),
            source="[Another Source]",
            serial_number="[Another Serial]",
        )
        Aircraft.objects.filter(pk=hklm.pk).update(registration="G-NEWR")
        with pytest.raises(RecordsAreNeverDeletedError):
            baseline.save()
        with pytest.raises(Exception, match="permission denied"), transaction.atomic():
            Baseline.objects.filter(pk=baseline.pk).update(signed_by_name="[Altered]")
    with working_for(sample.ours.id, sample.administrator.id):
        User.objects.filter(pk=sample.lucy.pk).update(full_name="[Renamed]")
    body = page(signed_in(sample.reader), f"/configuration/baselines/{baseline.id}/")
    assert "<h1>Configuration Baseline, G-HKLM</h1>" in body
    assert "<dt>Signed By</dt><dd>Lucy Grant, Continuing Airworthiness Manager</dd>" in body
    assert "<dt>Baseline Date</dt><dd>18 November 2026</dd>" in body
    shown = {row[2]: row for row in rows(body, 0)}
    assert shown["Right Magneto"] == [
        "Engine", "74", "Right Magneto", "[Part Number]", "[Serial Number]", "[Logbook]", "",
    ]  # fmt: skip
    assert "[Another Serial]" not in body and "G-NEWR" not in body and "[Renamed]" not in body
    set_up = page(signed_in(sample.reader), f"/aircraft/{hklm.id}/set-up-configuration/")
    assert f'<a href="/configuration/baselines/{baseline.id}/">Baseline Signed by Lucy Grant, ' in (
        set_up
    )


REFUSED_POSITIONS: tuple[tuple[dict[str, Any], str], ...] = (
    ({"name": " "}, "Has a Name"),
    ({"product": "[Unknown]"}, "Airframe, an Engine or a Propeller"),
    ({"chapter": 0}, "From 1 to 99"),
    ({"chapter": 100}, "From 1 to 99"),
    ({"major": True}, "A Major Item Is an Engine or a Propeller"),
    ({"name": "Landing Light", "chapter": 33}, "Already Recorded for the Aircraft"),
)


@pytest.mark.parametrize(("altered", "reason"), REFUSED_POSITIONS)
def test_what_cannot_be_true_of_a_position_is_refused(
    sample: Sample, hklm: Aircraft, altered: dict[str, Any], reason: str
) -> None:
    """REQ-270. A position is recorded once for an aircraft, in a product and a chapter."""
    given: dict[str, Any] = {"product": Product.AIRFRAME, "chapter": 34, "name": "[Altimeter]"}
    with (
        working_for(sample.ours.id, sample.planner.id),
        pytest.raises(services.RefusedError, match=reason),
    ):
        services.add_position(Aircraft.objects.get(pk=hklm.pk), **{**given, **altered})
    with working_for(sample.ours.id, sample.reader.id):
        assert Position.objects.count() == 12


def test_what_is_fitted_at_a_position_belongs_to_its_aircraft(
    sample: Sample, hklm: Aircraft, fleet: dict[str, Aircraft]
) -> None:
    """REQ-271. A change given is a change of the same aircraft and a component given
    is fitted to it now: the service and, for the change, the database refuse any
    other. What is recorded says where it was read. A position keeps its aircraft."""
    with working_for(sample.ours.id, sample.planner.id):
        elsewhere = modification_services.record_change(
            Aircraft.objects.get(pk=fleet["G-ABCD"].pk),
            title="[Change]",
            route=Route.STANDARD_CHANGE,
            mass_effect=D("0.0"),
            embodied_on=TODAY,
        )
        loose = component_services.add_component(
            sample.ours, name="[Loose]", basis="No Limit Recorded"
        )
        pump = Position.objects.get(aircraft=hklm, name="Vacuum Pump")
        for values, reason in (
            ({"source": " "}, "Say Where What Is Fitted Was Read"),
            ({"source": "X", "change": elsewhere}, "Belongs to Another Aircraft"),
            ({"source": "X", "component": loose}, "Not Fitted to This Aircraft"),
        ):
            with pytest.raises(services.RefusedError, match=reason):
                services.record_position(pump, **values)
        for altered, constraint in (
            ({"recorded": True, "source": "X", "change": elsewhere}, "change of its own aircraft"),
            ({"recorded": True, "source": ""}, "position_recorded_says_its_source"),
            ({"serial_number": "X"}, "position_recorded_says_its_source"),
            ({"needs_change": True}, "position_recorded_says_its_source"),
            ({"aircraft": fleet["G-ABCD"]}, "A position keeps its aircraft"),
            ({"chapter": 0}, "position_has_a_name_a_product_and_a_chapter"),
            ({"product": "[Unknown]"}, "position_has_a_name_a_product_and_a_chapter"),
            ({"name": "Landing Light", "chapter": 33}, "position_recorded_once_for_an_aircraft"),
        ):
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Position.objects.filter(pk=pump.pk).update(**altered)
        services.record_position(pump, source="[Logbook]", part_number="[Part]")
        with pytest.raises(services.RefusedError, match="Already Recorded"):
            services.record_position(pump, source="[Logbook]", part_number="[Part]")
        assert Position.objects.get(pk=pump.pk).status == "Recorded"


# Roles, other organisations and the export


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_run_a_transfer_and_set_up_a_configuration(
    sample: Sample, hklm: Aircraft, role: str
) -> None:
    """REQ-006, REQ-275. The checklist: the Continuing Airworthiness Manager and
    Planning and Records, as for aircraft. Positions: the same two, under Record
    Aircraft Configuration. The baseline is signed by the Continuing Airworthiness
    Manager alone, as the board has it. Every role reads."""
    close_every_open_item(sample, hklm)
    client = signed_in(getattr(sample, role))
    records = role in ("lucy", "planner")
    transfers = page(client, "/transfers/").split("<main", 1)[1]
    set_up = page(client, f"/aircraft/{hklm.id}/set-up-configuration/").split("<main", 1)[1]
    assert ("<form" in transfers) == records
    assert ("Add a Position" in set_up) == records
    assert ("Sign Configuration Baseline" in set_up) == (role == "lucy")
    answers = [
        post(client, f"/transfers/items/{item(sample, hklm, 6).id}/", state="Complete", note="X"),
        post(
            client,
            f"/aircraft/{hklm.id}/set-up-configuration/positions/add/",
            product="Airframe",
            chapter="34",
            name="[Altimeter]",
        ),
        post(
            client,
            f"/configuration/positions/{position(sample, hklm, 'Carburettor').id}/record/",
            source="[Another Logbook]",
        ),
    ]
    assert [answer.status_code for answer in answers] == [302 if records else 403] * 3
    signed = post(client, f"/aircraft/{hklm.id}/set-up-configuration/sign/")
    assert signed.status_code == (302 if role == "lucy" else 403)
    with working_for(sample.ours.id, sample.reader.id):
        assert Baseline.objects.count() == (1 if role == "lucy" else 0)
    if role == "planner":
        with as_owner():
            refused = AccessEntry.objects.filter(kind="Action Refused")
            assert list(refused.values_list("detail", flat=True)) == ["Sign Configuration Baseline"]


def test_another_organisations_transfers_and_configurations_are_not_found(
    sample: Sample, hklm: Aircraft
) -> None:
    """REQ-003, REQ-002."""
    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        baseline = services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        transfer = Transfer.objects.get()
    stranger = signed_in(sample.stranger)
    assert get(stranger, f"/aircraft/{hklm.id}/set-up-configuration/").status_code == 404
    assert get(stranger, f"/configuration/baselines/{baseline.id}/").status_code == 404
    for path, values in (
        (f"/transfers/{hklm.id}/start/", {}),
        (f"/transfers/items/{item(sample, hklm, 6).id}/", {"state": "Complete"}),
        (f"/aircraft/{hklm.id}/set-up-configuration/positions/add/",
         {"product": "Airframe", "chapter": "34", "name": "X"}),
        (f"/configuration/positions/{position(sample, hklm, 'Carburettor').id}/record/",
         {"source": "X"}),
        (f"/aircraft/{hklm.id}/set-up-configuration/sign/", {}),
    ):  # fmt: skip
        assert post(stranger, path, **values).status_code == 404, path
    assert "G-HKLM" not in page(stranger, "/transfers/")
    with working_for(sample.other.id, sample.stranger.id):
        makes = (
            lambda: Transfer.objects.create(
                organisation=sample.other, aircraft=hklm, started_on=TODAY),
            lambda: TransferItem.objects.create(
                organisation=sample.other, transfer_id=transfer.id, number=1),
            lambda: Position.objects.create(
                organisation=sample.other, aircraft=hklm, product=Product.AIRFRAME, chapter=34,
                name="X"),
            lambda: Baseline.objects.create(
                organisation=sample.other, aircraft=hklm, signed_on=date(2026, 11, 1),
                signed_by=sample.stranger),
        )  # fmt: skip
        for make in makes:
            with pytest.raises(Exception, match=r"own organisation|with positions recorded"):
                with transaction.atomic():
                    make()


def test_the_export_of_an_aircraft_holds_its_transfer_its_positions_and_its_baseline(
    sample: Sample, hklm: Aircraft, fleet: dict[str, Aircraft]
) -> None:
    """REQ-134. G-HKLM: its transfer and ten items, its 12 positions and its signed
    baseline. G-ABCD: none."""
    close_every_open_item(sample, hklm)
    with working_for(sample.ours.id, sample.lucy.id):
        services.sign_baseline(Aircraft.objects.get(pk=hklm.pk), by=sample.lucy)
        ours = build_export(sample.ours, by=sample.lucy, aircraft=hklm)
        abcd = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-ABCD"])

    def read(export: object, name: str) -> list[dict[str, object]]:
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:  # type: ignore[attr-defined]
            held: list[dict[str, object]] = json.loads(archive.read(f"records/{name}.json"))
            return held

    assert len(read(ours, "configuration_transfer")) == 1
    assert sorted(int(str(one["number"])) for one in read(ours, "configuration_transferitem")) == (
        list(range(1, 11))
    )
    assert len(read(ours, "configuration_position")) == 12
    (baseline,) = read(ours, "configuration_baseline")
    assert (baseline["signed_by_name"], baseline["aircraft_registration"]) == (
        "Lucy Grant",
        "G-HKLM",
    )
    assert len(json.loads(str(baseline["positions"]))) == 12
    for table in ("transfer", "transferitem", "position", "baseline"):
        assert read(abcd, f"configuration_{table}") == []
