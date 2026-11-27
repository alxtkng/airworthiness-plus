"""The airworthiness review and the certificate issued from it (REQ-107 to REQ-110, REQ-112).

G-EJKL of design-system/SampleData.md: certificate valid to 6 December 2026,
reviewed on 18 November 2026 by the review staff member whose recency lapses
on 2 December 2026 and who is not qualified under Part-66.

By hand. 18 November 2026 is 18 days before 6 December 2026, inside the 90
days of ML.A.903(d), so the new certificate runs a year from the old expiry:
6 December 2027. The copy goes to the Civil Aviation Authority within 10 days
of issue, ML.A.903(f): 18 + 10 = 28 November 2026. The certificate for G-CDEF
took serial 1, so this one takes serial 2.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction
from django.test import Client
from django.test.utils import CaptureQueriesContext

from airworthiness_plus.accounts.models import AccessEntry
from airworthiness_plus.accounts.roles import Action, permitted
from airworthiness_plus.aircraft import services as aircraft_services
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Event
from airworthiness_plus.history.session import working_for
from airworthiness_plus.reviews import services
from airworthiness_plus.reviews.checklist import CHECKLIST, RECORDS, SURVEY
from airworthiness_plus.reviews.models import (
    Certificate,
    ProgrammeDiscrepancy,
    Result,
    Review,
    ReviewItem,
    ReviewStaff,
)
from tests.conftest import as_owner
from tests.support import (
    TODAY,
    Sample,
    SampleReviews,
    add_sample_fleet,
    add_sample_programmes,
    add_sample_reviews,
    call,
    page,
    post,
    signed_in,
)

pytestmark = pytest.mark.django_db
D = Decimal
EVIDENCE = "[Evidence Sampled]"


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


@pytest.fixture
def ejkl(sample: Sample, fleet: dict[str, Aircraft]) -> Aircraft:
    """G-EJKL with the entries CAA Form 15c asks for."""
    aircraft = fleet["G-EJKL"]
    with working_for(sample.ours.id, sample.planner.id):
        aircraft_services.record_details(
            aircraft,
            serial_number="[Aircraft Serial Number]",
            manufacturer="[Aircraft Manufacturer]",
            designation="[Manufacturer Designation]",
        )
    return aircraft


@pytest.fixture
def review(sample: Sample, ejkl: Aircraft, reviews: SampleReviews) -> Review:
    """A review of G-EJKL started today by the review staff member."""
    with working_for(sample.ours.id, sample.reviewer.id):
        return services.start_review(ejkl, staff=reviews.reviewer)


def complete(sample: Sample, review: Review, *, assisted_by: str = "[Part-66 Name]") -> None:
    """Record every point Satisfactory, and the survey, hours and programme."""
    with working_for(sample.ours.id, sample.reviewer.id):
        for item in review.items.all():
            services.record_item(item, result=Result.SATISFACTORY, evidence=EVIDENCE)
        services.record_details(
            review,
            assisted_by=assisted_by,
            airframe_hours=D("11206.8"),
            programme_discrepancy=ProgrammeDiscrepancy.NONE_FOUND,
        )


# The checklist


def test_the_checklist_is_the_points_of_ml_a_903() -> None:
    """REQ-107, REQ-108. ML.A.903(a)(1) to (11), then (c)(1) to (5), each once and in order."""
    references = [point.reference for point in CHECKLIST]
    assert references == [f"ML.A.903(a)({n})" for n in range(1, 12)] + [
        f"ML.A.903(c)({n})" for n in range(1, 6)
    ]
    assert [point.part for point in CHECKLIST] == [RECORDS] * 11 + [SURVEY] * 5
    # Only the two points the regulation words as "if required" may be Not Applicable.
    assert [point.reference for point in CHECKLIST if point.may_not_apply] == [
        "ML.A.903(a)(9)",
        "ML.A.903(a)(11)",
    ]


def test_a_review_starts_with_every_point_to_be_verified(
    sample: Sample, ejkl: Aircraft, reviews: SampleReviews
) -> None:
    """REQ-107, REQ-108. No result is filled in in advance (hazard H-014)."""
    client = signed_in(sample.reviewer)
    response = post(client, f"/aircraft/{ejkl.id}/review/start/")
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reviewer.id):
        review = Review.objects.get(aircraft=ejkl)
        assert review.staff == reviews.reviewer
        assert review.started_on == TODAY
        items = list(review.items.all())
    assert response["Location"] == f"/reviews/{review.id}/"
    assert [item.reference for item in items] == [point.reference for point in CHECKLIST]
    assert all(not item.result and not item.evidence for item in items)
    body = page(client, f"/reviews/{review.id}/")
    assert body.count("<td>To Be Verified</td>") == 16
    assert "Issue Airworthiness Review Certificate for G-EJKL" not in body
    assert "<li>No Result Yet for ML.A.903(a)(1), " in body


def test_only_review_staff_start_a_review(sample: Sample, ejkl: Aircraft) -> None:
    """REQ-109. Holding the role is not enough: the person is on the review staff record."""
    client = signed_in(sample.reviewer)
    assert post(client, f"/aircraft/{ejkl.id}/review/start/").status_code == 403
    with working_for(sample.ours.id, sample.reviewer.id):
        assert Review.objects.count() == 0
        assert AccessEntry.objects.filter(user=sample.reviewer, kind="Action Refused").count() == 1


def test_a_result_comes_with_its_evidence_and_not_applicable_only_where_allowed(
    sample: Sample, review: Review
) -> None:
    """REQ-107. Checked by the service and again by the database."""
    with working_for(sample.ours.id, sample.reviewer.id):
        items = {item.reference: item for item in review.items.all()}
        first, mass = items["ML.A.903(a)(1)"], items["ML.A.903(a)(9)"]
        with pytest.raises(services.RefusedError, match="Evidence"):
            services.record_item(first, result=Result.SATISFACTORY, evidence=" ")
        with pytest.raises(services.RefusedError, match="Applies to Every Aircraft"):
            services.record_item(first, result=Result.NOT_APPLICABLE, evidence=EVIDENCE)
        with pytest.raises(services.RefusedError, match="Finding Is Described"):
            services.record_item(first, result=Result.FINDING, evidence=EVIDENCE)
        services.record_item(mass, result=Result.NOT_APPLICABLE, evidence=EVIDENCE)
        for values in (
            {"result": Result.NOT_APPLICABLE, "evidence": EVIDENCE},
            {"result": Result.SATISFACTORY, "evidence": ""},
            {"result": Result.SATISFACTORY, "evidence": EVIDENCE, "finding": "[Finding]"},
            {"result": Result.FINDING, "evidence": EVIDENCE, "finding": "x", "closure": "y"},
        ):
            with pytest.raises(DatabaseError), transaction.atomic():
                ReviewItem.objects.filter(pk=first.pk).update(**values)
    client = signed_in(sample.reviewer)
    body = post(client, f"/review-items/{first.id}/", result="Not Applicable", evidence=EVIDENCE)
    assert "This Point Applies to Every Aircraft" in body.content.decode()
    assert (
        "Give a Result and the Evidence Sampled"
        in post(client, f"/review-items/{first.id}/", result="Satisfactory").content.decode()
    )


def test_the_certificate_waits_for_every_point_every_finding_and_the_survey(
    sample: Sample, review: Review, reviews: SampleReviews
) -> None:
    """REQ-108, REQ-109. ML.A.903(b), (e)(1) to (3). Each reason is shown until it is met."""
    client = signed_in(sample.reviewer)
    with working_for(sample.ours.id, sample.reviewer.id):
        items = {item.reference: item for item in review.items.all()}
    for reference, item in items.items():
        if reference != "ML.A.903(c)(4)":
            response = post(
                client, f"/review-items/{item.id}/", result="Satisfactory", evidence=EVIDENCE
            )
            assert response.status_code == 302
    defect = items["ML.A.903(c)(4)"]
    post(
        client,
        f"/review-items/{defect.id}/",
        result="Finding",
        evidence=EVIDENCE,
        finding="[Finding at the Survey]",
    )
    body = page(client, f"/reviews/{review.id}/")
    assert "No Result Yet" not in body
    assert "<li>Finding Not Closed on ML.A.903(c)(4)</li>" in body
    assert "<li>ML.A.903(b): Name Who Assisted at the Survey</li>" in body
    assert "<li>Airframe Flight Hours at the Review Not Entered</li>" in body
    assert (
        "<li>ML.A.903(e)(3): State Whether a Discrepancy Was Found in the "
        "Maintenance Programme</li>" in body
    )
    # An attempt to issue now is refused on the server, whatever the page offers (TH-009).
    refused = post(client, f"/reviews/{review.id}/issue/")
    assert refused.status_code == 200
    assert "Finding Not Closed on ML.A.903(c)(4)" in refused.content.decode()

    post(client, f"/review-items/{defect.id}/close/", closure="[Rectified and Released]")
    post(
        client,
        f"/reviews/{review.id}/details/",
        assisted_by="",
        airframe_hours="11206.8",
        programme_discrepancy="Found, Not Yet Addressed",
    )
    body = page(client, f"/reviews/{review.id}/")
    assert "[Finding at the Survey], Closed 18 November 2026, [Rectified and Released]" in body
    assert "<li>ML.A.903(b): Name Who Assisted at the Survey</li>" in body
    assert (
        "<li>ML.A.903(e)(3): The Maintenance Programme Discrepancy Is Not Yet Addressed</li>"
        in body
    )
    post(
        client,
        f"/reviews/{review.id}/details/",
        assisted_by="[Part-66 Name]",
        airframe_hours="11206.8",
        programme_discrepancy="Found and Addressed",
    )
    body = page(client, f"/reviews/{review.id}/")
    assert "<li>" not in body.split("Issue the Certificate for G-EJKL")[1]
    assert "Issue Airworthiness Review Certificate for G-EJKL" in body
    with working_for(sample.ours.id, sample.reviewer.id):
        assert (
            Certificate.objects.filter(aircraft=review.aircraft, issued_by__isnull=False).count()
            == 0
        )


def test_staff_qualified_under_part_66_need_no_assistance(
    sample: Sample, review: Review, reviews: SampleReviews
) -> None:
    """REQ-108. ML.A.903(b) asks for assistance only when the person is not so qualified."""
    complete(sample, review, assisted_by="")
    with working_for(sample.ours.id, sample.administrator.id):
        assert services.outstanding(review, TODAY) == [
            "ML.A.903(b): Name Who Assisted at the Survey"
        ]
        ReviewStaff.objects.filter(pk=reviews.reviewer.pk).update(part_66_qualified=True)
        review.refresh_from_db()
        assert services.outstanding(review, TODAY) == []


def test_the_form_15c_entries_are_needed_before_issue(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110. Appendix IV to Part-ML: manufacturer, designation, serial number, hours."""
    with working_for(sample.ours.id, sample.reviewer.id):
        review = services.start_review(fleet["G-EJKL"], staff=reviews.reviewer)
    complete(sample, review)
    with working_for(sample.ours.id, sample.reviewer.id):
        assert services.outstanding(review, TODAY) == [
            "CAA Form 15c: Not Entered for the Aircraft, Aircraft Manufacturer, "
            "Manufacturer\N{RIGHT SINGLE QUOTATION MARK}s Designation, Aircraft Serial Number"
        ]
    planner = signed_in(sample.planner)
    response = post(
        planner,
        f"/aircraft/{fleet['G-EJKL'].id}/details/",
        serial_number="[Aircraft Serial Number]",
        manufacturer="[Aircraft Manufacturer]",
        designation="[Manufacturer Designation]",
    )
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reviewer.id):
        review.refresh_from_db()
        assert services.outstanding(review, TODAY) == []


