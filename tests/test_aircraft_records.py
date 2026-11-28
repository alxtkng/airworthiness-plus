"""The structural register and technical log keep source records and attribution."""

import io
import json
from datetime import timedelta
from decimal import Decimal
from uuid import UUID
from zipfile import ZipFile

import pytest
from django.db import DatabaseError, transaction
from django.test import Client
from django.urls import reverse

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.middleware import VERIFIED_AT_KEY
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.components.models import Basis, Component
from airworthiness_plus.defects.models import AircraftDrawing, DamageEntry, FlightReport
from airworthiness_plus.exports.verify import verify
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.programme import services as programme_services
from airworthiness_rules.intervals import Interval, TaskKind
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    get,
    page,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db


def _save(client: Client, path: str, **values: str) -> str:
    response = post(client, path, **values)
    assert response.status_code == 302, response.content.decode()
    return str(response.headers["Location"])


def _identifier(path: str) -> UUID:
    return UUID(path.rstrip("/").rsplit("/", 1)[-1])


def _export(client: Client, aircraft: Aircraft) -> ZipFile:
    response = post(client, reverse("export_aircraft", args=[aircraft.id]))
    assert response.status_code == 200
    assert verify(response.content).problems == ()
    return ZipFile(io.BytesIO(response.content))


def test_damage_revisions_preserve_physical_reference_and_linked_records(sample: Sample) -> None:
    fleet = add_sample_fleet(sample)
    programme = add_sample_programmes(sample, fleet)["G-FMNO"].programme
    aircraft, other = fleet["G-FMNO"], fleet["G-CDEF"]
    client = signed_in(sample.planner)
    with working_for(sample.ours.id, sample.planner.id):
        repair = programme_services.record_work(
            aircraft,
            description="Lightning damage repair",
            dated=TODAY,
            hours=Decimal("4950.2"),
            cycles=0,
        )
        task = programme_services.add_task(
            programme,
            title="Repeat Frame 17 inspection",
            kind=TaskKind.PROGRAMME_TASK,
            counter=aircraft.counters.get(kind=CounterKind.AIRFRAME),
            source="SYNTHETIC-SRM 51-01, rev 1",
            interval=Interval(hours=Decimal("25")),
            starts=repair.reading,
        )
    drawing_a = _save(
        client,
        reverse("record_damage_drawing", args=[aircraft.id]),
        reference="D-100",
        view="Front",
        revision="A",
        outline="5,10 90,10 50,80",
    )
    finding = {
        "title": "Lightning strike finding",
        "found_on": "2026-11-18",
        "frame_or_zone": "Frame 17, Zone 2",
        "dimensions": "15 x 5 mm",
        "evidence": "SYNTHETIC-IMAGE-01",
        "applicable_reference": "SYNTHETIC-SRM 51-01, rev 1",
        "disposition": "Repaired, recurring inspection required",
        "marker_x": "30",
        "marker_y": "20",
        "repair": str(repair.id),
        "follow_up": str(task.id),
        "drawing": str(_identifier(drawing_a)),
    }
    original = _save(client, reverse("record_damage_entry", args=[aircraft.id]), **finding)
    body = page(client, original)
    assert f"{drawing_a}#marker-{_identifier(original)}" in body
    assert f"#work-{repair.id}" in body
    assert f"#task-{task.id}" in body
    assert page(client, drawing_a).count(f'href="{original}"') == 2

    drawing_b = _save(
        client,
        reverse("revise_damage_drawing", args=[aircraft.id, _identifier(drawing_a)]),
        revision="B",
        outline="5,10 90,10 55,85",
    )
    assert original in page(client, drawing_a)
    assert "No Markers Recorded for This Revision" in page(client, drawing_b)
    finding.update(drawing=str(_identifier(drawing_b)), marker_x="40")
    remapped = _save(
        client,
        reverse("revise_damage_entry", args=[aircraft.id, _identifier(original)]),
        **finding,
    )
    assert "Frame 17, Zone 2" in page(client, remapped)
    assert original in page(client, remapped)
    assert remapped in page(client, drawing_b)
    assert "SYNTHETIC-IMAGE-01" in page(client, original)

    outsider = signed_in(sample.stranger)
    for path in (drawing_a, drawing_b, original, remapped):
        assert get(outsider, path).status_code == 404
    wrong_aircraft = reverse("damage_drawing", args=[other.id, _identifier(drawing_a)])
    assert get(client, wrong_aircraft).status_code == 404
    response = post(client, reverse("record_damage_entry", args=[other.id]), **finding)
    assert response.status_code == 200
    assert "Select a valid choice" in response.content.decode()

    with working_for(sample.ours.id, sample.planner.id):
        with pytest.raises(DatabaseError), transaction.atomic():
            DamageEntry.objects.filter(pk=_identifier(original)).update(frame_or_zone="Changed")
        assert len(Event.of(DamageEntry.objects.get(pk=_identifier(original)))) == 1
        assert AircraftDrawing.objects.get(pk=_identifier(drawing_b)).supersedes_id == _identifier(
            drawing_a
        )
    with _export(client, aircraft) as archive:
        records = {
            row["id"]: row for row in json.loads(archive.read("records/defects_damageentry.json"))
        }
        latest = records[str(_identifier(remapped))]
        before = records[str(_identifier(original))]
        assert latest["supersedes_id"] == before["id"]
        assert before["drawing_id"] == str(_identifier(drawing_a))
        assert latest["drawing_id"] == str(_identifier(drawing_b))
        assert latest["frame_or_zone"] == before["frame_or_zone"] == "Frame 17, Zone 2"
        assert latest["repair_id"] == before["repair_id"] == str(repair.id)
        assert latest["follow_up_id"] == before["follow_up_id"] == str(task.id)


