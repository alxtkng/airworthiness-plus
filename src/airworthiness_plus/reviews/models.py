"""Airworthiness review staff, review certificates and their extensions.

Sources, read in the UK text on 18 November 2026: ML.A.901, ML.A.903,
CAO.A.045 and AMC1 CAO.A.045, CAO.A.090(a)(3), CAO.A.095. The certificate
is CAA Form 15c (Appendix IV to Part-ML).
"""

from django.db import models
from django.db.models import F, Q

from airworthiness_plus.accounts.models import User
from airworthiness_plus.aircraft.models import Aircraft
from airworthiness_plus.history.models import Record
from airworthiness_plus.organisations.models import Organisation


class ReviewStaff(Record):
    """One person authorised as airworthiness review staff (CAO.A.045).

    The record is kept after the person leaves: nothing is removed
    (REQ-115, CAO.A.045(e): at least 2 years).
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="review_staff")
    authorisation_reference = models.CharField("Authorisation Reference", max_length=60)
    # CAO.A.045(b): formally accepted after a review under supervision.
    accepted_on = models.DateField("Accepted")
    # ML.A.903(b): staff not qualified under Part-66 are assisted at the survey.
    part_66_qualified = models.BooleanField("Qualified Under Part-66", default=False)
    # AMC1 CAO.A.045(c)(1): months of continuing airworthiness management in
    # the current 2-year period, as the organisation records them.
    months_involved = models.PositiveSmallIntegerField(
        "Months of Continuing Airworthiness Management in the 2-Year Period", default=0
    )
    months_recorded_on = models.DateField("Months Recorded")
    last_review_before_records = models.DateField(
        "Last Review Before These Records", null=True, blank=True
    )
    # Once recency is lost it stays lost until a restoration is recorded,
    # whatever is entered afterwards. Found by the independent recompute.
    lapsed_on = models.DateField("Lapsed", null=True, blank=True)
    # AMC1 CAO.A.045(d): validity restored by a review under supervision.
    restored_on = models.DateField("Restored", null=True, blank=True)
    restored_under = models.CharField(
        "Restored Under the Supervision Of", max_length=200, blank=True
    )
    left_on = models.DateField("Left", null=True, blank=True)

    class Meta:
        ordering = ["accepted_on"]
        constraints = [
            models.CheckConstraint(
                condition=Q(restored_on__isnull=True, restored_under="")
                | (Q(restored_on__isnull=False) & ~Q(restored_under="")),
                name="reviewstaff_restoration_names_its_supervision",
            ),
        ]

    def __str__(self) -> str:
        return self.authorisation_reference


class Certificate(Record):
    """An airworthiness review certificate, CAA Form 15c (REQ-100 to REQ-103, REQ-110).

    One issued by this organisation takes its serial from the database,
    which allocates it in the transaction that issues the certificate:
    unique, in order, and never used again, because a certificate is never
    deleted and a voided one keeps its serial. One issued elsewhere is
    recorded with the reference it carries. The reference, dates, aircraft
    and serial of a certificate never change once recorded.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="+")
    serial_number = models.PositiveIntegerField(null=True, blank=True)
    reference = models.CharField("Certificate Reference", max_length=80, blank=True)
    issued_on = models.DateField("Date of Issue")
    valid_to = models.DateField("Date of Expiry")
    issued_by = models.ForeignKey(
        ReviewStaff, on_delete=models.PROTECT, null=True, blank=True, related_name="certificates"
    )
    issued_elsewhere_by = models.CharField("Issued By", max_length=200, blank=True)
    airframe_hours = models.DecimalField(
        "Airframe Flight Hours at the Review", max_digits=8, decimal_places=1, null=True, blank=True
    )
    copy_sent_on = models.DateField(
        "Copy Sent to the Civil Aviation Authority", null=True, blank=True
    )
    voided = models.BooleanField(default=False)
    void_reason = models.CharField("Reason", max_length=200, blank=True)

    class Meta:
        ordering = ["issued_on", "serial_number"]
        constraints = [
            models.UniqueConstraint(
                fields=["organisation", "serial_number"], name="certificate_serial_used_once"
            ),
            models.UniqueConstraint(
                fields=["organisation", "reference"], name="certificate_reference_used_once"
            ),
            models.CheckConstraint(
                condition=Q(valid_to__gt=F("issued_on")), name="certificate_expires_after_issue"
            ),
            # Issued here by review staff, or elsewhere by a named issuer.
            models.CheckConstraint(
                condition=Q(issued_by__isnull=False, issued_elsewhere_by="")
                | (
                    Q(issued_by__isnull=True, serial_number__isnull=True)
                    & ~Q(issued_elsewhere_by="")
                ),
                name="certificate_issued_here_or_elsewhere",
            ),
            models.CheckConstraint(
                condition=Q(voided=False, void_reason="") | (Q(voided=True) & ~Q(void_reason="")),
                name="certificate_void_has_a_reason",
            ),
        ]

    def __str__(self) -> str:
        return self.reference


