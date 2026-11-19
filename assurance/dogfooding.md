# Dogfooding: The Sample Organisation Compared by Hand

Step 9 of private beta. Date: 19 November 2026.

## What Was Done

1. The sample organisation of `design-system/SampleData.md` was loaded by the seed command, `python manage.py seed_sample_organisation`, which builds it through the same services as the pages (`src/airworthiness_plus/sample/build.py`).
2. Every output the pages show for it was written out with today set to 18 November 2026, the sample's own day.
3. Each output was compared by hand with `SampleData.md`: the figure was worked from the sample's inputs first, then set beside what the page showed.
4. Every difference is listed below and raised as an Issue.

The comparison is kept as a test, `tests/test_sample_seed.py`, so that it is made again on every change.

No real records were loaded. Whether they may be, and on what terms, is Alex King's decision (Issue 28).

## Fleet

Source: `SampleData.md`, Fleet. Seven rows, six columns each.

| Aircraft Registration | Status | Next Due | Review Certificate Valid To | Airframe Hours | Agrees |
|---|---|---|---|---|---|
| G-DGHI | Unserviceable, Stabilator Trim Cable | Rectify Defect | 19 May 2027 | 9,874.3 | Yes |
| G-EJKL | Serviceable | Airworthiness Review, 18 Days | 6 December 2026 | 11,206.8 | Yes |
| G-ABCD | Serviceable | 50-Hour Check, 12.4 Hours | 14 March 2027 | 6,412.6 | Yes |
| G-BXYZ | Serviceable | 100-Hour or Annual Check, 41.0 Hours | 2 August 2027 | 3,318.0 | Yes |
| G-FMNO | Serviceable | Annual Check, 78 Days | 27 April 2027 | 4,950.2 | Yes |
| G-CDEF | Serviceable | Engine Overhaul, 220.0 Hours | 2 December 2027 | 7,731.5 | See D-1 |
| G-HKLM | Transfer In | Records 14 of 18 Received | | | Yes, on the Transfers tab |

Type Rating and Owned By agree on every row, character for character.

## Due Items

Source: `SampleData.md`, Maintenance Programme Inputs. Worked by hand:

| Aircraft Registration | Working | By Hand | Shown | Agrees |
|---|---|---|---|---|
| G-ABCD | Last done at 6,375.0, every 50: 6,375.0 + 50 | Due 6,425.0 Hours | 6,425.0 Hours | Yes |
| G-ABCD | 6,425.0 − 6,412.6 | 12.4 Hours | 12.4 Hours | Yes |
| G-BXYZ | 3,259.0 + 100; less 3,318.0 | 3,359.0 Hours, 41.0 Hours | 3,359.0 Hours, 41.0 Hours | Yes |
| G-BXYZ | 30 July 2026 + 12 months; days from 18 November 2026: 12 + 31 + 31 + 28 + 31 + 30 + 31 + 30 + 30 | 30 July 2027, 254 Days | 30 July 2027, 254 Days | Yes |
| G-BXYZ | 41.0 hours at 0.5 a day is 82 days, against 254 | Hours First | Projected First on the hours limit | Yes |
| G-BXYZ | Tolerance: 3,359.0 + 10; 30 July 2027 + 1 month | 3,369.0 Hours; 30 August 2027, after the certificate's 2 August 2027 | 3,369.0 Hours; 30 August 2027, After the Review Certificate Ends 2 August 2027 | Yes |
| G-FMNO | 4,912.0 + 100; less 4,950.2 | 5,012.0 Hours, 61.8 Hours | 5,012.0 Hours, 61.8 Hours | Yes |
| G-FMNO | 4 February 2026 + 12 months; days: 12 + 31 + 31 + 4 | 4 February 2027, 78 Days | 4 February 2027, 78 Days | Yes |
| G-FMNO | 61.8 hours at 0.2 a day is 309 days, against 78 | Calendar First | Projected First on the calendar limit | Yes |
| G-FMNO | Tolerance: 5,012.0 + 10; 4 February 2027 + 1 month | 5,022.0 Hours; 4 March 2027 | 5,022.0 Hours; 4 March 2027 | Yes |
| G-CDEF | Engine at 1,780.0 since overhaul, overhaul at 2,000 | Due 2,000.0 Hours, 220.0 Hours | 2,000.0 Hours, 220.0 Hours | Yes |
| G-ABCD | Tyre replaced 22 October 2026; release in the records within 30 days | By 21 November 2026 | To Be Recorded by 21 November 2026, Due Soon | Yes |

## Review Dates

Source: `SampleData.md`, Fleet and the notes for the review pages. Days are counted from 18 November 2026: 12 days are left in November.

| Aircraft Registration | Valid To | Working | By Hand | Shown | Agrees |
|---|---|---|---|---|---|
| G-EJKL | 6 December 2026 | 12 + 6 | 18 Days, inside the 90 days | 18 Days, Due Soon, Inside the 90-Day Window | Yes |
| G-ABCD | 14 March 2027 | 12 + 31 + 31 + 28 + 14 | 116 Days | 116 Days | Yes |
| G-FMNO | 27 April 2027 | 12 + 31 + 31 + 28 + 31 + 27 | 160 Days | 160 Days | Yes |
| G-DGHI | 19 May 2027 | 12 + 31 + 31 + 28 + 31 + 30 + 19 | 182 Days | 182 Days | Yes |
| G-BXYZ | 2 August 2027 | 12 + 31 + 31 + 28 + 31 + 30 + 31 + 30 + 31 + 2 | 257 Days | 257 Days | Yes |
| G-CDEF | 2 December 2027 | 12 + 365 to 30 November 2027 + 2 | 379 Days | 379 Days | Yes |
| G-CDEF | Reviewed 11 November 2026, 21 days before 2 December 2026 | Inside the 90 days, so a year from the old expiry: 2 December 2027. Copy within 10 days: 21 November 2026 | 2 December 2027; To Be Sent by 21 November 2026, Due Soon | Yes |