# Issue


def test_g_ejkl_certificate_is_issued_from_the_completed_review(
    sample: Sample, review: Review, reviews: SampleReviews
) -> None:
    """REQ-102, REQ-109, REQ-110, REQ-111, REQ-112. The working is at the top of this file."""
    complete(sample, review)
    client = signed_in(sample.reviewer)
    response = post(client, f"/reviews/{review.id}/issue/")
    assert response.status_code == 302
    with working_for(sample.ours.id, sample.reviewer.id):
        review.refresh_from_db()
        certificate = review.certificate
        assert certificate is not None
        assert response["Location"] == f"/certificates/{certificate.id}/"
        assert (certificate.serial_number, certificate.reference) == (
            2,
            "UK.CAO.[Number]-ARC-0002",
        )
        assert (certificate.issued_on, certificate.valid_to) == (TODAY, date(2027, 12, 6))
        assert certificate.issued_by == reviews.reviewer
        assert certificate.airframe_hours == D("11206.8")
        # The issue is in the history, as the person who issued it.
        event = Event.of(review).order_by("-sequence").first()
        assert event is not None
        assert event.actor_id == sample.reviewer.id

    body = page(signed_in(sample.reader), f"/certificates/{certificate.id}/")
    for entry in (
        "<dt>Certificate Reference</dt><dd>UK.CAO.[Number]-ARC-0002</dd>",
        "<dt>Issued By</dt><dd>[Your Organisation], [Organisation Address], UK.CAO.[Number]</dd>",
        "<dt>Aircraft Manufacturer</dt><dd>[Aircraft Manufacturer]</dd>",
        "<dt>Manufacturer&#8217;s Designation</dt><dd>[Manufacturer Designation]</dd>",
        "<dt>Aircraft Registration</dt><dd>G-EJKL</dd>",
        "<dt>Aircraft Serial Number</dt><dd>[Aircraft Serial Number]</dd>",
        "<dt>Date of Issue</dt><dd>18 November 2026</dd>",
        "<dt>Date of Expiry</dt><dd>6 December 2027</dd>",
        "<dt>Airframe Flight Hours at the Time of Review</dt><dd>11,206.8</dd>",
        "<dt>Airworthiness Review Staff</dt><dd>[Review Name]</dd>",
        "<dt>Authorisation Number</dt><dd>[Authorisation Reference 2]</dd>",
        "The Review and Its Evidence",
    ):
        assert entry in body, entry
    schedule = page(signed_in(sample.reader), "/reviews/")
    start = schedule.index(">G-EJKL</a>")
    row = schedule[start : schedule.index("</tr>", start)]
    assert "<td>6 December 2027</td>" in row
    assert "To Be Sent by 28 November 2026" in row
    # The review keeps its evidence beside the certificate (REQ-112).
    kept = page(signed_in(sample.reader), f"/reviews/{review.id}/")
    assert kept.count(f"<td>{EVIDENCE}</td>") == 16
    assert ">UK.CAO.[Number]-ARC-0002</a>" in kept
    assert "<button" not in kept.split("<main")[1]