class Extension(Record):
    """One extension of a certificate, ML.A.901(c) (REQ-104 to REQ-106).

    The three conditions are each confirmed before the extension is made.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    certificate = models.ForeignKey(
        Certificate, on_delete=models.PROTECT, related_name="extensions"
    )
    extended_on = models.DateField("Extended")
    valid_to = models.DateField("Date of Expiry")
    extended_by = models.ForeignKey(User, on_delete=models.PROTECT, related_name="+")
    # CAA Form 15c: airframe flight hours at the date of issue of the extension.
    airframe_hours = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)
    managed_for_12_months = models.BooleanField()
    maintained_by_approved_organisations = models.BooleanField()
    no_evidence_not_airworthy = models.BooleanField()
    copy_sent_on = models.DateField(
        "Copy Sent to the Civil Aviation Authority", null=True, blank=True
    )

    class Meta:
        ordering = ["extended_on"]
        constraints = [
            models.CheckConstraint(
                condition=Q(
                    managed_for_12_months=True,
                    maintained_by_approved_organisations=True,
                    no_evidence_not_airworthy=True,
                ),
                name="extension_every_condition_confirmed",
            ),
        ]


class Result(models.TextChoices):
    """What the review found on one point."""

    SATISFACTORY = "Satisfactory", "Satisfactory"
    FINDING = "Finding", "Finding"
    NOT_APPLICABLE = "Not Applicable", "Not Applicable"


class ProgrammeDiscrepancy(models.TextChoices):
    """ML.A.903(e)(3) and (h): whether the review found the programme deficient.

    Point (h) says the programme may be reviewed with the airworthiness
    review, not that it must be, so the review can say that it was not.
    """

    NOT_REVIEWED = "Not Reviewed With This Review", "Not Reviewed With This Review"
    NONE_FOUND = "None Found", "None Found"
    ADDRESSED = "Found and Addressed", "Found and Addressed"
    NOT_ADDRESSED = "Found, Not Yet Addressed", "Found, Not Yet Addressed"


class Review(Record):
    """One airworthiness review of an aircraft: records and physical survey (ML.A.903).

    Once its certificate is issued the review cannot be changed: the
    database refuses.
    """

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    aircraft = models.ForeignKey(Aircraft, on_delete=models.PROTECT, related_name="+")
    staff = models.ForeignKey(ReviewStaff, on_delete=models.PROTECT, related_name="reviews")
    started_on = models.DateField("Started")
    # ML.A.903(b): staff not qualified under Part-66 are assisted at the survey.
    assisted_by = models.CharField("Assisted at the Survey By", max_length=200, blank=True)
    airframe_hours = models.DecimalField(
        "Airframe Flight Hours at the Review", max_digits=8, decimal_places=1, null=True, blank=True
    )
    programme_discrepancy = models.CharField(
        "Maintenance Programme", max_length=40, choices=ProgrammeDiscrepancy.choices, blank=True
    )
    certificate = models.OneToOneField(
        Certificate, on_delete=models.PROTECT, null=True, blank=True, related_name="review"
    )

    class Meta:
        ordering = ["started_on"]


class ReviewItem(Record):
    """One point of a review, with its result, the evidence sampled and any finding (REQ-107)."""

    organisation = models.ForeignKey(Organisation, on_delete=models.PROTECT, related_name="+")
    review = models.ForeignKey(Review, on_delete=models.PROTECT, related_name="items")
    position = models.PositiveSmallIntegerField()
    reference = models.CharField(max_length=20)
    part = models.CharField(max_length=40)
    label = models.CharField(max_length=200)
    may_not_apply = models.BooleanField(default=False)
    result = models.CharField("Result", max_length=20, choices=Result.choices, blank=True)
    evidence = models.CharField("Evidence Sampled", max_length=300, blank=True)
    finding = models.CharField("Finding", max_length=300, blank=True)
    closure = models.CharField("How It Was Closed", max_length=300, blank=True)
    closed_on = models.DateField("Closed", null=True, blank=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["review", "position"], name="reviewitem_one_for_each_point"
            ),
            # A result comes with the evidence sampled.
            models.CheckConstraint(
                condition=Q(result="") | (Q(result__in=Result.values) & ~Q(evidence="")),
                name="reviewitem_result_has_its_evidence",
            ),
            models.CheckConstraint(
                condition=~Q(result=Result.NOT_APPLICABLE) | Q(may_not_apply=True),
                name="reviewitem_not_applicable_only_where_the_regulation_allows",
            ),
            models.CheckConstraint(
                condition=(Q(result=Result.FINDING) & ~Q(finding=""))
                | (~Q(result=Result.FINDING) & Q(finding="", closure="", closed_on__isnull=True)),
                name="reviewitem_finding_is_described",
            ),
            models.CheckConstraint(
                condition=Q(closure="", closed_on__isnull=True)
                | (~Q(closure="") & Q(closed_on__isnull=False)),
                name="reviewitem_closure_has_its_date",
            ),
        ]

    @property
    def open_finding(self) -> bool:
        """Return whether the point has a finding that is not yet closed."""
        return self.result == Result.FINDING and self.closed_on is None
