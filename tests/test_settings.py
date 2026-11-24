"""Settings: organisation details, approvals held, deferral limits and alert lead times.

REQ-211 to REQ-214. Decisions.md, Canvas Build, decision 4: the defaults stay
10.0 hours, 10 cycles and 30 days, and a 60-day alert for review
certificates is a setting the organisation may turn on. The Settings
board's 15 hours is not taken.

ML.A.403 was read in the UK text in the Civil Aviation Authority Regulatory
Library on 24 November 2026. Point (b) says who may defer a defect; point
(c) says a defect is rectified "within the limits specified in the
maintenance data". It gives no number of days: the 30 days of the Settings
board are the organisation's own default.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.http import HttpResponse
from django.test import Client
from hypothesis import given
from hypothesis import strategies as st

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.organisations import approvals
from airworthiness_plus.organisations.models import Approval, Organisation
from airworthiness_plus.programme import due
from airworthiness_plus.reviews import services as review_services
from airworthiness_rules.programme import Flag, Thresholds, review_certificate_lead_days
from tests.conftest import as_owner
from tests.support import (
    Sample,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    make_sample,
    signed_in,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def sample() -> Sample:
    return make_sample()


@pytest.fixture
def fleet(sample: Sample) -> dict[str, Aircraft]:
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    add_sample_reviews(sample, fleet)
    return fleet


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


def ours(sample: Sample) -> Organisation:
    with working_for(sample.ours.id, sample.reader.id):
        return Organisation.objects.get()


# The page


def test_settings_stands_outside_the_groups_and_shows_what_is_set(sample: Sample) -> None:
    """REQ-202, REQ-211 to REQ-214. The defaults of decision 4, and the points of ML.A.403."""
    body = page(signed_in(sample.reader), "/settings/")
    crumb = body.split('aria-label="Location"', 1)[1].split("</nav>", 1)[0]
    assert crumb.count("<li>") == 1
    assert '<li><a href="/settings/" aria-current="location">Settings</a></li>' in crumb
    sidebar = body.split('<nav aria-label="Sections">', 1)[1].split("</nav>", 1)[0]
    assert '<a href="/settings/" aria-current="page">Settings</a>' in sidebar
    for text in (
        "<h2>Organisation Details</h2>",
        "<dt>Organisation Name</dt><dd>[Your Organisation]</dd>",
        "<dt>Address</dt><dd>[Organisation Address]</dd>",
        "<dt>Approval Reference</dt><dd>UK.CAO.[Number]</dd>",
        '<a href="/organisation/">Approval and Scope</a>',
        "<h2>Approvals Held</h2>",
        "<td>Part-CAO</td><td>UK.CAO.[Number]</td><td>Held</td>",
        "<h2>Deferral Limits</h2>",
        "<p>Limit in the Maintenance Data Applies When Shorter, ML.A.403(c)</p>",
        "<td>Pilot-in-Command</td><td>Defects on Non-Required Equipment</td>"
        "<td>30 Days</td><td>ML.A.403(b)(1)</td>",
        "<td>Pilot-in-Command, Minimum Equipment List</td>"
        "<td>Required Equipment Listed in the Minimum Equipment List</td>"
        "<td>Limit Given in the Minimum Equipment List</td><td>ML.A.403(b)(2)</td>",
        "<td>Pilot-in-Command, With Agreement</td>"
        "<td>Other Defects, Part-NCO, Owner or Organisation Agrees</td>"
        "<td>30 Days</td><td>ML.A.403(b)(3)</td>",
        "<td>Certifying Staff</td><td>Other Defects</td><td>30 Days</td><td>ML.A.403(b)(4)</td>",
        "<h2>Alert Lead Times</h2>",
        "<td>Airworthiness Review Certificate Expiry</td><td>30 Days</td>",
        "<td>Hour-Based Checks and Life Limits</td><td>10.0 Hours</td>",
        "<td>Cycle-Based Checks and Life Limits</td><td>10 Cycles</td>",
        "<td>Calendar Checks and Programme Reviews</td><td>30 Days</td>",
    ):
        assert text in body, text
    # Only the Administrator is offered the forms.
    assert "<form" not in body.split("<main", 1)[1]
    assert body.count("<form") == 1  # signing out
    assert page(signed_in(sample.administrator), "/settings/").count("<form") == 5


def test_the_defaults_are_those_of_the_record(sample: Sample) -> None:
    """REQ-212, REQ-214. Decision 4: 30 days, 10.0 hours, 10 cycles; no earlier alert."""
    organisation = ours(sample)
    assert due.thresholds_of(organisation) == Thresholds(30, Decimal("10.0"), 10)
    assert due.certificate_thresholds(organisation) == Thresholds(30, Decimal("10.0"), 10)
    assert organisation.review_alert_days is None
    assert (
        organisation.deferral_days_non_required,
        organisation.deferral_days_with_agreement,
        organisation.deferral_days_certifying_staff,
    ) == (30, 30, 30)


# Organisation details


def test_the_administrator_changes_the_name_and_address_and_it_is_in_the_history(
    sample: Sample,
) -> None:
    """REQ-211."""
    administrator = signed_in(sample.administrator)
    response = post(
        administrator,
        "/settings/details/",
        name="  [Your Organisation] Limited ",
        address="[New Organisation Address]",
    )
    assert response.status_code == 302
    assert response["Location"] == "/settings/"
    organisation = ours(sample)
    assert (organisation.name, organisation.address) == (
        "[Your Organisation] Limited",
        "[New Organisation Address]",
    )
    with working_for(sample.ours.id, sample.reader.id):
        entry = Event.of(organisation).last()
    assert entry is not None
    assert (entry.changed, entry.actor_name) == (["address", "name"], "[Accountable Manager]")
    refused = post(administrator, "/settings/details/", name=" ", address="[Address]")
    assert refused.status_code == 200
    assert "This field is required" in refused.content.decode()
    assert ours(sample).name == "[Your Organisation] Limited"


@pytest.mark.parametrize("role", ["lucy", "planner", "reviewer", "reader"])
def test_only_the_administrator_changes_settings(sample: Sample, role: str) -> None:
    """REQ-006. Every change on the page is refused to the others, and logged."""
    client = signed_in(getattr(sample, role))
    with working_for(sample.ours.id, sample.reader.id):
        approval = Approval.objects.get()
    paths = (
        "/settings/details/",
        "/settings/approvals/",
        f"/settings/approvals/{approval.id}/end/",
        "/settings/lead-times/",
        "/settings/deferral-limits/",
    )
    for path in paths:
        assert post(client, path, name="X").status_code == 403, path
    assert ours(sample).name == "[Your Organisation]"
    with as_owner():
        refused = AccessEntry.objects.filter(
            kind="Action Refused", detail="Change Organisation Record"
        )
        assert refused.count() == len(paths)


# Approvals held


def test_the_administrator_records_an_approval_held_and_that_it_has_ended(
    sample: Sample,
) -> None:
    """REQ-200, REQ-211. Decision 1."""
    administrator = signed_in(sample.administrator)
    added = post(
        administrator, "/settings/approvals/", approval="Part-145", reference="UK.145.[Number]"
    )
    assert added.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert approvals.types_held(sample.ours) == {"Part-CAO", "Part-145"}
        part_145 = Approval.objects.get(approval="Part-145")
        first = Approval.objects.get(approval="Part-CAO")
    body = page(administrator, "/settings/")
    assert "<td>Part-145</td><td>UK.145.[Number]</td><td>Held</td>" in body
    again = post(
        administrator, "/settings/approvals/", approval="Part-145", reference="UK.145.[Number]"
    )
    assert again.status_code == 200
    assert "Part-145 Is Already Recorded" in again.content.decode()
    unknown = post(administrator, "/settings/approvals/", approval="Part-147", reference="X")
    assert unknown.status_code == 200
    assert "Select a valid choice" in unknown.content.decode()

    ended = post(administrator, f"/settings/approvals/{part_145.id}/end/", on="2026-11-18")
    assert ended.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        assert approvals.types_held(sample.ours) == {"Part-CAO"}
    assert (
        "<td>Part-145</td><td>UK.145.[Number]</td><td>No Longer Held From 18 November 2026</td>"
        in page(administrator, "/settings/")
    )
    kept = post(administrator, f"/settings/approvals/{first.id}/end/", on="2026-11-18")
    assert kept.status_code == 200
    assert "Set Up With Is Changed by Airworthiness Limited" in kept.content.decode()
    future = post(administrator, "/settings/approvals/", approval="Part-CAMO", reference="R")
    assert future.status_code == 302
    with working_for(sample.ours.id, sample.reader.id):
        camo = Approval.objects.get(approval="Part-CAMO")
    late = post(administrator, f"/settings/approvals/{camo.id}/end/", on="2999-01-01")
    assert late.status_code == 200
    assert "No Longer Held From Is Not After Today" in late.content.decode()
    # Another organisation's approval is not found.
    assert (
        post(
            signed_in(sample.stranger), f"/settings/approvals/{camo.id}/end/", on="2026-11-18"
        ).status_code
        == 404
    )


# Alert lead times


def lead_times(client: Client, **values: str) -> HttpResponse:
    sent = {"due_soon_days": "30", "due_soon_hours": "10.0", "due_soon_cycles": "10", **values}
    return post(client, "/settings/lead-times/", **sent)


def test_the_hour_lead_time_is_the_organisations_to_set(
    sample: Sample, fleet: dict[str, Aircraft], monkeypatch: pytest.MonkeyPatch
) -> None:
    """REQ-212, golden. G-ABCD's 50-hour check has 12.4 hours remaining (SampleData.md).

    At the recorded default of 10.0 hours that is not yet Due Soon. An
    organisation that sets 15.0 hours, the figure of the Settings board,
    sees it as Due Soon; at 12.4 it is, and at 12.3 it is not.
    """
    monkeypatch.setattr(aircraft_services, "today", lambda: date(2026, 11, 18))
    administrator = signed_in(sample.administrator)

    def flag() -> Flag:
        with working_for(sample.ours.id, sample.reader.id):
            aircraft = Aircraft.objects.get(registration="G-ABCD")
            (line,) = due.due_lines(aircraft, date(2026, 11, 18))
            assert line.first[0].remaining_text == "12.4 Hours"
            return line.flag

    assert flag() is Flag.NONE
    for hours, expected in (("15.0", Flag.DUE_SOON), ("12.4", Flag.DUE_SOON), ("12.3", Flag.NONE)):
        assert lead_times(administrator, due_soon_hours=hours).status_code == 302
        assert ours(sample).due_soon_hours == Decimal(hours)
        assert flag() is expected, hours
    assert "<td>Hour-Based Checks and Life Limits</td><td>12.3 Hours</td>" in page(
        administrator, "/settings/"
    )
    # The other organisation's lead times are its own.
    with working_for(sample.other.id, sample.stranger.id):
        assert Organisation.objects.get().due_soon_hours == Decimal("10.0")


def test_a_review_certificate_can_be_given_an_earlier_alert(
    sample: Sample, fleet: dict[str, Aircraft]
) -> None:
    """REQ-213, golden. G-ABCD's certificate is valid to 14 March 2027 (SampleData.md).

    By hand: 13 January 2027 is 60 days before (18 to the end of January,
    28 in February, 14 in March); 12 January is 61; 12 February is 30;
    11 February is 31. With no earlier alert the certificate is Due Soon
    from 30 days. With the alert at 60 days it is Due Soon from 60. Nothing
    else takes the earlier lead time.
    """
    administrator = signed_in(sample.administrator)

    def flag(today: date) -> tuple[int | None, Flag]:
        with working_for(sample.ours.id, sample.reader.id):
            aircraft = Aircraft.objects.get(registration="G-ABCD")
            line = review_services.schedule_line(aircraft, today)
            return line.days, line.flag

    assert flag(date(2027, 2, 11)) == (31, Flag.NONE)
    assert flag(date(2027, 2, 12)) == (30, Flag.DUE_SOON)
    assert flag(date(2027, 1, 13)) == (60, Flag.NONE)

    assert lead_times(administrator, review_alert="on", review_alert_days="60").status_code == 302
    organisation = ours(sample)
    assert organisation.review_alert_days == 60
    assert due.certificate_thresholds(organisation).days == 60
    assert due.thresholds_of(organisation).days == 30
    assert flag(date(2027, 1, 12)) == (61, Flag.NONE)
    assert flag(date(2027, 1, 13)) == (60, Flag.DUE_SOON)
    assert flag(date(2027, 2, 11)) == (31, Flag.DUE_SOON)
    assert flag(date(2027, 3, 14)) == (0, Flag.DUE)
    assert flag(date(2027, 3, 15)) == (-1, Flag.OVERDUE)
    body = page(administrator, "/settings/")
    assert "<td>Airworthiness Review Certificate Expiry</td><td>60 Days</td>" in body
    assert "<td>Calendar Checks and Programme Reviews</td><td>30 Days</td>" in body

    # Turned off again, the days typed are not kept.
    assert lead_times(administrator, review_alert_days="60").status_code == 302
    assert ours(sample).review_alert_days is None
    assert flag(date(2027, 1, 13)) == (60, Flag.NONE)


def test_lead_times_that_make_no_sense_are_refused(sample: Sample) -> None:
    """REQ-212, REQ-213. On the page with the reason, and by the database whoever asks."""
    administrator = signed_in(sample.administrator)
    for values, message in (
        ({"due_soon_days": "-1"}, "greater than or equal to 0"),
        ({"due_soon_days": "366"}, "less than or equal to 365"),
        ({"due_soon_hours": "10.05"}, "no more than 1 decimal place"),
        ({"due_soon_hours": "1000"}, "less than or equal to 999.9"),
        ({"due_soon_cycles": "10000"}, "less than or equal to 9999"),
        ({"review_alert": "on"}, "Give the Days of the Earlier Alert"),
        (
            {"review_alert": "on", "review_alert_days": "30"},
            "The Earlier Alert Is More Days Than the Calendar Lead Time",
        ),
        ({"review_alert": "on", "review_alert_days": "366"}, "less than or equal to 365"),
    ):
        response = lead_times(administrator, **values)
        assert response.status_code == 200, values
        assert message in response.content.decode(), values
    organisation = ours(sample)
    assert (organisation.due_soon_days, organisation.review_alert_days) == (30, None)
    with working_for(sample.ours.id, sample.administrator.id):
        with (
            pytest.raises(IntegrityError, match="organisation_review_alert_is_the_earlier"),
            transaction.atomic(),
        ):
            Organisation.objects.filter(pk=sample.ours.pk).update(review_alert_days=30)
        with (
            pytest.raises(IntegrityError, match="organisation_deferral_limits_are_at_least_a_day"),
            transaction.atomic(),
        ):
            Organisation.objects.filter(pk=sample.ours.pk).update(deferral_days_non_required=0)


@given(
    st.integers(min_value=0, max_value=365),
    st.one_of(st.none(), st.integers(min_value=1, max_value=365)),
)
def test_the_lead_time_of_a_review_certificate_is_never_shorter_than_the_calendar_one(
    days: int, alert: int | None
) -> None:
    """REQ-213. The earlier alert only ever adds warning."""
    lead = review_certificate_lead_days(days, alert)
    assert lead >= days
    assert lead == (days if alert is None or alert <= days else alert)


# Deferral limits


def test_the_administrator_sets_the_default_deferral_limits(sample: Sample) -> None:
    """REQ-214. The organisation's own defaults, in days, for the three decisions
    of ML.A.403(b) that the regulation gives no limit of its own."""
    administrator = signed_in(sample.administrator)
    response = post(
        administrator,
        "/settings/deferral-limits/",
        deferral_days_non_required="60",
        deferral_days_with_agreement="14",
        deferral_days_certifying_staff="21",
    )
    assert response.status_code == 302
    organisation = ours(sample)
    assert (
        organisation.deferral_days_non_required,
        organisation.deferral_days_with_agreement,
        organisation.deferral_days_certifying_staff,
    ) == (60, 14, 21)
    body = page(administrator, "/settings/")
    assert "<td>Defects on Non-Required Equipment</td><td>60 Days</td>" in body
    assert "<td>Other Defects</td><td>21 Days</td>" in body
    with working_for(sample.ours.id, sample.reader.id):
        entry = Event.of(organisation).last()
    assert entry is not None
    assert entry.changed == [
        "deferral_days_certifying_staff",
        "deferral_days_non_required",
        "deferral_days_with_agreement",
    ]
    for value, message in (("0", "greater than or equal to 1"), ("366", "less than or equal to")):
        refused = post(
            administrator,
            "/settings/deferral-limits/",
            deferral_days_non_required=value,
            deferral_days_with_agreement="14",
            deferral_days_certifying_staff="21",
        )
        assert refused.status_code == 200
        assert message in refused.content.decode()
    assert ours(sample).deferral_days_non_required == 60