def test_a_review_is_issued_once(sample: Sample, review: Review) -> None:
    """REQ-110. A second attempt finds the certificate already there."""
    complete(sample, review)
    with working_for(sample.ours.id, sample.reviewer.id):
        services.issue_from_review(review)
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.issue_from_review(review)
        assert (
            Certificate.objects.filter(aircraft=review.aircraft, issued_by__isnull=False).count()
            == 1
        )


def test_a_review_is_never_altered_once_its_certificate_is_issued(
    sample: Sample, review: Review
) -> None:
    """REQ-110, REQ-112, hazard H-003. Refused by the service, the page and the database."""
    complete(sample, review)
    with working_for(sample.ours.id, sample.reviewer.id):
        services.issue_from_review(review)
        review.refresh_from_db()
        item = review.items.all()[0]
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.record_item(item, result=Result.FINDING, evidence=EVIDENCE, finding="[Late]")
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.record_details(
                review, assisted_by="", airframe_hours=None, programme_discrepancy=""
            )
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            ReviewItem.objects.filter(pk=item.pk).update(evidence="[Changed]")
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            Review.objects.filter(pk=review.pk).update(assisted_by="[Changed]")
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            ReviewItem.objects.create(
                organisation_id=review.organisation_id,
                review=review,
                position=17,
                reference="[Reference]",
                part=RECORDS,
                label="[Label]",
            )
    client = signed_in(sample.reviewer)
    body = post(client, f"/review-items/{item.id}/", result="Finding", evidence="x", finding="y")
    assert "A Review Is Never Altered Once Its Certificate Is Issued" in body.content.decode()
    # The owner of the database is refused as well.
    with as_owner(), connection.cursor() as cursor:
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            cursor.execute("UPDATE reviews_reviewitem SET evidence = 'x' WHERE id = %s", [item.pk])
        with pytest.raises(DatabaseError, match="never altered"), transaction.atomic():
            cursor.execute(
                "UPDATE reviews_review SET certificate_id = NULL WHERE id = %s", [review.pk]
            )


