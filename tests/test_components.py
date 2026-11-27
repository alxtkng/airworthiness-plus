"""Components and Life Limits (REQ-230 to REQ-239).

The Components board, with the sample of design-system/SampleData.md,
Components. Today in the sample is 18 November 2026. ML.A.503 and
ML.A.305(e) were read in the UK text on 27 November 2026.

By hand, for 18 November 2026, a lead time of 30 days and 10.0 hours:

- G-DGHI engine, on condition: 2,140.0 hours; review at 9,900.0, 25.7
  hours left. G-DGHI has no planning utilisation, so it cannot be placed by
  a day and comes first.
- G-CDEF's own propeller: off-wing, 1,412.0 hours, due back 25 November,
  7 days: Due Soon.
- G-ABCD battery: 28 February 2027, 102 days. G-BXYZ fire extinguisher:
  31 March 2027, 133 days.
- G-CDEF engine: 1,780.0 hours, 220.0 left, 366 days at 0.6 hours a day.
- G-ABCD vacuum pump: 182.0 hours, 318.0 left, 397 days at 0.8.
- The loan propeller on G-CDEF has no limit recorded and comes last.
- 7 tracked, 1 off-wing, 1 on condition, 3 due in 6 months (the G-DGHI
  engine, the battery and the fire extinguisher).
"""

import io
import json
import re
import zipfile
from datetime import date
from decimal import Decimal
from typing import Any

import pytest
from django.db import IntegrityError, connection, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts import sign_in
from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.components import services
from airworthiness_plus.components.models import Basis, Component, Installation
from airworthiness_plus.dashboard import services as dashboard_services
from airworthiness_plus.exports.build import build as build_export
from airworthiness_plus.history import chain
from airworthiness_plus.history.models import Event, RecordsAreNeverDeletedError
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations.models import Organisation
from airworthiness_plus.sample import build, phase1
from airworthiness_rules.intervals import Reading
from tests.conftest import as_owner
from tests.support import TODAY, Sample, dot, make_sample, signed_in

pytestmark = pytest.mark.django_db
D = Decimal


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
    build.add_programmes(sample, fleet)
    return fleet


@pytest.fixture
def components(sample: Sample, fleet: dict[str, Aircraft]) -> dict[str, Component]:
    added = phase1.add_components(sample.ours, sample.planner, fleet)
    return {f"{one.name} {one.serial_number or one.part_number}": one for one in added}


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def rows(body: str, table: int = 0) -> list[list[str]]:
    """Return the cells of each row of one table of the page."""
    found = body.split("<main", 1)[1].split("<table>")[1 + table].split("</table>", 1)[0]
    out = []
    for row in re.findall(r"<tr>\s*(<td.*?)</tr>", found, flags=re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.S)
        out.append([re.sub(r"<[^>]+>", "", cell).strip() for cell in cells])
    return out


def add(sample: Sample, **values: Any) -> Component:
    given: dict[str, Any] = {"name": "[Component]", "basis": Basis.SERVICE, "limit_hours": D("500")}
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return services.add_component(sample.ours, **given)


def fit(sample: Sample, component: Component, aircraft: Aircraft, **values: Any) -> Installation:
    given: dict[str, Any] = {
        "position": "[Position]",
        "fitted_on": date(2026, 11, 1),
        "airframe_hours_fitted": D("6400.0"),
        "hours_at_fitting": D("0.0"),
        "life_from": date(2026, 11, 1),
    }
    given.update(values)
    with working_for(sample.ours.id, sample.planner.id):
        return services.fit_component(component, aircraft, **given)


def line(sample: Sample, component: Component, today: date = TODAY) -> services.ComponentLine:
    with working_for(sample.ours.id, sample.reader.id):
        return services.component_line(Component.objects.get(pk=component.pk), today)


# The sample

PAGE = [
    ["Engine, Lycoming O-360", "G-DGHI", "On Condition, Reviewed Every 100.0 Hours",
     "2,140.0 Hours, Since 4 June 2018", "25.7 Hours", "", "", "[Serial Number Engine G-DGHI]",
     "Engine", "Review at 9,900.0",
     "Departure From the Manufacturer&#x27;s 2,000 Hours or 12 Years"],
    ["Propeller, Fixed Pitch", "Off-Wing",
     "2,000.0 Hours or 72 Months, Manufacturer Recommendation",
     "1,412.0 Hours, Since 2 November 2020", "Due Back 25 November 2026", "Due Soon",
     "[Part Number Propeller G-CDEF]", "[Serial Number Propeller G-CDEF]",
     "From G-CDEF, At [Propeller Organisation]", "",
     "[Propeller Manufacturer&#x27;s Service Information]"],
    ["Emergency Locator Transmitter Battery", "G-ABCD", "Battery Date", "522.6 Hours", "102 Days",
     "", "[Part Number Battery G-ABCD]", "", "Emergency Locator Transmitter", "28 February 2027",
     ""],
    ["Fire Extinguisher", "G-BXYZ", "Label Inspection Date", "368.0 Hours", "133 Days", "",
     "[Part Number Extinguisher G-BXYZ]", "", "Cabin", "31 March 2027", ""],
    ["Engine, Lycoming O-360", "G-CDEF", "2,000.0 Hours, Manufacturer Recommendation",
     "1,780.0 Hours, Since 12 March 2019", "220.0 Hours", "", "", "[Serial Number Engine G-CDEF]",
     "Engine", "2,000.0 Hours", "[Engine Manufacturer&#x27;s Service Instruction]"],
    ["Vacuum Pump", "G-ABCD", "500.0 Hours, Manufacturer Recommendation",
     "182.0 Hours, Since 6 April 2026", "318.0 Hours", "", "[Part Number Vacuum Pump G-ABCD]", "",
     "Engine", "500.0 Hours", "[Vacuum Pump Manufacturer&#x27;s Service Information]"],
    ["Propeller, Fixed Pitch, on Loan", "G-CDEF", "No Limit Recorded", "16.5 Hours", "", "",
     "[Part Number Loan Propeller]", "[Serial Number Loan Propeller]", "Propeller", "", ""],
]  # fmt: skip


