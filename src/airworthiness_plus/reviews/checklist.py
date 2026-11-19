"""What an airworthiness review checks, point by point (REQ-107, REQ-108).

ML.A.903(a)(1) to (11), the documented review of records, and
ML.A.903(c)(1) to (5), the physical survey, read in the UK text on
18 November 2026. The wording here is a short label for each point, not
the text of the regulation; the point number is the reference.
"""

from dataclasses import dataclass

RECORDS = "Review of Records"
SURVEY = "Physical Survey"


@dataclass(frozen=True)
class Point:
    """One thing the review verifies."""

    reference: str
    part: str
    label: str
    # The regulation says "if required": the point may not apply to the aircraft.
    may_not_apply: bool = False


CHECKLIST = (
    Point(
        "ML.A.903(a)(1)",
        RECORDS,
        "Airframe, Engine and Propeller Hours and Cycles Properly Recorded",
    ),
    Point(
        "ML.A.903(a)(2)",
        RECORDS,
        "Flight Manual Applicable to the Configuration and at the Latest Revision",
    ),
    Point(
        "ML.A.903(a)(3)", RECORDS, "All Maintenance Due Under the Maintenance Programme Carried Out"
    ),
    Point(
        "ML.A.903(a)(4)", RECORDS, "All Known Defects Corrected or Deferred in a Controlled Manner"
    ),
    Point(
        "ML.A.903(a)(5)",
        RECORDS,
        "All Applicable Airworthiness Directives Applied and Properly Registered",
    ),
    Point(
        "ML.A.903(a)(6)",
        RECORDS,
        "All Modifications and Repairs Registered and in Compliance with Part 21",
    ),
    Point(
        "ML.A.903(a)(7)",
        RECORDS,
        "Service-Life-Limited Components Identified, Registered and Within Their Approved Life",
    ),
    Point("ML.A.903(a)(8)", RECORDS, "All Maintenance Certified in Accordance with Part-ML"),
    Point(
        "ML.A.903(a)(9)",
        RECORDS,
        "Mass and Balance Statement Reflects the Configuration and Is Valid, If Required",
        may_not_apply=True,
    ),
    Point(
        "ML.A.903(a)(10)", RECORDS, "Aircraft Complies with the Latest Revision of Its Type Design"
    ),
    Point(
        "ML.A.903(a)(11)",
        RECORDS,
        "Noise Certificate Corresponds to the Current Configuration, If Required",
        may_not_apply=True,
    ),
    Point("ML.A.903(c)(1)", SURVEY, "All Required Markings and Placards Properly Installed"),
    Point("ML.A.903(c)(2)", SURVEY, "Aircraft Complies with Its Approved Flight Manual"),
    Point(
        "ML.A.903(c)(3)", SURVEY, "Aircraft Configuration Complies with the Approved Documentation"
    ),
    Point("ML.A.903(c)(4)", SURVEY, "No Evident Defect That Has Not Been Addressed Under ML.A.403"),
    Point(
        "ML.A.903(c)(5)",
        SURVEY,
        "No Inconsistency Between the Aircraft and the Review of Records",
    ),
)
