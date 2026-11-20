# Independent Verification: Dates, Records Deadlines and Airworthiness Review

Modules: `airworthiness_rules.dates`, `airworthiness_rules.records`, `airworthiness_rules.review`.

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the quoted rules (ML.A.305(a), ML.A.901(a), (c), (d), ML.A.903(d), (f)), the two project conventions (exact day counts in UK local dates; anniversaries) and the cases. It worked each answer by hand and was told to answer "not determined" where the rules did not settle a case. This mirrors an independent inspection.

## Result

Every case agrees with the golden tests in `tests/test_golden_review.py`.

| Case | Independent Answer | Golden Test | Agree |
|---|---|---|---|
| G-EJKL certificate valid to 6 December 2026, from 18 November 2026 | 18 days | 18 | Yes |
| G-CDEF reviewed 11 November 2026, previous expiry 2 December 2026 | 21 days early, pattern kept, valid to 2 December 2027 | Same | Yes |
| G-CDEF copy to the Civil Aviation Authority | 21 November 2026 | Same | Yes |
| G-ABCD tyre replaced 22 October 2026, release in records by | 21 November 2026 | Same | Yes |
| Review 2 September 2026 against expiry 2 December 2026 | 91 days, pattern not kept | Same | Yes |
| Review 3 September 2026 | 90 days, pattern kept | Same | Yes |
| Review 2 December 2026 | 0 days, pattern kept | Same | Yes |
| Review 3 December 2026 | After expiry, pattern not kept (inference) | Same | Yes |
| Review 2 September 2026, new validity | 2 September 2027 (inference) | Same | Yes |
| Extension 6 November 2026 against expiry 6 December 2026 | 30 days, permitted, valid to 6 December 2027 | Same | Yes |
| Extension 5 November 2026 | 31 days, not within the anticipation | Refused | Yes |
| Third consecutive extension | Not permitted | Refused | Yes |
| Expiry 29 February 2028, review 1 February 2028 | 28 February 2029 | Same | Yes |
| Day counts across month ends, a leap year, both clock changes, year end | 29, 30, 2, 2, 1 | Same | Yes |
| UK local date at 23:30 UTC on 30 June, 31 December, 24 October, 25 October 2026 | 1 July, 31 December, 25 October, 25 October | Same | Yes |

## Points the Verifier Found Not Settled by the Rules

These are readings the implementation makes that the quoted text does not state outright. Each needs a source or a decision before its requirement counts as verified.

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| Last day of a 1-year validity that does not keep the pattern: the anniversary or the day before | Anniversary | REQ-103 | To Be Checked against CAA Form 15c (Issue #38) |
| Whether the valid-to date is itself a valid day | Yes: a review or extension on that date keeps the pattern | REQ-100, REQ-102 | To Be Checked |
| Whether exactly 90 days (review) and exactly 30 days (extension) are inside the window | Inside | REQ-102, REQ-106 | To Be Checked |
| What the anticipation is measured between | Review or extension date to the current valid-to date | REQ-102, REQ-106 | To Be Checked |
| New date when the pattern is kept | Previous valid-to plus 1 year | REQ-102, REQ-104 | Matches SampleData.md (G-CDEF); To Be Checked |
| Extension more than 30 days early, or after expiry | Refused | REQ-106 | To Be Checked |
| Review after expiry | Pattern lost, 1 year from the review | REQ-102 | To Be Checked |
| Review date and issue date differ | Not modelled: one date is used | REQ-102 | Open design point for the review workflow |
| Release to service deadline counting | Completion day plus 30 | REQ-051 | Matches ML.A.305(a) wording "30 days after the day of the completion" |
| Copy deadline counting | Issue date plus 10. The rule says the copy is sent within 10 days | REQ-111 | Matches the brief's golden case; To Be Checked |
| What resets the count of consecutive extensions | A full review | REQ-104 | To Be Checked |
| After 29 February becomes 28 February, later years | Stay on 28 February unless re-derived | REQ-047 | Design decision to record |

Recency of review staff (REQ-113) is not in these modules yet: `SampleData.md` gives the lapse date (2 December 2026) but not the date of the person's last review, so the golden case cannot be worked by hand until that is added.

## Added 19 November 2026: The Days the Windows Open

`review_window_opens` and `extension_window_opens` were added so that a page can show the first day of the 90-day and 30-day windows (REQ-139). They were not recomputed by a separate person. They are held to the rules that were: two property tests show, for every pair of dates, that a review keeps the pattern exactly from the day shown to the day of expiry, and that an extension is accepted exactly from the day shown to the day of expiry (`tests/test_properties_dates.py`). One case is worked by hand: for a certificate ending 6 December 2026 the windows open on 7 September 2026 and 6 November 2026 (`tests/test_golden_review.py`).

## Added 20 November 2026: Dates Past the Calendar

`add_days`, `add_months` and `add_years` now raise `BeyondCalendarError` when the date asked for is after 31 December 9999 or before 1 January 1, and `add_months` reaches December 9999 without failing. Before, an interval of 2,147,483,647 days stopped the programme page with a server error, and one in months was shown with the wrong reason. Found while fixing finding 7 of the independent review of 20 November 2026; not in that review. No date inside the calendar changes. It was not recomputed by a separate person: a property test shows that any step of days, months or years from any date gives a date or this error and nothing else, and that a month step keeps the day or lands on the last day of the month (`tests/test_properties_dates.py`). The edges are worked by hand in `tests/test_input_limits.py`: 30 November 9999 plus 1 month is 30 December 9999; 31 January 9999 plus 11 months is 31 December 9999.
