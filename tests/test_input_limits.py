"""Odd input is refused on the page, never a server error.

Review of 20 November 2026, finding 7. Each case below gave a server
error (500) and wrote a traceback; each is now refused with a reason, or,
where it is sound, accepted.
"""

import importlib
import pkgutil
from collections.abc import Iterator
from datetime import date

import pytest
from django import forms
from django.http import HttpResponse
from django.test import Client

import airworthiness_plus
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft, CounterKind
from airworthiness_plus.directives.models import Directive
from airworthiness_plus.history.session import working_for
from airworthiness_plus.imports.models import Load, LoadedValue, ValueCheck
from airworthiness_plus.interface.forms import LARGEST_WHOLE_NUMBER, Form
from airworthiness_plus.programme import due
from airworthiness_plus.programme.models import Task
from airworthiness_plus.sample import build
from airworthiness_rules import dates
from tests.support import (
    TODAY,
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    make_sample,
    signed_in,
)
from tests.test_imports import fleet_load  # noqa: F401

pytestmark = pytest.mark.django_db
TOO_LARGE = str(LARGEST_WHOLE_NUMBER + 1)


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


def post(client: Client, path: str, **data: str) -> HttpResponse:
    return client.post(path, data, secure=True)  # type: ignore[return-value]


def every_form() -> Iterator[type[Form]]:
    for module in pkgutil.walk_packages(airworthiness_plus.__path__, "airworthiness_plus."):
        if module.name.endswith("forms"):
            importlib.import_module(module.name)
    waiting = list(Form.__subclasses__())
    while waiting:
        form = waiting.pop()
        waiting += form.__subclasses__()
        yield form


def test_every_whole_number_on_every_form_has_a_limit_the_database_holds() -> None:
    """A whole number too large for the database is refused on the form."""
    forms_seen = list(every_form())
    assert len(forms_seen) > 30
    for form in forms_seen:
        for name, field in form.base_fields.items():
            if type(field) is forms.IntegerField:
                assert field.max_value is not None, f"{form.__name__}.{name}"
                assert field.max_value <= LARGEST_WHOLE_NUMBER, f"{form.__name__}.{name}"


def test_cycles_too_large_for_the_database_are_refused_on_each_page(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """Hours and cycles with Confirm ticked, a directive's first cycles, and
    work on an aircraft with no reading yet."""
    client = signed_in(sample.lucy)
    abcd, ejkl = fleet["G-ABCD"], fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.lucy.id):
        counter = abcd.counters.get(kind=CounterKind.AIRFRAME)
        directives = build.add_directives(sample, fleet)
        undecided = Directive.objects.get(pk=directives[3].pk)
    entered = post(
        client,
        f"/aircraft/{abcd.id}/hours-and-cycles/",
        counter=str(counter.id),
        dated="2026-11-18",
        hours="6413.0",
        cycles=TOO_LARGE,
        confirmed="on",
    )
    decided = post(
        client,
        f"/aircraft/{fleet['G-BXYZ'].id}/directives/{undecided.id}/decide/",
        decision="Applicable",
        basis="[Basis]",
        first_cycles=TOO_LARGE,
    )
    worked = post(
        client,
        f"/aircraft/{ejkl.id}/work/add/",
        description="[Work]",
        dated="2026-11-18",
        hours="0",
        cycles=TOO_LARGE,
    )
    for response in (entered, decided, worked):
        assert response.status_code == 200
        assert f"less than or equal to {LARGEST_WHOLE_NUMBER}" in response.content.decode()


