"""Review certificates, extensions, the schedule and review staff (REQ-100 to REQ-116).

The certificates and people are those of design-system/SampleData.md.
Today in the sample world is 18 November 2026.
"""

import threading
from datetime import date
from decimal import Decimal

import psycopg
import pytest
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.http import HttpResponse
from django.test import Client

from airworthiness_plus.accounts.models import AccessEntry, User
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.session import working_for
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.models import Certificate, Extension, ReviewStaff
from airworthiness_rules.programme import Flag
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    SampleReviews,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    make_sample,
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


def get(client: Client, path: str) -> HttpResponse:
    return client.get(path, secure=True)  # type: ignore[return-value]


def post(client: Client, path: str, **values: str) -> HttpResponse:
    return client.post(path, values, secure=True)  # type: ignore[return-value]


def page(client: Client, path: str) -> str:
    response = get(client, path)
    assert response.status_code == 200, path
    return response.content.decode()


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
        "<td>18 Days</td>",
        "<td>Due Soon</td>",
        "<td>Inside the 90-Day Window</td>",
    ):
        assert text in ejkl, text
    order = [body.index(f">{registration}</a>") for registration in ("G-EJKL", "G-ABCD", "G-FMNO")]
    assert order == sorted(order)
    abcd = row_for(body, "G-ABCD")
    assert "<td>14 March 2027</td>" in abcd
    assert "<td>116 Days</td>" in abcd  # 12 + 31 + 31 + 28 + 14
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
    assert "<td>379 Days</td>" in cdef  # 12 in November, 365 to 30 November 2027, 2 in December
    assert "<td>To Be Sent by 21 November 2026, Due Soon</td>" in cdef
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
    assert "To Be Sent by 21 November 2026, Overdue" in row_for(page(client, "/reviews/"), "G-CDEF")
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
        serials = Certificate.objects.filter(issued_by__isnull=False).order_by("serial_number")
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
        "<td>After 2 December 2026, Due Soon</td>",
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
    extended to 6 December 2027. Each condition is confirmed; a copy is owed."""
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


# The Fleet and the programme page


def test_the_fleet_sets_the_review_beside_the_programme(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-100, SampleData.md, Fleet, Next Due and Review Certificate Valid To.
    G-EJKL: Airworthiness Review, 18 Days. G-DGHI: Rectify Defect. G-CDEF: the
    engine overhaul, projected at 366 days, comes before the review at 379."""
    body = page(signed_in(sample.reader), "/")
    assert "<td>Airworthiness Review, 18 Days</td>" in row_for(body, "G-EJKL")
    assert "<td>6 December 2026</td>" in row_for(body, "G-EJKL")
    assert "<td>Rectify Defect</td>" in row_for(body, "G-DGHI")
    assert "<td>19 May 2027</td>" in row_for(body, "G-DGHI")
    assert "<td>50-Hour Check, 12.4 Hours</td>" in row_for(body, "G-ABCD")
    assert "<td>100-Hour or Annual Check, 41.0 Hours</td>" in row_for(body, "G-BXYZ")
    assert "<td>Annual Check, 78 Days</td>" in row_for(body, "G-FMNO")
    assert "<td>Engine Overhaul, 220.0 Hours</td>" in row_for(body, "G-CDEF")
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


def call(client: Client, method: str, path: str) -> HttpResponse:
    return get(client, path) if method == "GET" else post(client, path)


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