def test_a_point_changed_while_the_certificate_is_issued_waits_and_is_refused(
    sample: Sample, review: Review
) -> None:
    """REQ-107, REQ-110, hazard H-003; review of 20 November 2026, finding 5.

    A second request, a double submit or another tab, could record a
    finding on a point while the first was issuing the certificate, and
    both were committed. The race needs two connections, which the tests
    cannot hold over records that are never deleted, so three things are
    shown here instead, and the race itself was run again by hand
    (assurance/independent-verification/code-review-2026-11-20.md):

    - the service reads the review again rather than trusting the copy it
      was given, which is what a request that started before the issue holds;
    - it reads it under a lock held to the end of the request, which the
      issue also takes, so one waits for the other;
    - the database reads the review under a lock too, by its id alone.
    """
    complete(sample, review)
    with working_for(sample.ours.id, sample.reviewer.id):
        stale_item = review.items.select_related("review").all()[0]
        stale_review = Review.objects.get(pk=review.pk)
        fresh_item = ReviewItem.objects.get(pk=stale_item.pk)

        with CaptureQueriesContext(connection) as queries:
            services.record_item(fresh_item, result=Result.SATISFACTORY, evidence=EVIDENCE)
            services.record_details(
                stale_review,
                assisted_by="[Part-66 Name]",
                airframe_hours=D("11206.8"),
                programme_discrepancy=ProgrammeDiscrepancy.NONE_FOUND,
            )
        locks = [
            query["sql"]
            for query in queries.captured_queries
            if 'FROM "reviews_review"' in query["sql"] and "FOR UPDATE" in query["sql"]
        ]
        assert len(locks) == 2

        services.issue_from_review(review)
        assert stale_item.review.certificate_id is None  # the copy held before the issue
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.record_item(
                stale_item, result=Result.FINDING, evidence=EVIDENCE, finding="[Late]"
            )
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.close_finding(stale_item, closure="[Closure]")
        with pytest.raises(services.RefusedError, match="Never Altered"):
            services.record_details(
                stale_review, assisted_by="", airframe_hours=None, programme_discrepancy=""
            )

    with as_owner(), connection.cursor() as cursor:
        cursor.execute("SELECT pg_get_functiondef('reviews_reviewitem_fixed'::regproc)")
        row = cursor.fetchone()
    assert row is not None
    definition = " ".join(str(row[0]).split())
    assert "WHERE id = NEW.review_id FOR SHARE;" in definition