def test_a_correction_of_another_counters_entry_is_refused(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-025. The page offered every entry of the aircraft; the database
    refused one of another counter with a server error."""
    client = signed_in(sample.planner)
    cdef = fleet["G-CDEF"]
    with working_for(sample.ours.id, sample.planner.id):
        engine = cdef.counters.get(kind=CounterKind.ENGINE)
        airframe = cdef.counters.get(kind=CounterKind.AIRFRAME)
        engine_entry = engine.entries.get()
        current = aircraft_services.current_reading(airframe)
    assert current is not None
    response = post(
        client,
        f"/aircraft/{cdef.id}/hours-and-cycles/",
        counter=str(airframe.id),
        dated="2026-11-18",
        hours=str(current.hours),
        cycles=str(current.cycles),
        supersedes=str(engine_entry.id),
    )
    assert response.status_code == 200
    # The entries offered are named as a person reads them.
    assert "UtilisationEntry object" not in response.content.decode()
    assert "Engine 1, 18 November 2026, 1,780.0 Hours, 0 Cycles" in response.content.decode()
    assert "A Correction Is of an Entry of the Same Counter" in response.content.decode()


def test_a_source_value_holding_a_nul_character_is_refused(
    sample: Sample,
    fleet_load: Load,  # noqa: F811
) -> None:
    """REQ-171. What the source says is written by hand on the check."""
    client = signed_in(sample.planner)
    with working_for(sample.ours.id, sample.planner.id):
        value = LoadedValue.objects.filter(load=fleet_load)[0]
    response = post(
        client, f"/imports/{fleet_load.id}/check/", **{f"source_{value.id}": "62\x0012.6"}
    )
    assert response.status_code == 200
    assert "A Value Holds a Character That Cannot Be Recorded" in response.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        assert ValueCheck.objects.count() == 0


@pytest.mark.parametrize("unit", ["months", "days"])
def test_an_interval_at_the_largest_whole_number_is_never_a_server_error(
    sample: Sample, fleet: dict[str, Aircraft], unit: str
) -> None:
    """A calendar interval so long its due date is past the year 9999 is
    refused when the task is added, or shown as cannot be calculated."""
    client = signed_in(sample.lucy)
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        counter = abcd.counters.get(kind=CounterKind.AIRFRAME)
    added = post(
        client,
        f"/aircraft/{abcd.id}/programme/tasks/add/",
        title="[Long Interval]",
        kind="Programme Task",
        counter=str(counter.id),
        source="[Source]",
        **{f"interval_{unit}": str(LARGEST_WHOLE_NUMBER)},
        starts_dated="2026-11-01",
        starts_hours="6400.0",
        starts_cycles="0",
    )
    assert added.status_code == 200
    assert "The Interval Runs Past 31 December 9999" in added.content.decode()
    for path in (f"/aircraft/{abcd.id}/programme/", "/", f"/aircraft/{abcd.id}/"):
        assert client.get(path, secure=True).status_code == 200, path


def test_a_date_past_the_calendar_is_its_own_error_and_the_last_day_is_reached() -> None:
    """The rules say when a date cannot be given, and do not fail on the way."""
    assert dates.add_months(date(9999, 11, 30), 1) == date(9999, 12, 30)
    assert dates.add_months(date(9999, 1, 31), 11) == date(9999, 12, 31)
    assert dates.add_days(date(9999, 12, 30), 1) == date(9999, 12, 31)
    for start, months in ((date(9999, 12, 1), 1), (date(2026, 11, 18), LARGEST_WHOLE_NUMBER)):
        with pytest.raises(dates.BeyondCalendarError):
            dates.add_months(start, months)
    for start, days in ((date(2026, 11, 18), LARGEST_WHOLE_NUMBER), (date(9999, 12, 31), 1)):
        with pytest.raises(dates.BeyondCalendarError):
            dates.add_days(start, days)
    with pytest.raises(dates.BeyondCalendarError):
        dates.add_years(date(9999, 12, 31), 1)


def test_a_stored_task_past_the_calendar_cannot_be_calculated_and_comes_first(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """A task already held, from before this check, is shown as one that
    cannot be calculated, which the Fleet shows first, never as not due."""
    abcd = fleet["G-ABCD"]
    with working_for(sample.ours.id, sample.lucy.id):
        task = Task.objects.filter(programme__aircraft=abcd).first()
        assert task is not None
        Task.objects.filter(pk=task.pk).update(
            interval_hours=None, interval_days=LARGEST_WHOLE_NUMBER
        )
        lines = due.due_lines(Aircraft.objects.get(pk=abcd.pk), TODAY)
    assert [line.problem for line in lines] == [
        "A Limit Falls After 31 December 9999 and Cannot Be Calculated"
    ]