| Review Staff | By Hand | Shown | Agrees |
|---|---|---|---|
| Lucy Grant | Last review 11 November 2026; recent until 11 November 2027 | Last Review 11 November 2026; After 11 November 2027; Current | Yes |
| Lucy Grant | 5 reviews in 12 months: G-DGHI, G-ABCD, G-BXYZ, G-FMNO, G-CDEF | The five certificates are held as hers: four from before these records, one issued here | Yes, since D-3 was fixed |
| The other review staff member | 4 months; last review 2 December 2025; lapses after 2 December 2026, 14 days away | 4; 2 December 2025; After 2 December 2026, Due Soon; Current | Yes |

## Directive Status, G-ABCD

| Directive | Working | By Hand | Shown | Agrees |
|---|---|---|---|---|
| [Directive Number 1] | First within 50 hours of 6,300.0: 6,350.0. Done at 6,350.0. Then every 100: 6,450.0. Less 6,412.6 | 6,450.0 Hours, 37.4 Hours | 6,450.0 Hours, 37.4 Hours | Yes |
| [Directive Number 2] | Not applicable, with its basis | Not Applicable | Not Applicable, Propeller Model Not Fitted, Logbook Checked | Yes |
| [Directive Number 3] | No decision yet | To be assessed | Applicability to Assess, To Assess | Yes |
| [Directive Number 4] | Once, within 3 months of 1 October 2026: 1 January 2027. Days: 12 + 31 + 1 | 1 January 2027, 44 Days | 1 January 2027, 44 Days | Yes |

Every directive shows as Applicability to Assess against every other aircraft, as the decision on directives requires.

## Maintenance Data

| Sample | Shown | Agrees |
|---|---|---|
| Grob G 115 manual amendment to check by 20 November 2026 | Last Checked 2 November 2026; Next Amendment Check By 20 November 2026; Due Soon | Yes |
| Piper PA-38 Series manual not held, needed for G-HKLM | Not Held, on the list and on G-HKLM's page | Yes |
| CAP 747 checked 16 November 2026 | Last Checked 16 November 2026 | Yes |
| G-BXYZ owner-provided instructions, confirmed current in writing 2 June 2026 | Provided by Syndicate of 6, Written Confirmation, 2 June 2026 | Yes |
| Manufacturers' manuals for every type in scope, checked 2 November 2026; Lycoming and Continental service information checked 16 November 2026 | Not loaded | See D-4 |

## Differences

| Number | Difference | Kind | Requirement | Outcome |
|---|---|---|---|---|
| D-1 | The sample writes 220 Hours for G-CDEF; the system writes 220.0 Hours | The sample and the writing rule differ. Hours are written to one decimal place (REQ-192) | REQ-192 | No change to the system. `SampleData.md` already notes it |
| D-2 | Work recorded for an earlier date, such as compliance with a directive on 20 July 2026, was shown as entered in the records After the 30 Days, because the day its release went into the records could only be today | Defect. A record brought in from a logbook would have been marked late when it was not | REQ-051 | Fixed in this change: the day the release was entered in the records can be given, on the page and in the seed; an import takes the day of the work. `test_sample_seed`, `test_programme` |
| D-3 | The sample says Lucy Grant has 5 reviews in 12 months. The system holds one of them as hers; the other four certificates are held as Recorded From the Aircraft Records, because a certificate from before these records began cannot be recorded as issued by the organisation's own review staff | Defect in what can be recorded. Recency is still right here, since it rests on the latest review | REQ-110, REQ-113 | Issue 71. Fixed 19 November 2026: such a certificate names the review staff member, keeps its reference and uses no serial. `test_reviews`, `test_imports`, `test_sample_seed` |
| D-4 | The sample names maintenance data that the seed does not load, because `SampleData.md` gives no revision or next-check date for it: the manuals for the other types, and Lycoming and Continental service information | Gap in the sample, not in the system | REQ-080 to REQ-083 | Decided 19 November 2026, after Alex King asked us to decide: the sample stays as it is. The seed loads only the four sets it can load without inventing a revision or a date. If he gives revisions and next-check dates for the rest, they are added |
| D-5 | The sample lists the Fleet with what needs attention first. The system listed it by Aircraft Registration | No requirement states the order | None | Decided 19 November 2026, after Alex King asked us to decide: the Fleet opens with what needs attention first (`Decisions.md`, Interface). The order now agrees with the sample except that G-FMNO, due in 78 days, comes before G-BXYZ, due in 82. `test_sample_seed: the_fleet_opens_with_what_needs_attention_first` |
| D-6 | Found while fixing D-3, not by comparing with the sample. When the organisation extended a certificate that was issued elsewhere, the copy of the extension owed to the Civil Aviation Authority was not shown on the schedule | Defect. A deadline of 10 days would have passed unflagged | REQ-111, ML.A.903(f) | Fixed 19 November 2026: the copy of an extension is tracked whoever issued the certificate. `test_reviews: g_ejkl_certificate_is_extended_within_30_days` |

## What This Does Not Show

- It is the sample, not real records. The sample's inputs were chosen to agree with its own Fleet table.
- The person comparing wrote the code. The independent recomputes in `assurance/independent-verification/` are the check on the arithmetic that did not.
- Work packages, defects, findings and the rest of `SampleData.md` are outside the slice and are not loaded.