def test_the_components_page_of_the_sample_on_18_november_2026(
    sample: Sample, components: dict[str, Component]
) -> None:
    """REQ-234. Golden: the Components board from the sample, nearest first, worked
    by hand in the heading of this file."""
    body = page(signed_in(sample.reader), "/components/")
    assert [row[:11] for row in rows(body)] == PAGE
    assert "<p>7 Tracked, 1 Off-Wing, 1 On Condition, 3 Due in 6 Months</p>" in body
    assert dot("Due Soon") in body
    # How a figure was worked out is on the page (REQ-139).
    engine = next(row for row in rows(body) if row[1] == "G-CDEF" and row[4] == "220.0 Hours")
    for part in ("Airframe Hours Now", "7,731.5", "5,951.5", "ML.A.503"):
        assert part in engine[11]
    with working_for(sample.ours.id, sample.reader.id):
        days = {
            (one.component.name, one.fitted_to): one.days for one in services.component_lines(TODAY)
        }
    assert days == {
        ("Engine, Lycoming O-360", "G-DGHI"): None,
        ("Propeller, Fixed Pitch", "Off-Wing"): 7,
        ("Emergency Locator Transmitter Battery", "G-ABCD"): 102,
        ("Fire Extinguisher", "G-BXYZ"): 133,
        ("Engine, Lycoming O-360", "G-CDEF"): 366,
        ("Vacuum Pump", "G-ABCD"): 397,
        ("Propeller, Fixed Pitch, on Loan", "G-CDEF"): None,
    }


def test_the_record_of_a_component_shows_where_it_has_been_fitted(
    sample: Sample, components: dict[str, Component], fleet: dict[str, Aircraft]
) -> None:
    """REQ-235. The propeller's record: fitted to G-CDEF on 2 November 2020 at 6,319.5
    airframe hours, removed on 2 November 2026 at 7,715.0, and where it is."""
    propeller = components["Propeller, Fixed Pitch [Serial Number Propeller G-CDEF]"]
    body = page(signed_in(sample.reader), f"/components/{propeller.id}/")
    assert rows(body) == [
        ["G-CDEF", "Propeller", "2 November 2020", "6,319.5", "2 November 2026", "16.5",
         "2 November 2020", "Release Certificate on File", "7,715.0", "Removed at 6-Year Limit",
         "[Propeller Organisation]", "25 November 2026"],
    ]  # fmt: skip
    assert "<dt>Fitted To</dt><dd>Off-Wing</dd>" in body
    assert "<dt>Since New or Overhaul</dt><dd>1,412.0 Hours, Since 2 November 2020</dd>" in body
    assert "Airworthiness Directive Applicability to Check Before Refit, ML.A.504(a)" in body
    # The Airworthiness Directives page says so too, as the Directives board does.
    directives = page(signed_in(sample.reader), "/directives/")
    assert (
        "G-CDEF Propeller, Fixed Pitch</a>, At [Propeller Organisation], Applicability Check"
        in (directives)
    )
    # Fitted again when it comes back: a second line, and the first stays.
    with working_for(sample.ours.id, sample.planner.id):
        loan = components["Propeller, Fixed Pitch, on Loan [Serial Number Loan Propeller]"]
        services.remove_component(
            services.current_installation(loan),  # type: ignore[arg-type]
            removed_on=TODAY,
            airframe_hours_removed=D("7731.5"),
            removal_reason="Own Propeller Returned",
        )
    fit(
        sample,
        propeller,
        fleet["G-CDEF"],
        position="Propeller",
        fitted_on=TODAY,
        airframe_hours_fitted=D("7731.5"),
        life_from=TODAY,
    )
    again = rows(page(signed_in(sample.reader), f"/components/{propeller.id}/"))
    assert [row[:5] for row in again] == [
        ["G-CDEF", "Propeller", "18 November 2026", "7,731.5", "Fitted"],
        ["G-CDEF", "Propeller", "2 November 2020", "6,319.5", "2 November 2026"],
    ]
    assert "Applicability Check" not in page(signed_in(sample.reader), "/directives/")


# Fitting and removing