def test_only_the_person_carrying_out_the_review_records_and_issues_it(
    sample: Sample, review: Review
) -> None:
    """REQ-109. ML.A.903(e)(1). Another member of review staff is refused, and it is logged."""
    complete(sample, review)
    lucy = signed_in(sample.lucy)
    with working_for(sample.ours.id, sample.lucy.id):
        item = review.items.all()[0]
    for path in (
        f"/review-items/{item.id}/",
        f"/review-items/{item.id}/close/",
        f"/reviews/{review.id}/details/",
        f"/reviews/{review.id}/issue/",
    ):
        assert post(lucy, path, result="Finding", evidence="x", finding="y").status_code == 403
    with working_for(sample.ours.id, sample.lucy.id):
        assert AccessEntry.objects.filter(user=sample.lucy, kind="Action Refused").count() == 4
        review.refresh_from_db()
        assert review.certificate is None
        assert review.items.filter(result=Result.SATISFACTORY).count() == 16


def test_review_staff_whose_recency_has_lapsed_cannot_issue_and_the_lapse_is_recorded(
    sample: Sample, review: Review, reviews: SampleReviews, day: Day
) -> None:
    """REQ-109, REQ-114, threat TH-009, test T-SEC-012. 3 December 2026 is a day too late."""
    complete(sample, review)
    day.today = date(2026, 12, 3)
    client = signed_in(sample.reviewer)
    response = post(client, f"/reviews/{review.id}/issue/")
    assert response.status_code == 200
    assert (
        "CAO.A.045(c): The Review Staff Member Does Not Have Recent Experience"
        in response.content.decode()
    )
    with working_for(sample.ours.id, sample.reviewer.id):
        review.refresh_from_db()
        assert review.certificate is None
        reviews.reviewer.refresh_from_db()
        assert reviews.reviewer.lapsed_on == date(2026, 12, 3)


