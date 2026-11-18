# Independent Verification: Recency of Airworthiness Review Staff

Module: `airworthiness_rules.review` (`recency_by_review_lasts_to`, `review_staff_recent`, `recency_lapses`), and its use in `airworthiness_plus.reviews.services`.

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the quoted rules (CAO.A.045(c); AMC1 CAO.A.045(c) and (d)), the project conventions and seven cases. It read no files and ran no code, worked each answer by hand, and was told to answer "not determined by the rules given" instead of guessing. This mirrors an independent inspection.

The quoted rules were read in the UK text in the Civil Aviation Authority Regulatory Library on 18 November 2026.

## Result

Every case agrees with the golden tests in `tests/test_golden_recency.py`.

| Case | Independent Answer | Agree |
|---|---|---|
| Lucy Grant, last review 11 November 2026, no months of involvement | The review counts to 11 November 2027. Recent on 18 November 2026 and 11 November 2027; not on 12 November 2027 | Yes |
| Last review 2 December 2025, 4 months of involvement | Lapses after 2 December 2026. Recent on 18 November and 2 December 2026; not on 3 December 2026. A review on 1 December 2026 moves the lapse to 1 December 2027 | Yes |
| No review, with 5, 6 and 24 months | Not recent; recent; recent | Yes |
| Last review 1 January 2024, on 18 November 2026, with 5 and 6 months | Not recent; recent | Yes |
| Lapse date with 6 months of involvement, and with no review | None shown in either case | Yes |
| Last review 29 February 2028 | Counts to 28 February 2029 | Yes |
| A lapsed person reviews under supervision on 10 December 2026 | Not determined by the rules given: the conventions had no rule for a supervised review, and no state for lapsed or restored | See the first finding |

## Findings Acted On

| Finding | Action |
|---|---|
| There was no gate on restoration. Once a person had lapsed, the system would show them recent again as soon as their months reached 6 or a new review date was entered, with no review under supervision as AMC1 CAO.A.045(d) requires. A lapsed person could then have issued a certificate | Fixed in this change. A lapse is recorded the moment it is found, and before any change to the person's months or last review, and it stands until a restoration is recorded. Test `test_a_lapse_is_remembered_until_a_restoration_is_recorded` |
| Nothing checked who supervised a restoration | Fixed in this change. The supervisor is another member of the organisation's review staff who is currently valid on that day, never the person themselves, or the supervision is named, as for the Civil Aviation Authority. Test `test_a_lapsed_person_cannot_supervise_a_restoration` |
| A blank lapse date meant two opposite things: recent by months, or not recent at all | Fixed in this change. The page states what recency rests on, and the status says Lapsed, Restoration Needed |
| The months figure had no date | Fixed in this change. The figure carries the date it was recorded, and the page shows it |
| Recency tested when the screen is viewed, not when the certificate is issued | Already met: recency is tested for the day of issue, on the server, at the moment of issue (REQ-109, threat TH-009) |
| "Recent" is not "authorised" | Already met: issue needs a review staff record, an active user who has not left, no lapse awaiting restoration, and recent experience |
| A future-dated or mistyped review date | Already met for dates after today, which are refused |

## Readings the Implementation Makes

Each needs a source or a decision by Alex King before its requirement counts as verified.

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| "The last 12-month period": whether the day 12 months after a review still counts | It counts: a review on 11 November 2026 counts on 11 November 2027 and not on the 12th | REQ-113 | To Be Checked. The stricter reading ends a day earlier |
| The date of the other review staff member's last review | 2 December 2025, from the lapse date of 2 December 2026 in `SampleData.md` | REQ-113 | To be confirmed by Alex King |
| "At least 6 months in every 2-year period" | A figure the organisation records, with its date. The system does not work out the 2-year window | REQ-113 | Question for Alex King: how the organisation counts it, and when the figure goes stale |
| What date a review has | The date of issue of the certificate | REQ-102, REQ-113 | Open design point, already in `review-and-dates.md` |
| Whether the review under supervision must be on record as satisfactory | The restoration is recorded by the Administrator, with its date and supervision. Its outcome is not a separate entry | REQ-114 | Question for Alex King |

## Findings Carried Forward

| Finding | Where It Goes |
|---|---|
| When recency rests on 6 months of involvement, the date by which the last review would stop counting is not shown, so a later fall in the figure gives no warning | Interface: show the review date beside the basis (REQ-113, REQ-139) |
| Whether a review counts only for the same organisation and an appropriate aircraft scope | Question for Alex King |
| An organisation's exposition may be stricter than the AMC | Outside the slice |
| Acceptance by the Civil Aviation Authority of supervision by the organisation's own staff, and the approved procedure | The exposition; recorded as text with the restoration |