def test_a_component_is_fitted_in_one_place_at_a_time(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-231, REQ-239. A second fitting, and the same form sent twice, are refused
    by the service and by the database."""
    pump = add(sample)
    fitted = fit(sample, pump, fleet["G-ABCD"])
    assert fitted.aircraft_registration == "G-ABCD"
    with pytest.raises(services.RefusedError, match="Already Fitted"):
        fit(sample, pump, fleet["G-BXYZ"], airframe_hours_fitted=D("3300.0"))
    with working_for(sample.ours.id, sample.planner.id):
        with pytest.raises(IntegrityError, match="one_at_a_time"), transaction.atomic():
            Installation.objects.create(
                organisation=sample.ours,
                component=pump,
                aircraft=fleet["G-BXYZ"],
                position="[Position]",
                fitted_on=TODAY,
                airframe_hours_fitted=D("3300.0"),
                hours_at_fitting=D("0"),
            )
        assert Installation.objects.count() == 1
    client = signed_in(sample.planner)
    other = add(sample, name="[Another]", serial_number="[Serial]")
    form = {
        "aircraft": str(fleet["G-ABCD"].id),
        "position": "Engine",
        "fitted_on": "2026-11-01",
        "airframe_hours_fitted": "6400.0",
        "hours_at_fitting": "12.5",
    }
    assert post(client, f"/components/{other.id}/fit/", **form).status_code == 302
    twice = post(client, f"/components/{other.id}/fit/", **form)
    assert twice.status_code == 200
    assert "This Component Is Already Fitted" in twice.content.decode()
    # 12.5 when fitted at 6,400.0; the airframe reads 6,412.6: 25.1 hours.
    assert line(sample, other).hours == D("25.1")


def test_a_removal_is_recorded_once_and_the_fitting_never_changes(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-231, REQ-235. A removal is added once. What was recorded of the fitting is
    never altered, by the application or by the owner of the tables, and nothing of
    a removed fitting changes."""
    pump = add(sample)
    fitted = fit(sample, pump, fleet["G-ABCD"])
    changes: tuple[dict[str, Any], ...] = (
        {"position": "[Altered]"},
        {"fitted_on": date(2026, 10, 1)},
        {"airframe_hours_fitted": D("1.0")},
        {"hours_at_fitting": D("400.0")},
        {"cycles_at_fitting": 4},
        {"airframe_cycles_fitted": 0 + 1},
        {"aircraft_registration": "G-ZZZZ"},
        {"aircraft": fleet["G-BXYZ"]},
        {"release_document": "[Altered]"},
        {"life_from": date(2026, 10, 1)},
    )
    with working_for(sample.ours.id, sample.planner.id):
        for change in changes:
            with pytest.raises(IntegrityError, match="never altered"), transaction.atomic():
                Installation.objects.filter(pk=fitted.pk).update(**change)
        with pytest.raises(RecordsAreNeverDeletedError):
            fitted.delete()
        services.remove_component(
            fitted,
            removed_on=date(2026, 11, 10),
            airframe_hours_removed=D("6405.0"),
            removal_reason="[Reason]",
        )
        with pytest.raises(services.RefusedError, match="Already Removed"):
            services.remove_component(
                fitted,
                removed_on=date(2026, 11, 10),
                airframe_hours_removed=D("6405.0"),
                removal_reason="[Reason]",
            )
        with pytest.raises(IntegrityError, match="removed is never altered"), transaction.atomic():
            Installation.objects.filter(pk=fitted.pk).update(removal_reason="[Altered]")
    with as_owner(), connection.cursor() as cursor:
        cursor.execute(
            "SELECT set_config('airworthiness.organisation', %s, true)", [str(sample.ours.id)]
        )
        with pytest.raises(IntegrityError, match="removed is never altered"), transaction.atomic():
            cursor.execute(
                "UPDATE components_installation SET due_back_on = '2026-12-01' WHERE id = %s",
                [fitted.id],
            )
        cursor.execute("SELECT set_config('airworthiness.organisation', '', true)")
    # 5.0 hours on the aircraft: the count stops at the removal.
    assert line(sample, pump).hours == D("5.0")
    with working_for(sample.ours.id, sample.reader.id):
        assert chain.problems(Event.of(fitted)) == []
        assert Event.of(fitted).count() == 2


def test_a_fitting_keeps_the_registration_as_it_stood(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-235. The database writes the Aircraft Registration, whatever the
    application sends, and a later change of registration does not change it."""
    pump = add(sample)
    with working_for(sample.ours.id, sample.planner.id):
        made = Installation.objects.create(
            organisation=sample.ours,
            component=pump,
            aircraft=fleet["G-ABCD"],
            aircraft_registration="G-ZZZZ",
            position="[Position]",
            fitted_on=TODAY,
            airframe_hours_fitted=D("6412.6"),
            hours_at_fitting=D("0"),
        )
        made.refresh_from_db()
        assert made.aircraft_registration == "G-ABCD"
        Aircraft.objects.filter(pk=fleet["G-ABCD"].pk).update(registration="G-NEWR")
    body = page(signed_in(sample.reader), f"/components/{pump.id}/")
    assert rows(body)[0][0] == "G-ABCD"
    assert "<dt>Fitted To</dt><dd>G-ABCD</dd>" in body


REFUSED_FITTINGS: tuple[tuple[dict[str, Any], str], ...] = (
    ({"position": " "}, "Names Its Position"),
    ({"fitted_on": date(2026, 11, 19)}, "Not Fitted After Today"),
    ({"life_from": date(2026, 11, 2)}, "New or Overhauled After It Was Fitted"),
    ({"airframe_hours_fitted": D("6412.7")}, "Not More Hours or Cycles Then"),
    ({"airframe_cycles_fitted": 1}, "Not More Hours or Cycles Then"),
    ({"airframe_hours_fitted": D("-0.1")}, "Hours Are From 0"),
    ({"hours_at_fitting": D("1000000.0")}, "Hours Are From 0"),
    ({"cycles_at_fitting": 10_000_000}, "Cycles Are From 0"),
)


@pytest.mark.parametrize(("change", "reason"), REFUSED_FITTINGS)
def test_what_cannot_be_true_of_a_fitting_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], change: dict[str, Any], reason: str
) -> None:
    """REQ-231, REQ-239. G-ABCD's airframe reads 6,412.6 hours and 0 cycles."""
    pump = add(sample)
    with pytest.raises(services.RefusedError, match=reason):
        fit(sample, pump, fleet["G-ABCD"], **change)
    with working_for(sample.ours.id, sample.reader.id):
        assert Installation.objects.count() == 0
    # The hours the aircraft has now are accepted.
    fit(sample, pump, fleet["G-ABCD"], airframe_hours_fitted=D("6412.6"))


REFUSED_REMOVALS: tuple[tuple[dict[str, Any], str], ...] = (
    ({"removal_reason": " "}, "Says Why"),
    ({"removed_on": date(2026, 11, 19)}, "Not Removed After Today"),
    ({"removed_on": date(2026, 10, 31)}, "Before It Was Fitted"),
    ({"airframe_hours_removed": D("6399.9")}, "Not Fewer Hours or Cycles"),
    ({"airframe_hours_removed": D("6412.7")}, "Not More Hours or Cycles Then"),
    ({"due_back_on": date(2026, 11, 9)}, "Not Due Back Before"),
)


@pytest.mark.parametrize(("change", "reason"), REFUSED_REMOVALS)
def test_what_cannot_be_true_of_a_removal_is_refused(
    sample: Sample, fleet: dict[str, Aircraft], change: dict[str, Any], reason: str
) -> None:
    """REQ-231, REQ-239. Fitted on 1 November 2026 at 6,400.0 airframe hours."""
    fitted = fit(sample, add(sample), fleet["G-ABCD"])
    given: dict[str, Any] = {
        "removed_on": date(2026, 11, 10),
        "airframe_hours_removed": D("6405.0"),
        "removal_reason": "[Reason]",
    }
    with (
        working_for(sample.ours.id, sample.planner.id),
        pytest.raises(services.RefusedError, match=reason),
    ):
        services.remove_component(fitted, **{**given, **change})
    with working_for(sample.ours.id, sample.reader.id):
        assert Installation.objects.get(pk=fitted.pk).removed_on is None


def test_the_database_holds_the_bounds_of_a_component_and_a_fitting(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-239. Whatever the application sends: every limit and count within its
    bounds, a limit that fits its kind, and a removal that is whole."""
    good: dict[str, Any] = {
        "organisation": sample.ours,
        "name": "[Component]",
        "basis": Basis.SERVICE,
        "limit_hours": D("500"),
    }
    review = {
        "basis": Basis.ON_CONDITION,
        "limit_hours": None,
        "review_hours": D("100"),
        "last_review_hours": D("0"),
        "last_review_on": TODAY,
    }
    components: tuple[tuple[dict[str, Any], str], ...] = (
        ({"name": ""}, "component_has_a_name"),
        ({"basis": "[Unknown]"}, "component_has_a_name"),
        ({"limit_hours": None}, "component_limit_fits_its_kind"),
        ({"limit_date": TODAY, "date_label": "X"}, "component_limit_fits_its_kind"),
        ({"basis": Basis.DATE}, "component_limit_fits_its_kind"),
        ({"basis": Basis.DATE, "limit_hours": None, "limit_date": TODAY}, "fits_its_kind"),
        ({"basis": Basis.NONE}, "component_limit_fits_its_kind"),
        ({"basis": Basis.ON_CONDITION, "limit_hours": None}, "component_limit_fits_its_kind"),
        ({**review, "last_review_on": None}, "component_limit_fits_its_kind"),
        ({"limit_hours": D("0")}, "component_limits_within_bounds"),
        ({"limit_hours": D("100000.0")}, "component_limits_within_bounds"),
        ({"limit_cycles": 0}, "component_limits_within_bounds"),
        ({"limit_cycles": 1_000_000}, "component_limits_within_bounds"),
        ({"limit_months": 0}, "component_limits_within_bounds"),
        ({"limit_months": 1_201}, "component_limits_within_bounds"),
        ({**review, "review_hours": D("0")}, "component_limits_within_bounds"),
        ({**review, "review_hours": D("10000.0")}, "component_limits_within_bounds"),
        ({**review, "last_review_hours": D("1000000.0")}, "component_limits_within_bounds"),
    )
    fitting: dict[str, Any] = {
        "organisation": sample.ours,
        "aircraft": fleet["G-ABCD"],
        "position": "[Position]",
        "fitted_on": date(2026, 11, 1),
        "airframe_hours_fitted": D("6400.0"),
        "hours_at_fitting": D("0"),
    }
    removal = {
        "removed_on": date(2026, 11, 10),
        "airframe_hours_removed": D("6405.0"),
        "airframe_cycles_removed": 0,
        "removal_reason": "[Reason]",
    }
    fittings: tuple[tuple[dict[str, Any], str], ...] = (
        ({"position": ""}, "installation_fitting_within_bounds"),
        ({"airframe_hours_fitted": D("-0.1")}, "installation_fitting_within_bounds"),
        ({"airframe_hours_fitted": D("1000000.0")}, "installation_fitting_within_bounds"),
        ({"hours_at_fitting": D("1000000.0")}, "installation_fitting_within_bounds"),
        ({"cycles_at_fitting": 10_000_000}, "installation_fitting_within_bounds"),
        ({"life_from": date(2026, 11, 2)}, "installation_fitting_within_bounds"),
        (removal, "recorded after the fitting"),
    )
    removals: tuple[tuple[dict[str, Any], str], ...] = (
        ({"removal_reason": ""}, "removal_is_complete_or_absent"),
        ({"removed_on": date(2026, 10, 31)}, "removal_is_complete_or_absent"),
        ({"airframe_hours_removed": D("6399.9")}, "removal_is_complete_or_absent"),
        ({"airframe_hours_removed": None}, "removal_is_complete_or_absent"),
        ({"airframe_cycles_removed": None}, "removal_is_complete_or_absent"),
        ({"due_back_on": date(2026, 11, 9)}, "removal_is_complete_or_absent"),
        ({"removed_on": None}, "removal_is_complete_or_absent"),
    )
    with working_for(sample.ours.id, sample.planner.id):
        for change, constraint in components:
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Component.objects.create(**{**good, **change})
        one = Component.objects.create(
            **{**good, "limit_hours": D("99999.9"), "limit_cycles": 999_999, "limit_months": 1_200}
        )
        for change, constraint in fittings:
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Installation.objects.create(component=one, **{**fitting, **change})
        made = Installation.objects.create(component=one, **fitting)
        for change, constraint in removals:
            with pytest.raises(IntegrityError, match=constraint), transaction.atomic():
                Installation.objects.filter(pk=made.pk).update(**{**removal, **change})
        assert Installation.objects.filter(pk=made.pk).update(**removal) == 1


# Adding a component and its limit

REFUSED_LIMITS: tuple[tuple[dict[str, Any], str], ...] = (
    ({"name": " "}, "Has a Name"),
    ({"basis": "[Unknown]"}, "Choose What the Limit Is"),
    ({"limit_hours": None}, "in Hours, Cycles or Months"),
    ({"limit_date": TODAY}, "No Date on the Component"),
    ({"review_hours": D("100")}, "No Date on the Component and No Review"),
    ({"limit_hours": D("100000.0")}, "at Most 99,999.9"),
    ({"limit_hours": D("0")}, "Above 0"),
    ({"limit_cycles": 1_000_000}, "From 1 to 999,999"),
    ({"limit_months": 1_201}, "From 1 to 1,200"),
    ({"basis": Basis.DATE, "limit_hours": None}, "Give the Date on the Component"),
    ({"basis": Basis.DATE, "limit_date": TODAY, "date_label": "X"}, "No Other Limit"),
    ({"basis": Basis.ON_CONDITION, "limit_hours": None}, "Says How Often It Is Reviewed"),
    (
        {
            "basis": Basis.ON_CONDITION,
            "limit_hours": None,
            "review_hours": D("100"),
            "last_review_hours": D("0"),
            "last_review_on": date(2026, 11, 19),
        },
        "Not After Today",
    ),
    ({"basis": Basis.NONE}, "No Limit Recorded Has No Limit"),
)


@pytest.mark.parametrize(("change", "reason"), REFUSED_LIMITS)
def test_a_limit_that_does_not_fit_its_kind_is_refused(
    sample: Sample, change: dict[str, Any], reason: str
) -> None:
    """REQ-230, REQ-239. ML.A.503: a life is in calendar time, hours or cycles."""
    with pytest.raises(services.RefusedError, match=reason):
        add(sample, **change)
    with working_for(sample.ours.id, sample.reader.id):
        assert Component.objects.count() == 0


def test_a_component_sent_twice_is_recorded_once(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-239. A serial number is recorded once. A component with none is refused
    while another of the same name and part number has never been fitted."""
    client = signed_in(sample.planner)
    form = {"name": "Vacuum Pump", "part_number": "[Part]", "basis": "Service Life Limit",
            "limit_hours": "500"}  # fmt: skip
    assert post(client, "/components/add/", **form).status_code == 302
    twice = post(client, "/components/add/", **form)
    assert "Already Recorded and Not Yet Fitted" in twice.content.decode()
    with working_for(sample.ours.id, sample.reader.id):
        first = Component.objects.get()
    # Once the first is fitted, a second pump of the same part number is another pump.
    fit(sample, first, fleet["G-ABCD"])
    assert post(client, "/components/add/", **form).status_code == 302
    serial = {**form, "serial_number": "[Serial]"}
    assert post(client, "/components/add/", **serial).status_code == 302
    assert "This Component Is Already Recorded" in (
        post(client, "/components/add/", **serial).content.decode()
    )
    with working_for(sample.ours.id, sample.reader.id):
        assert Component.objects.count() == 3


def test_a_limit_is_changed_and_the_history_keeps_the_earlier_one(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-230. From 500 hours to 450: what remains follows, and the history holds both."""
    pump = add(sample)
    fit(sample, pump, fleet["G-ABCD"])
    assert line(sample, pump).remaining_text == "487.4 Hours"
    client = signed_in(sample.planner)
    form = {"basis": "Service Life Limit", "limit_hours": "450", "source": "[Revision 2]"}
    assert post(client, f"/components/{pump.id}/limit/", **form).status_code == 302
    assert line(sample, pump).remaining_text == "437.4 Hours"
    assert "This Limit Is Already Recorded" in (
        post(client, f"/components/{pump.id}/limit/", **form).content.decode()
    )
    with working_for(sample.ours.id, sample.reader.id):
        before, after = (
            json.loads(event.after_json or "{}")["limit_hours"] for event in Event.of(pump)
        )
    assert (D(str(before)), D(str(after))) == (D("500.0"), D("450.0"))


# What remains, and its marks


def test_a_limit_is_marked_as_it_comes_near_and_is_passed(
    sample: Sample, fleet: dict[str, Aircraft], day: Day
) -> None:
    """REQ-232. A pump of 500 hours fitted to G-ABCD at 6,400.0 with 477.4: on
    18 November at 6,412.6 it has 490.0, 10.0 left, which is Due Soon at the lead
    time of 10.0 hours. At 6,422.6 it is Due; a tenth more and it is Overdue. No
    tolerance is given."""
    pump = add(sample)
    fit(sample, pump, fleet["G-ABCD"], hours_at_fitting=D("477.3"))
    assert (line(sample, pump).remaining_text, line(sample, pump).status) == ("10.1 Hours", "")
    other = add(sample, name="[Second]")
    fit(sample, other, fleet["G-ABCD"], hours_at_fitting=D("477.4"), position="[Second]")
    assert (line(sample, other).remaining_text, line(sample, other).status) == (
        "10.0 Hours",
        "Due Soon",
    )
    with working_for(sample.ours.id, sample.reader.id):
        counter = fleet["G-ABCD"].counters.get(kind="Airframe")
    day.today = date(2026, 12, 1)
    with working_for(sample.ours.id, sample.planner.id):
        aircraft_services.enter_utilisation(counter, Reading(day.today, D("6422.6"), 0))
    assert (
        line(sample, other, day.today).remaining_text,
        line(sample, other, day.today).status,
    ) == (
        "0.0 Hours",
        "Due",
    )
    day.today = date(2026, 12, 2)
    with working_for(sample.ours.id, sample.planner.id):
        aircraft_services.enter_utilisation(counter, Reading(day.today, D("6422.7"), 0))
    late = line(sample, other, day.today)
    assert (late.remaining_text, late.status) == ("0.1 Hours Overdue", "Overdue")
    assert late.days is not None and late.days < 0


def test_a_calendar_life_with_no_day_to_run_from_cannot_be_calculated(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-232. As the Set Up Configuration board has it: the calendar limit is not
    worked out until the overhaul date is recorded. It is shown first, not left
    clear, and the day is then given once."""
    propeller = add(
        sample, name="[Propeller]", basis=Basis.RECOMMENDATION, limit_hours=None, limit_months=72
    )
    fitted = fit(sample, propeller, fleet["G-EJKL"], life_from=None, airframe_hours_fitted=D("0"))
    found = line(sample, propeller)
    assert found.problem.startswith("Calendar Limit Not Worked Out")
    assert (found.remaining_text, found.due_in_six_months) == ("Cannot Be Calculated", True)
    with working_for(sample.ours.id, sample.reader.id):
        assert services.component_lines(TODAY)[0].component == propeller
        panel = dashboard_services.continuing_airworthiness(
            Organisation.objects.get(pk=sample.ours.pk), TODAY
        )
    row = next(row for row in panel.rows if row.page == "Aircraft Configuration")
    assert (row.subject, row.item, row.due, row.first) == (
        "G-EJKL",
        "Component Limit, [Propeller]",
        "Cannot Be Calculated",
        True,
    )
    client = signed_in(sample.planner)
    address = f"/components/{propeller.id}/new-or-overhauled/"
    assert "After It Was Fitted" in post(client, address, life_from="2026-11-02").content.decode()
    assert post(client, address, life_from="2021-01-15").status_code == 302
    assert "Already Recorded" in post(client, address, life_from="2021-01-16").content.decode()
    # 15 January 2021 and 72 months: 15 January 2027, 58 days from 18 November 2026.
    assert line(sample, propeller).remaining_text == "58 Days"
    with working_for(sample.ours.id, sample.reader.id):
        assert Installation.objects.get(pk=fitted.pk).life_from == date(2021, 1, 15)


def test_a_review_of_a_component_on_condition_moves_the_next_review(
    sample: Sample, components: dict[str, Component]
) -> None:
    """REQ-233. G-DGHI's engine, reviewed at 9,800.0, is next reviewed at 9,900.0. A
    review at 9,870.0 on 17 November moves it to 9,970.0: 95.7 hours left."""
    engine = components["Engine, Lycoming O-360 [Serial Number Engine G-DGHI]"]
    assert line(sample, engine).due_text == "Review at 9,900.0"
    client = signed_in(sample.planner)
    address = f"/components/{engine.id}/review/"
    for hours, on, reason in (
        ("9799.9", "2026-11-17", "Not Before the Last Review"),
        ("9870.0", "2026-10-19", "Not Before the Last Review"),
        ("9874.4", "2026-11-17", "Not More Hours Then"),
        ("9870.0", "2026-11-19", "Not After Today"),
    ):
        refused = post(client, address, airframe_hours=hours, reviewed_on=on)
        assert reason in refused.content.decode(), reason
    assert post(client, address, airframe_hours="9870.0", reviewed_on="2026-11-17").status_code == (
        302
    )
    twice = post(client, address, airframe_hours="9870.0", reviewed_on="2026-11-17")
    assert "This Review Is Already Recorded" in twice.content.decode()
    after = line(sample, engine)
    assert (after.due_text, after.remaining_text) == ("Review at 9,970.0", "95.7 Hours")
    pump = components["Vacuum Pump [Part Number Vacuum Pump G-ABCD]"]
    refused = post(
        client, f"/components/{pump.id}/review/", airframe_hours="6400.0", reviewed_on="2026-11-17"
    )
    assert "Only a Component Kept on Condition Is Reviewed" in refused.content.decode()


# The Dashboard, roles, other organisations and the export


def test_the_dashboard_shows_a_component_from_its_lead_time(
    sample: Sample, components: dict[str, Component], day: Day
) -> None:
    """REQ-237. Golden, from the Home board: G-CDEF's own propeller is due back on
    25 November 2026, in 7 days. The battery date of 28 February 2027 is shown from
    29 January 2027, 30 days before, and is Overdue on 1 March."""

    def shown() -> list[list[str]]:
        with working_for(sample.ours.id, sample.reader.id):
            panel = dashboard_services.continuing_airworthiness(
                Organisation.objects.get(pk=sample.ours.pk), day.today
            )
        return [
            [row.subject, row.item, row.due, row.remaining, row.status, row.detail]
            for row in panel.rows
            if row.page == "Aircraft Configuration"
        ]

    assert shown() == [
        ["G-CDEF", "Propeller, Fixed Pitch Due Back", "25 November 2026", "7 Days", "Due Soon",
         "Removed 2 November 2026, At [Propeller Organisation]"],
    ]  # fmt: skip
    propeller = components["Propeller, Fixed Pitch [Serial Number Propeller G-CDEF]"]
    body = page(signed_in(sample.reader), "/dashboard/")
    assert f'<a href="/components/{propeller.id}/">Aircraft Configuration</a>' in body
    day.today = date(2026, 11, 26)
    assert shown()[0][2:5] == ["25 November 2026", "1 Day Overdue", "Overdue"]
    battery = ["G-ABCD", "Component Limit, Emergency Locator Transmitter Battery"]
    day.today = date(2027, 1, 28)
    assert not [row for row in shown() if row[:2] == battery]
    day.today = date(2027, 1, 29)
    assert next(row for row in shown() if row[:2] == battery)[2:] == [
        "28 February 2027",
        "30 Days",
        "Due Soon",
        "Battery Date, ML.A.503",
    ]
    day.today = date(2027, 3, 1)
    assert next(row for row in shown() if row[:2] == battery)[3:5] == ["1 Day Overdue", "Overdue"]


FIT = {
    "position": "Engine",
    "fitted_on": "2026-11-01",
    "airframe_hours_fitted": "6400.0",
    "hours_at_fitting": "0",
}


@pytest.mark.parametrize("role", ["administrator", "lucy", "planner", "reviewer", "reader"])
def test_who_may_record_components(sample: Sample, fleet: dict[str, Aircraft], role: str) -> None:
    """REQ-006, REQ-238. The Continuing Airworthiness Manager and Planning and Records
    record; every role reads. A link or form is shown only to a role that may use it."""
    fitted, loose = add(sample, name="[Fitted]"), add(sample, name="[Loose]")
    fit(sample, fitted, fleet["G-ABCD"])
    client = signed_in(getattr(sample, role))
    may = role in ("lucy", "planner")
    listed = page(client, "/components/").split("<main", 1)[1]
    one = page(client, f"/components/{fitted.id}/").split("<main", 1)[1]
    assert ('href="/components/add/"' in listed) == may
    assert ("<form" in one) == may
    assert get(client, "/components/add/").status_code == (200 if may else 403)
    answers = [
        post(client, "/components/add/", name="[New]", basis="No Limit Recorded"),
        post(client, f"/components/{loose.id}/fit/", aircraft=str(fleet["G-ABCD"].id), **FIT),
        post(
            client,
            f"/components/{fitted.id}/remove/",
            removed_on="2026-11-10",
            airframe_hours_removed="6405.0",
            removal_reason="[Reason]",
        ),
        post(client, f"/components/{loose.id}/limit/", basis="No Limit Recorded"),
        post(
            client, f"/components/{loose.id}/review/", airframe_hours="1", reviewed_on="2026-11-01"
        ),
        post(client, f"/components/{loose.id}/new-or-overhauled/", life_from="2026-11-02"),
    ]
    assert [answer.status_code for answer in answers[:4]] == [302 if may else 403] * 4
    assert [answer.status_code for answer in answers[4:]] == [200 if may else 403] * 2
    with working_for(sample.ours.id, sample.reader.id):
        assert Component.objects.count() == (3 if may else 2)
        assert Installation.objects.filter(removed_on__isnull=True).count() == 1
        assert Installation.objects.count() == (2 if may else 1)
    if not may:
        with as_owner():
            refused = AccessEntry.objects.filter(kind="Action Refused")
            assert list(refused.values_list("detail", flat=True)) == (
                ["Record Aircraft Configuration"] * 7
            )


def test_another_organisations_components_are_not_found_or_shown(
    sample: Sample, components: dict[str, Component], fleet: dict[str, Aircraft]
) -> None:
    """REQ-003, REQ-002."""
    stranger = signed_in(sample.stranger)
    pump = components["Vacuum Pump [Part Number Vacuum Pump G-ABCD]"]
    assert get(stranger, f"/components/{pump.id}/").status_code == 404
    for address, values in (
        ("fit", {"aircraft": str(fleet["G-ABCD"].id), **FIT}),
        ("remove", {"removed_on": "2026-11-10", "airframe_hours_removed": "1",
                    "removal_reason": "X"}),
        ("limit", {"basis": "No Limit Recorded"}),
        ("review", {"airframe_hours": "1", "reviewed_on": "2026-11-01"}),
        ("new-or-overhauled", {"life_from": "2026-11-01"}),
    ):  # fmt: skip
        assert post(stranger, f"/components/{pump.id}/{address}/", **values).status_code == 404
    for path in ("/components/", "/directives/", "/dashboard/"):
        body = page(stranger, path)
        assert "Vacuum Pump" not in body and "G-CDEF" not in body and "Propeller" not in body
    made = post(stranger, "/components/add/", name="[Theirs]", basis="No Limit Recorded")
    refused = post(stranger, made["Location"] + "fit/", aircraft=str(fleet["G-ABCD"].id), **FIT)
    assert "Select a valid choice" in refused.content.decode()
    with working_for(sample.other.id, sample.stranger.id):
        theirs = Component.objects.get()
        own = aircraft_services.add_aircraft(
            organisation=sample.other, registration="G-OTHR", type_rating="[Type]", owner="X"
        )
        pairs: tuple[dict[str, Any], ...] = (
            {"component": pump, "aircraft": own},
            {"component": theirs, "aircraft": fleet["G-ABCD"]},
        )
        for values in pairs:
            with (
                pytest.raises(Exception, match="refers only to records of its own organisation"),
                transaction.atomic(),
            ):
                Installation.objects.create(
                    organisation=sample.other,
                    position="[Position]",
                    fitted_on=TODAY,
                    airframe_hours_fitted=D("0"),
                    hours_at_fitting=D("0"),
                    **values,
                )


def test_the_export_of_an_aircraft_holds_every_component_ever_fitted_to_it(
    sample: Sample, components: dict[str, Component], fleet: dict[str, Aircraft]
) -> None:
    """REQ-134, REQ-235. G-CDEF: its engine, its own propeller, now off-wing, and the
    loan propeller, each with its fitting. G-EJKL: none."""
    with working_for(sample.ours.id, sample.lucy.id):
        cdef = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-CDEF"])
        ejkl = build_export(sample.ours, by=sample.lucy, aircraft=fleet["G-EJKL"])

    def read(export: object, name: str) -> list[dict[str, object]]:
        with zipfile.ZipFile(io.BytesIO(export.content)) as archive:  # type: ignore[attr-defined]
            found: list[dict[str, object]] = json.loads(archive.read(f"records/{name}.json"))
            return found

    assert sorted(str(one["name"]) for one in read(cdef, "components_component")) == [
        "Engine, Lycoming O-360",
        "Propeller, Fixed Pitch",
        "Propeller, Fixed Pitch, on Loan",
    ]
    fittings = read(cdef, "components_installation")
    assert sorted(str(one["aircraft_registration"]) for one in fittings) == ["G-CDEF"] * 3
    assert [one["removal_reason"] for one in fittings if one["removed_on"]] == [
        "Removed at 6-Year Limit"
    ]
    assert read(ejkl, "components_component") == []
    assert read(ejkl, "components_installation") == []


def test_aircraft_configuration_is_in_the_sidebar_with_directives_as_its_view(
    sample: Sample, components: dict[str, Component]
) -> None:
    """REQ-238. The Sidebar and Tabs boards: Aircraft Configuration, with Components
    and Life Limits first and Airworthiness Directives beside it. Aircraft no longer
    has Airworthiness Directives among its views."""
    client = signed_in(sample.reader)
    for path in ("/components/", "/directives/"):
        body = page(client, path)
        sidebar = body.split('<nav aria-label="Sections">', 1)[1].split("</nav>", 1)[0]
        assert '<a href="/components/" aria-current="page">Aircraft Configuration</a>' in sidebar
        tabs = body.split('<nav class="tabs" aria-label="Views">', 1)[1].split("</nav>", 1)[0]
        assert re.findall(r">([^<]+)</a>", tabs) == [
            "Components and Life Limits",
            "Airworthiness Directives",
        ]
    fleet_tabs = page(client, "/").split('<nav class="tabs" aria-label="Views">', 1)[1]
    assert re.findall(r">([^<]+)</a>", fleet_tabs.split("</nav>", 1)[0]) == [
        "All Aircraft",
        "Airworthiness Reviews",
        "Transfers",
    ]