def test_technical_log_uses_structured_parts_and_refuses_unauthorised_transcription(
    sample: Sample,
) -> None:
    aircraft = add_sample_fleet(sample)["G-FMNO"]
    with working_for(sample.ours.id, sample.planner.id):
        linked = Component.objects.create(
            organisation=sample.ours, name="Starter", part_number="3291556-1", basis=Basis.NONE
        )
        unrelated = Component.objects.create(
            organisation=sample.ours,
            name="Other starter",
            part_number="3291556-2",
            basis=Basis.NONE,
        )
    client = signed_in(sample.planner)
    flight = _save(
        client,
        reverse("record_technical_log_flight", args=[aircraft.id]),
        reference="SYNTH 18/1",
        flown_on="2026-11-18",
        departure="EGKA",
        arrival="EGKB",
    )
    report_form = reverse(
        "transcribe_technical_log_report", args=[aircraft.id, _identifier(flight)]
    )
    data = {
        "kind": "Pilot Report",
        "chapter": "80",
        "section": "11",
        "component": str(linked.id),
        "source_reference": "PILOT-001",
        "reporter": "Original pilot",
        "report": "  Starter did not engage.\r\nSecond attempt normal.  ",
        "confirmed": "on",
        "recorded_by": str(sample.lucy.id),
        "recorded_by_id": str(sample.lucy.id),
        "recorder_name": sample.lucy.full_name,
    }
    reader = signed_in(sample.reader)
    session = reader.session
    session[VERIFIED_AT_KEY] = sign_in.current_time().isoformat()
    session.save()
    assert post(reader, report_form, **data).status_code == 403

    session = client.session
    session[VERIFIED_AT_KEY] = (sign_in.current_time() - timedelta(minutes=20)).isoformat()
    session.save()
    prompt = post(client, report_form, **data)
    assert prompt.status_code == 200
    assert "Verify to Transcribe the Report" in prompt.content.decode()
    assert "Cancel" in prompt.content.decode()
    assert get(client, reverse("dashboard")).status_code == 200
    with working_for(sample.ours.id, sample.planner.id):
        assert FlightReport.objects.count() == 0

    session = client.session
    session[VERIFIED_AT_KEY] = sign_in.current_time().isoformat()
    session.save()
    pilot = _save(client, report_form, **data)
    assert _save(client, report_form, **data) == pilot
    conflict = post(client, report_form, **{**data, "report": "Changed wording"})
    assert conflict.status_code == 200
    assert "This source already identifies a report." in conflict.content.decode()
    finding = _save(
        client,
        report_form,
        **{
            **data,
            "kind": "Maintenance Finding",
            "source_reference": "MX-001",
            "reporter": "Engineer",
        },
    )
    _save(
        client,
        report_form,
        **{**data, "component": str(unrelated.id), "source_reference": "OTHER-PART"},
    )
    _save(
        client,
        report_form,
        **{
            **data,
            "component": "",
            "report": "3291556-1 is a text mention only",
            "source_reference": "TEXT-ONLY",
        },
    )
    log = page(client, reverse("technical_log", args=[aircraft.id]) + "?chapter=80&part=3291556-1")
    assert pilot in log and finding in log
    assert "OTHER-PART" not in log and "TEXT-ONLY" not in log
    assert get(signed_in(sample.stranger), pilot).status_code == 404
    with _export(client, aircraft) as archive:
        records = json.loads(archive.read("records/defects_flightreport.json"))
        result = next(row for row in records if row["id"] == str(_identifier(pilot)))
        assert result["reporter"] == "Original pilot"
        assert result["report"] == data["report"]
        assert result["recorded_by_id"] == str(sample.planner.id)
        assert result["recorder_name"] == sample.planner.full_name
        assert result["source_reference"] == "PILOT-001"
        assert result["flight_id"] == str(_identifier(flight))
        assert result["component_id"] == str(linked.id)
        components = json.loads(archive.read("records/components_component.json"))
        assert str(linked.id) in {row["id"] for row in components}