# Void


def test_a_void_certificate_stays_and_the_next_review_takes_the_next_serial(
    sample: Sample, review: Review, reviews: SampleReviews, ejkl: Aircraft
) -> None:
    """REQ-110. The void certificate no longer counts; its serial is not used again."""
    complete(sample, review)
    with working_for(sample.ours.id, sample.reviewer.id):
        first = services.issue_from_review(review)
    client = signed_in(sample.reviewer)
    assert post(client, f"/certificates/{first.id}/void/").status_code == 302
    with working_for(sample.ours.id, sample.reviewer.id):
        first.refresh_from_db()
        assert not first.voided  # a void needs its reason
    post(client, f"/certificates/{first.id}/void/", reason="[Issued in Error]")
    body = page(client, f"/certificates/{first.id}/")
    assert '<p role="alert">Void, [Issued in Error]</p>' in body
    assert "Void Certificate</button>" not in body
    with working_for(sample.ours.id, sample.reviewer.id):
        # The certificate from the records counts again: valid to 6 December 2026.
        assert services.current_valid_to(ejkl) == date(2026, 12, 6)
        again = services.start_review(ejkl, staff=reviews.reviewer)
    complete(sample, again)
    with working_for(sample.ours.id, sample.reviewer.id):
        second = services.issue_from_review(again)
        assert (second.serial_number, second.valid_to) == (3, date(2027, 12, 6))


