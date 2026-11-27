"""Review certificates, extensions, the schedule and review staff (REQ-100 to REQ-116).

The certificates and people are those of design-system/SampleData.md.
Today in the sample world is 18 November 2026.
"""

import threading
from datetime import date, timedelta
from decimal import Decimal

import psycopg
import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.interface.formatting import long_date
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.models import Certificate, Extension, ReviewStaff
from airworthiness_rules.dates import add_years
from airworthiness_rules.programme import Flag
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    SampleReviews,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    call,
    dot,
    page,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal


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
    fleet = add_sample_fleet(sample)
    add_sample_programmes(sample, fleet)
    return fleet


@pytest.fixture
def reviews(sample: Sample, fleet: dict[str, Aircraft]) -> SampleReviews:
    return add_sample_reviews(sample, fleet)


def row_for(body: str, registration: str) -> str:
    start = body.index(f">{registration}</a>")
    return body[start : body.index("</tr>", start)]


CONDITIONS = {
    "managed_for_12_months": "on",
    "maintained_by_approved_organisations": "on",
    "no_evidence_not_airworthy": "on",
}


# The schedule


def test_the_schedule_shows_each_certificate_and_the_days_remaining(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-100, REQ-116, golden. G-EJKL: valid to 6 December 2026, 18 days on
    18 November 2026, Due Soon, inside the 90-day window. Soonest first."""
    body = page(signed_in(sample.reader), "/reviews/")
    ejkl = row_for(body, "G-EJKL")
    for text in (
        "<td>6 December 2026</td>",
        '<td class="number">18 Days</td>',
        f"<td>{dot('Due Soon')}</td>",
        "<td>Inside the 90-Day Window</td>",
    ):
        assert text in ejkl, text
    order = [body.index(f">{registration}</a>") for registration in ("G-EJKL", "G-ABCD", "G-FMNO")]
    assert order == sorted(order)
    abcd = row_for(body, "G-ABCD")
    assert "<td>14 March 2027</td>" in abcd
    assert '<td class="number">116 Days</td>' in abcd  # 12 + 31 + 31 + 28 + 14
    assert "Inside the 90-Day Window" not in abcd
    assert "G-HKLM" not in body
    with working_for(sample.ours.id, sample.reader.id):
        line = services.schedule_line(Aircraft.objects.get(pk=fleet["G-EJKL"].pk), TODAY)
    assert (line.days, line.flag, line.in_review_window, line.in_extension_window) == (
        18,
        Flag.DUE_SOON,
        True,
        True,
    )


def test_g_cdef_early_review_keeps_the_pattern_and_the_copy_is_owed(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-102, REQ-110, REQ-111, golden. Reviewed 11 November 2026, 21 days
    before 2 December 2026: valid to 2 December 2027. The first certificate of
    the organisation: serial 1. The copy goes to the Civil Aviation Authority
    by 21 November 2026."""
    certificate = reviews.cdef
    assert (certificate.serial_number, certificate.reference) == (1, "UK.CAO.[Number]-ARC-0001")
    assert (certificate.issued_on, certificate.valid_to) == (date(2026, 11, 11), date(2027, 12, 2))
    body = page(signed_in(sample.reader), "/reviews/")
    cdef = row_for(body, "G-CDEF")
    assert "<td>2 December 2027</td>" in cdef
    assert (
        '<td class="number">379 Days</td>' in cdef
    )  # 12 in November, 365 to 30 November 2027, 2 in December
    assert f"<td>To Be Sent by 21 November 2026, {dot('Due Soon')}</td>" in cdef
    detail = page(signed_in(sample.reader), f"/aircraft/{fleet['G-CDEF'].id}/review/")
    assert ">UK.CAO.[Number]-ARC-0001</a></td>" in detail
    assert "<td>Lucy Grant, [Authorisation Reference 1]</td>" in detail
    assert "<td>Superseded</td>" in detail


def test_the_copy_sent_is_recorded_and_no_longer_owed(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-111, ML.A.903(f). Overdue from 22 November; cleared when recorded."""
    day.today = date(2026, 11, 22)
    client = signed_in(sample.planner)
    owed = row_for(page(client, "/reviews/"), "G-CDEF")
    assert f"To Be Sent by 21 November 2026, {dot('Overdue')}" in owed
    too_early = post(client, f"/certificates/{reviews.cdef.id}/copy-sent/", on="2026-11-10")
    assert "On or After the Day of Issue" in too_early.content.decode()
    sent = post(client, f"/certificates/{reviews.cdef.id}/copy-sent/", on="2026-11-20")
    assert sent.status_code == 302
    assert "To Be Sent" not in row_for(page(client, "/reviews/"), "G-CDEF")
    assert "Sent 20 November 2026" in page(client, f"/aircraft/{fleet['G-CDEF'].id}/review/")


# Serials


def test_serials_run_in_order_and_a_void_serial_is_never_used_again(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110, hazard H-007. The database sets the serial, whatever is asked for."""
    with working_for(sample.ours.id, sample.lucy.id):
        second = services.issue_certificate(fleet["G-EJKL"], staff=reviews.lucy, issued_on=TODAY)
        assert (second.serial_number, second.reference) == (2, "UK.CAO.[Number]-ARC-0002")
        services.void_certificate(second, "Issued Against the Wrong Aircraft")
        third = services.issue_certificate(fleet["G-ABCD"], staff=reviews.lucy, issued_on=TODAY)
        assert third.serial_number == 3
        chosen = Certificate.objects.create(
            organisation=sample.ours,
            aircraft=fleet["G-FMNO"],
            serial_number=1,
            reference="UK.CAO.[Number]-ARC-0001",
            issued_on=TODAY,
            valid_to=date(2027, 11, 18),
            issued_by=reviews.lucy,
        )
        chosen.refresh_from_db()
        assert (chosen.serial_number, chosen.reference) == (4, "UK.CAO.[Number]-ARC-0004")
        serials = Certificate.objects.filter(serial_number__isnull=False).order_by("serial_number")
        assert [certificate.serial_number for certificate in serials] == [1, 2, 3, 4]
        # The voided certificate is still there, and G-EJKL is back on its earlier one.
        assert Certificate.objects.get(pk=second.pk).voided
        assert services.current_valid_to(fleet["G-EJKL"]) == date(2026, 12, 6)
    with working_for(sample.other.id, sample.stranger.id):
        assert Certificate.objects.count() == 0


def test_what_a_certificate_says_is_never_altered(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110, hazards H-007 and H-010. Refused for the application and the owner."""
    changes = (
        "serial_number = 99",
        "reference = 'Changed'",
        "valid_to = '2028-12-02'",
        "issued_on = '2026-11-01'",
    )
    with working_for(sample.ours.id, sample.lucy.id):
        for change in changes:
            with (
                pytest.raises(DatabaseError, match="never altered"),
                transaction.atomic(),
                connection.cursor() as cursor,
            ):
                cursor.execute(
                    f"UPDATE reviews_certificate SET {change} WHERE id = %s",  # noqa: S608
                    [reviews.cdef.id],
                )
        services.void_certificate(reviews.cdef, "Test of Voiding")
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            Certificate.objects.filter(pk=reviews.cdef.pk).update(voided=False, void_reason="")
        with pytest.raises(services.RefusedError, match="Reason"):
            services.void_certificate(reviews.cdef, " ")
    with as_owner(), working_for(sample.ours.id):
        with (
            pytest.raises(DatabaseError, match="never altered"),
            transaction.atomic(),
            connection.cursor() as cursor,
        ):
            cursor.execute("UPDATE reviews_certificate SET valid_to = '2029-01-01'")


def test_two_certificates_cannot_be_allocated_a_serial_at_the_same_moment(
    sample: Sample,
) -> None:
    """REQ-110, threat TH-023, planned test T-SEC-017. Two separate connections:
    while the first holds its allocation the second waits, and is refused when
    its wait runs out; once the first has finished, the second proceeds."""
    parameters = connection.get_connection_params()
    parameters.pop("cursor_factory", None)
    parameters.pop("context", None)
    organisation = str(sample.ours.id)
    outcome: dict[str, str] = {}
    with psycopg.connect(**parameters) as first, psycopg.connect(**parameters) as second:
        first.execute("SELECT reviews_allocate_serial(%s)", [organisation])

        def contend() -> None:
            try:
                second.execute("SET lock_timeout = '300ms'")
                second.execute("SELECT reviews_allocate_serial(%s)", [organisation])
                outcome["second"] = "allocated"
            except psycopg.errors.LockNotAvailable:
                outcome["second"] = "waited"
                second.rollback()

        thread = threading.Thread(target=contend)
        thread.start()
        thread.join(timeout=10)
        assert outcome == {"second": "waited"}
        first.rollback()
        row = second.execute("SELECT reviews_allocate_serial(%s)", [organisation]).fetchone()
        assert row is not None
        assert row[0] >= 1
        second.rollback()


# Who may issue


def test_review_staff_who_have_lapsed_cannot_issue(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-109, CAO.A.045(c), threat TH-009, planned test T-SEC-012. The other
    review staff member is recent to 2 December 2026 and not on the 3rd."""
    with working_for(sample.ours.id, sample.reviewer.id):
        assert services.may_issue(reviews.reviewer, date(2026, 12, 2))
        assert not services.may_issue(reviews.reviewer, date(2026, 12, 3))
    day.today = date(2026, 12, 3)
    with working_for(sample.ours.id, sample.reviewer.id):
        with pytest.raises(services.RefusedError, match="Recent Experience"):
            services.issue_certificate(
                fleet["G-EJKL"], staff=reviews.reviewer, issued_on=date(2026, 12, 3)
            )
        # Carried out in time, on 1 December, the review keeps them current for a year.
        issued = services.issue_certificate(
            fleet["G-EJKL"], staff=reviews.reviewer, issued_on=date(2026, 12, 1)
        )
        assert issued.valid_to == date(2027, 12, 6)
        assert services.staff_line(reviews.reviewer, date(2026, 12, 3)).lapses == date(2027, 12, 1)


def test_staff_who_have_left_or_been_made_inactive_cannot_issue(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-109, REQ-115. The record of the person stays."""
    with working_for(sample.ours.id, sample.administrator.id):
        ReviewStaff.objects.filter(pk=reviews.lucy.pk).update(left_on=TODAY)
        reviews.lucy.refresh_from_db()
        assert not services.may_issue(reviews.lucy, TODAY)
        assert services.staff_line(reviews.lucy, TODAY).state == "Left"
        ReviewStaff.objects.filter(pk=reviews.lucy.pk).update(left_on=None)
        User.objects.filter(pk=sample.lucy.pk).update(is_active=False)
        assert not services.may_issue(ReviewStaff.objects.get(pk=reviews.lucy.pk), TODAY)
    assert "Lucy Grant" in page(signed_in(sample.reader), "/review-staff/")


# Recency


def test_the_staff_page_shows_recency_and_what_it_rests_on(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-113, AMC1 CAO.A.045(c). Lucy Grant: last review 11 November 2026,
    current to 11 November 2027. The other: 4 months, last review 2 December
    2025, lapsing after 2 December 2026, 14 days away: Due Soon."""
    body = page(signed_in(sample.reader), "/review-staff/")
    for text in (
        "<td>Lucy Grant</td>",
        "<td>11 November 2026</td>",
        "<td>After 11 November 2027</td>",
        f"<td>After 2 December 2026, {dot('Due Soon')}</td>",
        "<td>A Review in the Last 12 Months</td>",
        "<td>4, Recorded 18 November 2026</td>",
        "<td>Current</td>",
    ):
        assert text in body, text


def test_a_lapse_is_remembered_until_a_restoration_is_recorded(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-113, REQ-114, AMC1 CAO.A.045(d). Found by the independent recompute.
    After 2 December 2026 the other review staff member has lapsed. Raising
    their months to 6 does not make them current: only a review under the
    supervision of currently valid review staff, or of the authority, does."""
    day.today = date(2026, 12, 10)
    admin = signed_in(sample.administrator)
    staff = reviews.reviewer
    assert "Lapsed, Restoration Needed" in page(admin, "/review-staff/")

    assert post(admin, f"/review-staff/{staff.id}/involvement/", months="6").status_code == 302
    with working_for(sample.ours.id, sample.administrator.id):
        staff.refresh_from_db()
        assert staff.lapsed_on == date(2026, 12, 10)
        line = services.staff_line(staff, day.today)
        assert (line.recent, line.restoration_needed, line.state) == (
            True,
            True,
            "Lapsed, Restoration Needed",
        )
        assert not services.may_issue(staff, day.today)
        with pytest.raises(services.RefusedError, match="Their Own Restoration"):
            services.record_restoration(staff, on=day.today, supervisor=staff)
        with pytest.raises(services.RefusedError, match="Names the Supervision"):
            services.record_restoration(staff, on=day.today)
        with pytest.raises(services.RefusedError, match="Only a Lapsed"):
            services.record_restoration(
                reviews.lucy, on=day.today, under="Civil Aviation Authority"
            )

    restored = post(
        admin,
        f"/review-staff/{staff.id}/restoration/",
        on="2026-12-10",
        supervisor=str(reviews.lucy.id),
    )
    assert restored.status_code == 302
    body = page(admin, "/review-staff/")
    assert "Restored 10 December 2026 Under Lucy Grant, [Authorisation Reference 1]" in body
    with working_for(sample.ours.id, sample.administrator.id):
        staff.refresh_from_db()
        assert services.may_issue(staff, day.today)
        assert services.last_review(staff) == date(2026, 12, 10)


def test_a_lapsed_person_cannot_supervise_a_restoration(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-114, AMC1 CAO.A.045(d): another currently valid member of review staff."""
    day.today = date(2027, 11, 20)  # both have lapsed by now
    with working_for(sample.ours.id, sample.administrator.id):
        with pytest.raises(services.RefusedError, match="Currently Valid"):
            services.record_restoration(reviews.reviewer, on=day.today, supervisor=reviews.lucy)
        services.record_restoration(
            reviews.reviewer, on=day.today, under="Civil Aviation Authority, [Surveyor Name]"
        )
        assert services.may_issue(ReviewStaff.objects.get(pk=reviews.reviewer.pk), day.today)


# Extension


def test_g_ejkl_certificate_is_extended_within_30_days(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-104 to REQ-106, ML.A.901(c) and (d). 18 days before 6 December 2026:
    extended to 6 December 2027. Each condition is confirmed. The certificate
    was issued elsewhere, and the copy of its extension is still owed to the
    Civil Aviation Authority: by 28 November 2026 (REQ-111, ML.A.903(f))."""
    client = signed_in(sample.lucy)
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.current_certificate(ejkl)
    assert certificate is not None
    path = f"/certificates/{certificate.id}/extend/"
    partial = dict(CONDITIONS)
    del partial["maintained_by_approved_organisations"]
    refused = post(client, path, **partial)
    assert "ML.A.901(c): Every Condition for an Extension Is Confirmed" in refused.content.decode()

    assert post(client, path, **CONDITIONS).status_code == 302
    body = page(client, f"/aircraft/{ejkl.id}/review/")
    for text in (
        "<dd>6 December 2027</dd>",
        "<dd>1 of 2</dd>",
        "<td>[Certificate Reference G-EJKL], Extension 1</td>",
        "<td>Extended, ML.A.901(c) Conditions Confirmed</td>",
    ):
        assert text in body, text
    with working_for(sample.ours.id, sample.lucy.id):
        extension = Extension.objects.get(certificate=certificate)
        assert (extension.extended_on, extension.valid_to) == (TODAY, date(2027, 12, 6))
        with pytest.raises(IntegrityError, match="every_condition"), transaction.atomic():
            Extension.objects.filter(pk=extension.pk).update(no_evidence_not_airworthy=False)
    owed = row_for(page(client, "/reviews/"), "G-EJKL")
    assert f"To Be Sent by 28 November 2026, {dot('Due Soon')}" in owed
    sent = post(client, f"/extensions/{extension.id}/copy-sent/", on="2026-11-18")
    assert sent.status_code == 302
    assert "To Be Sent" not in row_for(page(client, "/reviews/"), "G-EJKL")


def test_extensions_are_limited_to_two_and_to_the_30_days_before_expiry(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-104, REQ-106. G-ABCD, valid to 14 March 2027: 116 days away is too
    early. G-EJKL: extended twice, a third is refused."""

    def extend(certificate: Certificate) -> Extension:
        return services.extend_certificate(
            certificate,
            extended_by=sample.lucy,
            managed_for_12_months=True,
            maintained_by_approved_organisations=True,
            no_evidence_not_airworthy=True,
        )

    with working_for(sample.ours.id, sample.lucy.id):
        abcd = services.current_certificate(fleet["G-ABCD"])
        ejkl = services.current_certificate(fleet["G-EJKL"])
        assert abcd is not None
        assert ejkl is not None
        with pytest.raises(services.RefusedError, match="at most 30 days"):
            extend(abcd)
        extend(ejkl)
        # G-ABCD the day after its certificate ran out: a review is needed.
        day.today = date(2027, 3, 15)
        with pytest.raises(services.RefusedError, match="expired"):
            extend(abcd)
        day.today = date(2027, 11, 20)
        second = extend(ejkl)
        assert second.valid_to == date(2028, 12, 6)
        day.today = date(2028, 11, 20)
        with pytest.raises(services.RefusedError, match="at most two consecutive"):
            extend(ejkl)


# Recording a certificate issued elsewhere


def test_a_certificate_issued_elsewhere_keeps_its_own_reference(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-100, REQ-110. As when an aircraft is taken on: no serial of ours is used."""
    client = signed_in(sample.planner)
    hklm = fleet["G-HKLM"]
    fields = {
        "reference": "[Certificate Reference G-HKLM]",
        "issued_elsewhere_by": "[Previous Organisation]",
        "issued_on": "2026-05-20",
        "valid_to": "2027-05-20",
    }
    assert post(client, f"/aircraft/{hklm.id}/review/certificates/", **fields).status_code == 302
    again = post(client, f"/aircraft/{hklm.id}/review/certificates/", **fields)
    assert "This Certificate Reference Is Already Recorded" in again.content.decode()
    with working_for(sample.ours.id, sample.planner.id):
        recorded = Certificate.objects.get(aircraft=hklm)
        assert (recorded.serial_number, recorded.issued_by) == (None, None)
        for values, message in (
            ({**fields, "valid_to": "2026-05-20"}, "Expires After"),
            ({**fields, "issued_on": "2026-11-19"}, "After Today"),
        ):
            with pytest.raises(services.RefusedError, match=message):
                services.record_certificate(
                    hklm,
                    reference="[Another Reference]",
                    issued_elsewhere_by="[Previous Organisation]",
                    issued_on=date.fromisoformat(values["issued_on"]),
                    valid_to=date.fromisoformat(values["valid_to"]),
                )


def test_a_certificate_from_before_these_records_can_be_the_organisations_own(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110, REQ-113; Issue 71, D-3. It names the review staff member, keeps
    the reference it was issued with and uses no serial. It is dated no later
    than the person's last review before these records, which the Administrator
    states, so that recording it cannot change whether the person is recent."""
    client = signed_in(sample.planner)
    hklm = fleet["G-HKLM"]
    path = f"/aircraft/{hklm.id}/review/certificates/"
    fields = {
        "reference": "[Certificate Reference G-HKLM]",
        "issued_by": str(reviews.lucy.id),
        "issued_on": "2026-05-20",
        "valid_to": "2027-05-20",
    }
    with working_for(sample.ours.id, sample.lucy.id):
        before = services.staff_line(reviews.lucy, TODAY)
    # Lucy Grant's last review before these records is 2 August 2026.
    for values, message in (
        ({**fields, "issued_elsewhere_by": "[Previous Organisation]"}, "Not Both"),
        ({**fields, "issued_by": ""}, "Has Its Reference and Its Issuer"),
        ({**fields, "issued_on": "2026-08-03"}, "No Later Than the Person"),
    ):
        refused = post(client, path, **values)
        assert refused.status_code == 200
        assert message in refused.content.decode(), message
    assert post(client, path, **fields).status_code == 302
    with working_for(sample.ours.id, sample.lucy.id):
        recorded = Certificate.objects.get(aircraft=hklm)
        assert (recorded.serial_number, recorded.reference) == (
            None,
            "[Certificate Reference G-HKLM]",
        )
        assert (recorded.issued_by, recorded.from_before_records) == (reviews.lucy, True)
        # Whether she is recent, and until when, is as it was.
        after = services.staff_line(reviews.lucy, TODAY)
        assert (after.last_review, after.lapses) == (before.last_review, before.lapses)
        # The next certificate issued here takes the next serial: none was used.
        ejkl = services.issue_certificate(fleet["G-EJKL"], staff=reviews.lucy, issued_on=TODAY)
        assert (reviews.cdef.serial_number, ejkl.serial_number) == (1, 2)
        assert not ejkl.from_before_records
        # What it says cannot be changed afterwards.
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            Certificate.objects.filter(pk=recorded.pk).update(from_before_records=False)
    body = page(client, f"/aircraft/{hklm.id}/review/")
    assert "<td>Lucy Grant, [Authorisation Reference 1], Before These Records</td>" in body
    assert f"/certificates/{recorded.id}/copy-sent/" not in body  # no copy is owed for it now
    with working_for(sample.ours.id, sample.lucy.id):
        assert services.schedule_line(hklm, TODAY).copies == ()
    detail = page(client, f"/certificates/{recorded.id}/")
    for text in (
        "<p>Recorded From Before These Records</p>",
        "<dd>Lucy Grant</dd>",
        "<dd>[Authorisation Reference 1]</dd>",
    ):
        assert text in detail, text


def test_the_database_holds_a_certificate_from_before_to_the_same_rule(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-109, REQ-110, hazard H-007. Whatever the application does, a certificate
    of the organisation's own with no review behind it is one from before the
    person's last review before these records, and an ordinary one has a serial."""
    hklm = fleet["G-HKLM"]

    def create(**values: object) -> Certificate:
        with transaction.atomic():
            return Certificate.objects.create(
                organisation_id=hklm.organisation_id,
                aircraft=hklm,
                valid_to=date(2027, 10, 1),
                **values,
            )

    with working_for(sample.ours.id, sample.lucy.id):
        with pytest.raises(DatabaseError, match="before these records"):
            create(
                reference="[A]",
                issued_on=date(2026, 10, 1),
                issued_by=reviews.lucy,
                from_before_records=True,
            )
        with pytest.raises(IntegrityError, match="certificate_from_before"):
            create(
                reference="[B]",
                issued_on=date(2026, 5, 1),
                issued_elsewhere_by="[Previous Organisation]",
                from_before_records=True,
            )
        # A reference typed for an ordinary certificate is replaced: it has its serial.
        ordinary = create(reference="[C]", issued_on=date(2026, 10, 1), issued_by=reviews.lucy)
        ordinary.refresh_from_db()
        assert (ordinary.serial_number, ordinary.reference) == (2, "UK.CAO.[Number]-ARC-0002")
        elsewhere = create(
            reference="[D]", issued_on=date(2026, 5, 1), issued_elsewhere_by="[Previous]"
        )
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            Certificate.objects.filter(pk=elsewhere.pk).update(issued_elsewhere_by="[Another]")


def test_the_last_review_before_these_records_is_not_moved_before_a_certificate(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-113. The date the Administrator states stays on or after every
    certificate of the person recorded from before these records. Lucy Grant's
    latest is G-BXYZ's, 2 August 2026."""
    with working_for(sample.ours.id, sample.administrator.id):
        for earlier in (date(2026, 8, 1), None):
            with pytest.raises(services.RefusedError, match="Is Dated 2 August 2026"):
                services.update_involvement(
                    reviews.lucy, months=0, last_review_before_records=earlier
                )
        services.update_involvement(
            reviews.lucy, months=0, last_review_before_records=date(2026, 8, 2)
        )


def test_a_restoration_does_not_move_the_limit_on_a_certificate_from_before(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-109, REQ-110; found by the independent review of 19 November 2026.
    A restoration was written into the person's last review before these
    records, so a certificate dated inside these records, with no review and
    no serial, could then be recorded as theirs. The restoration now has its
    own date, and the last review before these records is never after the
    day the person was recorded as review staff."""
    day.today = date(2027, 1, 20)
    staff = reviews.reviewer
    planner = signed_in(sample.planner)
    hklm = fleet["G-HKLM"]
    fields = {
        "reference": "[Made Up Reference]",
        "issued_by": str(staff.id),
        "issued_on": "2027-01-15",
        "valid_to": "2028-01-15",
    }
    path = f"/aircraft/{hklm.id}/review/certificates/"
    assert "No Later Than the Person" in post(planner, path, **fields).content.decode()

    with working_for(sample.ours.id, sample.administrator.id):
        services.record_restoration(staff, on=date(2027, 1, 15), supervisor=reviews.lucy)
        staff.refresh_from_db()
        # The restoration counts as the person's last review, and they are current again.
        assert services.last_review(staff) == date(2027, 1, 15)
        assert services.may_issue(staff, day.today)
        # It is not their last review before these records, which stays where it was.
        assert staff.last_review_before_records == date(2025, 12, 2)
        assert staff.recorded_on == TODAY

    refused = post(planner, path, **fields)
    assert refused.status_code == 200
    assert "No Later Than the Person" in refused.content.decode()
    with working_for(sample.ours.id, sample.administrator.id):
        assert not Certificate.objects.filter(aircraft=hklm).exists()
        # Nor can the Administrator state a last review before these records
        # that is after the day the person was recorded as review staff.
        with pytest.raises(services.RefusedError, match="Recorded as Review Staff"):
            services.update_involvement(
                staff, months=4, last_review_before_records=date(2027, 1, 15)
            )
        with pytest.raises(services.RefusedError, match="Recorded as Review Staff"):
            services.add_review_staff(
                user=sample.planner,
                authorisation_reference="[Authorisation Reference 3]",
                accepted_on=date(2027, 1, 1),
                last_review_before_records=date(2027, 1, 21),
            )
        # The database holds to it whatever the application does.
        with pytest.raises(IntegrityError, match="before_records"), transaction.atomic():
            ReviewStaff.objects.filter(pk=staff.pk).update(
                last_review_before_records=date(2027, 1, 15)
            )
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            ReviewStaff.objects.filter(pk=staff.pk).update(recorded_on=date(2027, 6, 1))


def test_an_aircraft_with_no_certificate_comes_near_the_top_of_the_fleet(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """Dogfooding D-5; found by the independent review of 19 November 2026. With
    its only certificate voided, G-EJKL had nothing ranked and fell to the
    bottom of the Fleet. Nobody knows where it stands, so it comes straight
    after the Unserviceable aircraft, as it comes first on the review schedule."""
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.current_certificate(fleet["G-EJKL"])
        assert certificate is not None
        services.void_certificate(certificate, "Recorded in Error")
    body = page(signed_in(sample.reader), "/")
    order = sorted(
        ("G-DGHI", "G-EJKL", "G-ABCD", "G-FMNO", "G-BXYZ", "G-CDEF"),
        key=lambda registration: body.index(f">{registration}</a>"),
    )
    assert order[:2] == ["G-DGHI", "G-EJKL"]
    assert body.index(">G-EJKL</a>") < body.index(">G-ABCD</a>")


# How each figure was worked out (REQ-139, hazard H-014)


def opened(body: str, title: str) -> str:
    """Return the working shown under ``title``."""
    assert f"<summary>{title}</summary>" in body, title
    return body.split(f"<summary>{title}</summary>", 1)[1].split("</details>", 1)[0]


def test_every_figure_of_a_review_certificate_shows_how_it_was_reached(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-139. G-EJKL, valid to 6 December 2026, on 18 November 2026.

    By hand. 12 days left in November and 6 in December: 18 days. 90 days
    before 6 December: 6 + 30 + 31 + 23 reaches 7 September 2026. 30 days
    before: 6 + 24 reaches 6 November 2026. Its date of expiry was recorded
    from the aircraft records, so it is shown as recorded, not as calculated.
    """
    client = signed_in(sample.lucy)
    ejkl = fleet["G-EJKL"]
    body = page(client, f"/aircraft/{ejkl.id}/review/")
    recorded = opened(body, "Where Valid to 6 December 2026 Comes From")
    assert "as Recorded. It Is Not Calculated" in recorded
    assert "<dt>Source</dt><dd>The Certificate, CAA Form 15c</dd>" in recorded
    days = opened(body, "How 18 Days Remaining Was Calculated")
    for text in (
        "<dt>Today</dt><dd>18 November 2026</dd>",
        "<dt>Valid To</dt><dd>6 December 2026</dd>",
        "Due Soon at 30 Days or Fewer",
    ):
        assert text in days, text
    window = opened(body, "How the 90-Day Window Was Calculated")
    assert "<dt>Window Opens</dt><dd>7 September 2026</dd>" in window
    assert "<dt>Source</dt><dd>ML.A.903(d)</dd>" in window
    extensions = opened(body, "How 0 of 2 Extensions Was Counted")
    assert "<dt>An Extension Can Be Made From</dt><dd>6 November 2026</dd>" in extensions
    assert "<dt>Source</dt><dd>ML.A.901(c) and (d)</dd>" in extensions

    # Extended today: a year on from 6 December 2026, and a copy owed in 10 days.
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.current_certificate(ejkl)
    assert certificate is not None
    assert post(client, f"/certificates/{certificate.id}/extend/", **CONDITIONS).status_code == 302
    body = page(client, f"/aircraft/{ejkl.id}/review/")
    extended = opened(body, "How Valid to 6 December 2027 Was Calculated")
    for text in (
        "Each Extension Adds 1 Year to the Date of Expiry Before It",
        "<dt>Date of Expiry Before Any Extension</dt><dd>6 December 2026</dd>",
        "<dt>Extension 1</dt><dd>Made 18 November 2026, Valid to 6 December 2027</dd>",
    ):
        assert text in extended, text
    opened(body, "How 1 of 2 Extensions Was Counted")
    copy = opened(body, "How the Copy by 28 November 2026 Was Calculated")
    assert "<dt>Date of Extension</dt><dd>18 November 2026</dd>" in copy
    assert "<dt>Source</dt><dd>ML.A.903(f)</dd>" in copy


def test_a_certificate_issued_here_shows_the_rule_that_gave_its_expiry(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-139, REQ-101, REQ-102. G-CDEF, reviewed 11 November 2026 with the
    certificate before it ending 2 December 2026.

    By hand. 90 days before 2 December: 2 + 30 + 31 + 27 reaches 3 September
    2026, so 11 November is inside the window and the new certificate runs a
    year from 2 December 2026. The copy: 11 + 10 is 21 November 2026.

    G-HKLM has no certificate before: a year from the review, 18 November 2027.
    """
    client = signed_in(sample.reader)
    body = page(client, f"/aircraft/{fleet['G-CDEF'].id}/review/")
    kept = opened(body, "How Valid to 2 December 2027 Was Calculated")
    for text in (
        "A Review in the 90 Days Before the Date of Expiry Keeps the Pattern",
        "Which Is To Be Confirmed",
        "<dt>Date of Issue</dt><dd>11 November 2026</dd>",
        "<dt>Certificate Before It</dt><dd>[Certificate Reference G-CDEF]</dd>",
        "<dt>Its Date of Expiry</dt><dd>2 December 2026</dd>",
        "<dt>90-Day Window Opened</dt><dd>3 September 2026</dd>",
        "<dt>Source</dt><dd>ML.A.903(d)</dd>",
    ):
        assert text in kept, text
    opened(body, "How 379 Days Remaining Was Calculated")
    copy = opened(body, "How the Copy by 21 November 2026 Was Calculated")
    assert "<dt>Date of Issue</dt><dd>11 November 2026</dd>" in copy
    assert "<dt>Days Allowed</dt><dd>10</dd>" in copy

    with working_for(sample.ours.id, sample.lucy.id):
        services.issue_certificate(fleet["G-HKLM"], staff=reviews.lucy, issued_on=TODAY)
        line = services.schedule_line(fleet["G-HKLM"], TODAY)
        first = services.working(line, TODAY)[0]
    assert first.title == "How Valid to 18 November 2027 Was Calculated"
    assert first.rule.startswith("Valid for 1 Year From the Review")
    assert first.source == "ML.A.901(a)"


def test_the_working_never_gives_a_rule_that_does_not_give_the_date(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-139, hazard H-014. For every aircraft of the sample: a date that is
    explained by a rule is the date that rule gives from the inputs shown."""
    with working_for(sample.ours.id, sample.reader.id):
        for line in services.schedule(sample.ours, TODAY):
            if line.certificate is None:
                continue
            validity, remaining, window, *_ = services.working(line, TODAY)
            assert line.valid_to is not None
            assert validity.figure == long_date(line.valid_to)
            assert remaining.figure == f"{line.days} Days"
            given = dict(validity.inputs)
            if "Its Date of Expiry" in given and "Keeps the Pattern" in validity.rule:
                before = services.valid_to(
                    Certificate.objects.get(reference=given["Certificate Before It"])
                )
                assert add_years(before, 1) == line.valid_to
            elif validity.rule.startswith("Valid for 1 Year From the Review"):
                assert add_years(line.certificate.issued_on, 1) == line.valid_to
            elif "Extension" not in validity.rule:
                assert "It Is Not Calculated" in validity.rule
            opens = dict(window.inputs)["Window Opens"]
            assert opens == long_date(line.valid_to - timedelta(days=90))


def test_a_working_says_so_when_the_records_changed_after_the_certificate(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-139, hazard H-014; found by the independent review of 19 November
    2026. G-HKLM has no certificate. One is issued on 18 November 2026: a year
    from the review, 18 November 2027. The certificate it followed is then
    recorded, ending 2 December 2026, 14 days after the review. The working
    must not say the review was outside the 90 days beside inputs that show
    it was inside them."""
    hklm = fleet["G-HKLM"]
    with working_for(sample.ours.id, sample.lucy.id):
        services.issue_certificate(hklm, staff=reviews.lucy, issued_on=TODAY)
        services.record_certificate(
            hklm,
            reference="[Earlier]",
            issued_elsewhere_by="[Previous Organisation]",
            issued_on=date(2025, 12, 2),
            valid_to=date(2026, 12, 2),
        )
        validity = services.working(services.schedule_line(hklm, TODAY), TODAY)[0]
    assert validity.figure == "18 November 2027"
    assert "Was Not in the 90 Days" not in validity.rule
    assert "Set When the Certificate Was Issued" in validity.rule
    assert validity.title == "Where Valid to 18 November 2027 Comes From"


def test_no_day_is_given_for_an_extension_that_cannot_be_made(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    """REQ-104, REQ-139; found by the independent review of 19 November 2026.
    After two extensions a third is refused, so the working gives no day for one."""
    ejkl = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = services.current_certificate(ejkl)
        assert certificate is not None
        for today in (TODAY, date(2027, 11, 20)):
            day.today = today
            services.extend_certificate(
                certificate,
                extended_by=sample.lucy,
                managed_for_12_months=True,
                maintained_by_approved_organisations=True,
                no_evidence_not_airworthy=True,
            )
        found = services.working(services.schedule_line(ejkl, day.today), day.today)
    counted = next(one for one in found if one.title == "How 2 of 2 Extensions Was Counted")
    labels = [label for label, _ in counted.inputs]
    assert "An Extension Can Be Made From" not in labels
    assert ("Next", "No Further Extension: a Review Is Needed") in counted.inputs


def test_recency_shows_what_it_rests_on_and_the_rule(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-139, REQ-113, AMC1 CAO.A.045(c). The other review staff member: 4
    months, last review 2 December 2025, which counts to 2 December 2026."""
    body = page(signed_in(sample.reader), "/review-staff/")
    assert body.count("<summary>How Recency Was Worked Out</summary>") == 2
    theirs = body.split("[Review Name]", 1)[1]
    working = opened(theirs, "How Recency Was Worked Out")
    for text in (
        "6 Months of Continuing Airworthiness Management in the 2-Year Period",
        "1 Airworthiness Review in the Last 12 Months",
        "<dt>Last Review</dt><dd>2 December 2025</dd>",
        "<dd>4, Recorded 18 November 2026</dd>",
        "<dt>Recency Rests On</dt><dd>A Review in the Last 12 Months</dd>",
        "<dt>Last Day the Last Review Counts</dt><dd>2 December 2026</dd>",
        "<dt>Source</dt><dd>AMC1 CAO.A.045(c) and (d)</dd>",
    ):
        assert text in working, text


# The Fleet and the programme page


def test_the_fleet_sets_the_review_beside_the_programme(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-100, SampleData.md, Fleet, Next Due and Review Certificate Valid To.
    G-EJKL: Airworthiness Review, 18 Days. G-DGHI: Rectify Defect. G-CDEF: the
    engine overhaul, projected at 366 days, comes before the review at 379."""
    body = page(signed_in(sample.reader), "/")
    assert "<td>Airworthiness Review</td><td>18 Days</td>" in row_for(body, "G-EJKL")
    assert "<td>6 December 2026</td>" in row_for(body, "G-EJKL")
    assert "<td>Rectify Defect</td>" in row_for(body, "G-DGHI")
    assert "<td>19 May 2027</td>" in row_for(body, "G-DGHI")
    assert "<td>50-Hour Check</td><td>12.4 Hours</td>" in row_for(body, "G-ABCD")
    assert "<td>100-Hour or Annual Check</td><td>41.0 Hours</td>" in row_for(body, "G-BXYZ")
    assert "<td>Annual Check</td><td>78 Days</td>" in row_for(body, "G-FMNO")
    assert "<td>Engine Overhaul</td><td>220.0 Hours</td>" in row_for(body, "G-CDEF")
    assert "<td>2 December 2027</td>" in row_for(body, "G-CDEF")


def test_a_tolerance_that_ends_after_the_certificate_says_so(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-057, AMC1 ML.A.302(d), golden. G-BXYZ: the calendar tolerance ends
    30 August 2027; the certificate is valid to 2 August 2027. G-FMNO: the
    tolerance ends 4 March 2027, before the certificate's 27 April 2027."""
    client = signed_in(sample.reader)
    bxyz = page(client, f"/aircraft/{fleet['G-BXYZ'].id}/programme/")
    assert "<td>30 August 2027, After the Review Certificate Ends 2 August 2027</td>" in bxyz
    assert "<td>3,369.0 Hours</td>" in bxyz
    assert "After the Review Certificate" not in page(
        client, f"/aircraft/{fleet['G-FMNO'].id}/programme/"
    )


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews):  # type: ignore[no-untyped-def]
    certificate = reviews.cdef
    aircraft = fleet["G-CDEF"]
    return [
        ("GET", "/reviews/", Action.VIEW_RECORDS),
        ("GET", "/review-staff/", Action.VIEW_RECORDS),
        ("GET", f"/aircraft/{aircraft.id}/review/", Action.VIEW_RECORDS),
        ("POST", f"/aircraft/{aircraft.id}/review/certificates/", Action.ADD_OR_CHANGE_AIRCRAFT),
        (
            "POST",
            f"/certificates/{certificate.id}/extend/",
            Action.EXTEND_AIRWORTHINESS_REVIEW_CERTIFICATE,
        ),
        (
            "POST",
            f"/certificates/{certificate.id}/copy-sent/",
            Action.RECORD_COPY_SENT_TO_THE_AUTHORITY,
        ),
        ("POST", "/review-staff/add/", Action.MANAGE_USERS_AND_ROLES),
        ("POST", f"/review-staff/{reviews.lucy.id}/involvement/", Action.MANAGE_USERS_AND_ROLES),
        ("POST", f"/review-staff/{reviews.lucy.id}/restoration/", Action.MANAGE_USERS_AND_ROLES),
    ]


def test_another_organisations_certificates_and_staff_are_not_found_or_shown(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    stranger = signed_in(sample.stranger)
    for method, path, _ in addresses(sample, fleet, reviews)[2:]:
        if path != "/review-staff/add/":
            assert call(stranger, method, path).status_code == 404, f"{method} {path}"
    assert "G-CDEF" not in page(stranger, "/reviews/")
    assert "Lucy Grant" not in page(stranger, "/review-staff/")
    with as_owner():
        assert Extension.objects.count() == 0
        assert Certificate.objects.get(pk=reviews.cdef.pk).copy_sent_on is None


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_every_review_page_follows_the_role_matrix(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in addresses(sample, fleet, reviews):
        status = call(client, method, path).status_code
        if permitted(user.roles, action):
            assert status in (200, 302), f"{role} {method} {path}"
        else:
            assert status == 403, f"{role} {method} {path}"
            refusals += 1
    with working_for(sample.ours.id, user.id):
        logged = AccessEntry.objects.filter(user=user, kind="Action Refused").count()
    assert logged == refusals
    expected = {
        "Administrator": 3,
        "Airworthiness Review Staff": 4,
        "Planning and Records": 4,
        "Read Only": 6,
    }
    assert refusals == expected[role]


def test_review_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    pages = addresses(sample, fleet, reviews)
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


def test_review_authorisation_records_scope_and_refuses_issue_after_its_end(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews, day: Day
) -> None:
    path = f"/review-staff/{reviews.lucy.id}/authorisation/"
    details = {
        "version": services.review_authorisation_version(reviews.lucy),
        "authorisation_scope": "Part-ML aeroplanes under the CAE",
        "authorisation_valid_to": "2026-11-18",
    }
    assert post(signed_in(sample.reader), path, **details).status_code == 403
    assert post(signed_in(sample.administrator), path, **details).status_code == 302
    stale = post(
        signed_in(sample.administrator),
        path,
        **{
            **details,
            "authorisation_scope": "Scope from another editor",
            "authorisation_valid_to": "",
        },
    )
    assert "Authorisation Changed" in stale.content.decode()
    board = page(signed_in(sample.reader), "/review-staff/")
    assert "Part-ML aeroplanes under the CAE" in board
    assert "Part-ML aeroplanes under the CAE" not in page(
        signed_in(sample.stranger), "/review-staff/"
    )
    with working_for(sample.ours.id, sample.lucy.id):
        assert services.may_issue(ReviewStaff.objects.get(pk=reviews.lucy.pk), day.today)
        with pytest.raises(services.RefusedError, match="Confirm the Review Authorisation"):
            services.start_review(fleet["G-EJKL"], staff=reviews.lucy)
        active_staff = ReviewStaff.objects.get(pk=reviews.lucy.pk)
        with pytest.raises(services.RefusedError, match="Review Authorisation Changed"):
            services.start_review(
                fleet["G-EJKL"],
                staff=reviews.lucy,
                scope_confirmed=True,
                scope_version=services.review_authorisation_version(reviews.lucy),
            )
        draft = services.start_review(
            fleet["G-EJKL"],
            staff=active_staff,
            scope_confirmed=True,
            scope_version=services.review_authorisation_version(active_staff),
        )
        assert draft.confirmed_authorisation_scope == "Part-ML aeroplanes under the CAE"
        issued = services.issue_certificate(
            fleet["G-EJKL"], staff=reviews.lucy, issued_on=day.today
        )
        assert issued.review_staff_scope == "Part-ML aeroplanes under the CAE"
        assert issued.review_staff_valid_to == day.today
        day.today = date(2026, 11, 19)
        with pytest.raises(services.RefusedError, match="Does Not Cover the Review Start Date"):
            services.start_review(fleet["G-EJKL"], staff=reviews.lucy)
        with pytest.raises(services.RefusedError, match="Review Authorisation Ended"):
            services.issue_certificate(fleet["G-EJKL"], staff=reviews.lucy, issued_on=day.today)


def test_management_experience_snapshot_ages_out_of_review_recency(
    sample: Sample,
    reviews: SampleReviews,
    day: Day,
) -> None:
    day.today = date(2027, 12, 3)
    with working_for(sample.ours.id, sample.administrator.id):
        ReviewStaff.objects.filter(pk=reviews.reviewer.pk).update(
            months_involved=6, months_recorded_on=date(2025, 12, 3)
        )
        reviews.reviewer.refresh_from_db()
        assert not services.may_issue(reviews.reviewer, day.today)
        assert services.staff_line(reviews.reviewer, day.today).months_usable == 0