def test_a_certificate_issued_elsewhere_shows_who_issued_it(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-110. It keeps its own reference, and cannot be voided here."""
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = Certificate.objects.get(aircraft=fleet["G-EJKL"])
    body = page(signed_in(sample.reader), f"/certificates/{certificate.id}/")
    assert "<dt>Issued By</dt><dd>[Recorded From the Aircraft Records]</dd>" in body
    assert "<dt>Certificate Reference</dt><dd>[Certificate Reference G-EJKL]</dd>" in body
    assert "Void" not in body


def test_an_extension_carries_the_airframe_hours_on_its_date(
    sample: Sample, fleet: dict[str, Aircraft], reviews: SampleReviews
) -> None:
    """REQ-104, REQ-110. Appendix IV to Part-ML: hours at the date of issue of the extension."""
    with working_for(sample.ours.id, sample.lucy.id):
        certificate = Certificate.objects.get(aircraft=fleet["G-EJKL"])
        extension = services.extend_certificate(
            certificate,
            extended_by=sample.lucy,
            managed_for_12_months=True,
            maintained_by_approved_organisations=True,
            no_evidence_not_airworthy=True,
        )
        assert extension.airframe_hours == D("11206.8")
    body = page(signed_in(sample.reader), f"/certificates/{certificate.id}/")
    assert "<h2>First Extension</h2>" in body
    assert "<dt>Airframe Flight Hours at the Date of Issue</dt><dd>11,206.8</dd>" in body
    assert "<dt>Date of Expiry</dt><dd>6 December 2027</dd>" in body
    assert "<dt>Extended By</dt><dd>Lucy Grant</dd>" in body


# Other organisations (T-SEC-010), roles (T-SEC-011) and forged writes (T-SEC-005)


def addresses(review: Review, certificate: Certificate):  # type: ignore[no-untyped-def]
    aircraft = review.aircraft
    item = ReviewItem.objects.filter(review=review).order_by("position")[0]
    return [
        ("GET", f"/reviews/{review.id}/", Action.VIEW_RECORDS),
        ("GET", f"/certificates/{certificate.id}/", Action.VIEW_RECORDS),
        ("POST", f"/aircraft/{aircraft.id}/review/start/", Action.CARRY_OUT_AIRWORTHINESS_REVIEW),
        ("POST", f"/review-items/{item.id}/", Action.CARRY_OUT_AIRWORTHINESS_REVIEW),
        ("POST", f"/review-items/{item.id}/close/", Action.CARRY_OUT_AIRWORTHINESS_REVIEW),
        ("POST", f"/reviews/{review.id}/details/", Action.CARRY_OUT_AIRWORTHINESS_REVIEW),
        ("POST", f"/reviews/{review.id}/issue/", Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE),
        (
            "POST",
            f"/certificates/{certificate.id}/void/",
            Action.ISSUE_AIRWORTHINESS_REVIEW_CERTIFICATE,
        ),
        ("POST", f"/aircraft/{aircraft.id}/details/", Action.ADD_OR_CHANGE_AIRCRAFT),
    ]


def pages(sample: Sample, review: Review, reviews: SampleReviews):  # type: ignore[no-untyped-def]
    with working_for(sample.ours.id, sample.reviewer.id):
        return addresses(review, reviews.cdef)


def test_another_organisations_reviews_are_not_found(
    sample: Sample, review: Review, reviews: SampleReviews
) -> None:
    """REQ-003, REQ-004, threat TH-020, planned test T-SEC-010. Read and write."""
    complete(sample, review)
    stranger = signed_in(sample.stranger)
    for method, path, action in pages(sample, review, reviews):
        expected = 404 if permitted(sample.stranger.roles, action) else 403
        assert call(stranger, method, path).status_code == expected, f"{method} {path}"
    with as_owner():
        assert Review.objects.count() == 1
        assert Review.objects.get().certificate is None
        assert not Certificate.objects.get(pk=reviews.cdef.pk).voided
        assert Aircraft.objects.get(pk=review.aircraft_id).manufacturer == "[Aircraft Manufacturer]"


@pytest.mark.parametrize(
    "role", ["Administrator", "Airworthiness Review Staff", "Planning and Records", "Read Only"]
)
def test_every_review_checklist_page_follows_the_role_matrix(
    sample: Sample, review: Review, reviews: SampleReviews, role: str
) -> None:
    """REQ-006, threat TH-008, planned test T-SEC-011. Refusals are logged."""
    user = sample.by_role()[role]
    client = signed_in(user)
    refusals = 0
    for method, path, action in pages(sample, review, reviews):
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
        "Administrator": 7,
        "Airworthiness Review Staff": 1,
        "Planning and Records": 6,
        "Read Only": 7,
    }
    assert refusals == expected[role]


def test_review_checklist_pages_need_sign_in_and_refuse_forged_writes(
    sample: Sample, review: Review, reviews: SampleReviews
) -> None:
    """REQ-008, threats TH-003 and TH-008, planned test T-SEC-005."""
    listed = pages(sample, review, reviews)
    anonymous = Client()
    for method, path, _ in listed:
        response = call(anonymous, method, path)
        assert response.status_code == 302, path
        assert response["Location"].startswith("/sign-in/")
    forged = Client(enforce_csrf_checks=True)
    forged.force_login(
        sample.reviewer, backend="airworthiness_plus.accounts.backends.OrganisationBackend"
    )
    for method, path, _ in listed:
        if method == "POST":
            assert post(forged, path).status_code == 403, path
