# Independent Verification: Record Kept Until, and the Earlier Alert for Review Certificates

Module: `airworthiness_rules.personnel` (REQ-206) and `airworthiness_rules.programme`, `review_certificate_lead_days` and what uses it (REQ-213).

Date: 24 November 2026.

Method: duplicate inspection. A separate agent read REQ-206, REQ-213, REQ-055, REQ-046, REQ-047, the related lines of `Decisions.md`, `SampleData.md` and the UK text in the Civil Aviation Authority Regulatory Library. It worked every case below by hand and wrote them to this file before opening the implementation or its tests. Only then did it read the code and tests and run the functions. Nothing in the repository was changed; no database was used.

## Sources Read

Read on 24 November 2026 at regulatorylibrary.caa.co.uk/1321-2014, each on its own page.

| Point | What the Text Says | Confirmed |
|---|---|---|
| CAO.A.045(e) | The CAO keeps a record of all its airworthiness review staff and "shall retain that record for a period of at least 2 years after the date at which the person concerned no longer works for the CAO" | Yes, point letter shown |
| CAO.A.035(e) | "The CAO shall assess and record the qualification of all personnel." No period | Yes, point letter shown |
| CAO.A.040(d) | The CAO records the details of certifying staff and keeps a list in the exposition. No period | Yes. Not cited by REQ-206; read to check that Part-CAO gives no period for certifying staff |
| CAO.A.090 | Record-keeping: maintenance, continuing airworthiness, review certificate and permit records. Nothing on personnel records | Yes |
| CAMO.A.220, Personnel Records | "Personnel records shall be kept as long as the person works for the organisation, and shall be retained until 3 years after the person has left the organisation." The records are of personnel involved in continuing airworthiness management, compliance monitoring and safety management, and of all review staff and staff issuing recommendations and permits | Yes. The point letters are not shown on the page, as `Decisions.md` says |
| 145.A.55, Personnel Records (SI 2025 No. 1150) | "Personnel records must be kept for as long as a person works for the organisation and must be retained for 3 years after the person has left the organisation or for 3 years after an authorisation issued to that person has been withdrawn." The records are of personnel involved in maintenance, compliance monitoring and safety management, and of all review staff | Yes. Point letters not shown |

Not from the regulation, and so ours (D), as REQ-206 and REQ-213 already say: applying 3 years to every person of an organisation holding Part-CAMO or Part-145; taking the longer period; 29 February to 1 March; every number of REQ-055, REQ-212 and REQ-213.

Could not confirm: nothing was unreachable. No AMC or GM was found that gives a period for the other staff of a Part-CAO; AMC1 CAO.A.045 was not read in full.

## Worked by Hand, Before Reading the Code

### REQ-206: The Day a Record Is Kept Until

Rule as read: the day the person left plus N years, same day and month. N is 3 if the organisation holds Part-CAMO or Part-145; otherwise 2 if the person is airworthiness review staff of a Part-CAO; otherwise there is no day. 29 February goes to 1 March. Neither 2 nor 3 years after a 29 February can be a leap year (2100 is not one), so a 29 February leaver always lands on 1 March. 1 March is the right side: 28 February would be a day short of "at least 2 years after".

Sample people who have left:

| Person | Organisation | Left | Working | Kept Until |
|---|---|---|---|---|
| [Former Review Name], Airworthiness Review Staff | [Your Organisation], Part-CAO alone | 30 June 2025 | 2 years, CAO.A.045(e) | 30 June 2027. `SampleData.md` agrees |
| Nobody | [Second Organisation], Part-CAMO and Part-145 | | None of its 5 people has left | No case. If one left on 30 June 2025: 30 June 2028 |

Boundary cases of my own:

| No. | Approvals Held | Staff | Left | Working | Kept Until | Source Shown |
|---|---|---|---|---|---|---|
| 1 | Part-CAO | Review staff | 29 February 2024 | +2 years, no 29 February 2026 | 1 March 2026 | CAO.A.045(e) |
| 2 | Part-CAMO | Any | 29 February 2024 | +3 years, no 29 February 2027 | 1 March 2027 | CAMO.A.220 |
| 3 | Part-CAO and Part-145 | Review staff | 29 February 2028 | Longer of 2 and 3 | 1 March 2031 | 145.A.55 |
| 4 | Part-CAO | Review staff | 28 February 2024 | +2 years | 28 February 2026 | CAO.A.045(e) |
| 5 | Part-CAO | Review staff | 28 February 2026 | +2 years, lands in a leap year | 28 February 2028, not the 29th | CAO.A.045(e) |
| 6 | Part-CAMO | Any | 28 February 2025 | +3 years, lands in a leap year | 28 February 2028 | CAMO.A.220 |
| 7 | Part-CAO | Review staff | 31 December 2025 | +2 years | 31 December 2027 | CAO.A.045(e) |
| 8 | Part-CAMO | Any | 31 December 2025 | +3 years | 31 December 2028 | CAMO.A.220 |
| 9 | Part-CAO and Part-145 | Review staff | 30 June 2025 | Longer of 2 and 3 | 30 June 2028 | 145.A.55 |
| 10 | Part-CAO and Part-145 | Other staff | 30 June 2025 | 3 years, to everyone (ours) | 30 June 2028 | 145.A.55 |
| 11 | Part-CAMO alone | Review staff, and other staff | 30 June 2025 | 3 years | 30 June 2028 | CAMO.A.220 |
| 12 | Part-CAO alone | Other staff (certifying, planning, manager) | 30 June 2025 | No period given | No day; the page says no period is given | CAO.A.035(e) |
| 13 | Part-CAO and Part-CAMO | Other staff | 1 March 2024 | 3 years | 1 March 2027 | CAMO.A.220 |
| 14 | Part-CAMO and Part-145 | Any | 30 June 2025 | 3 years, both give it | 30 June 2028 | Both |
| 15 | Any | Any | Has not left | | No day | |

### REQ-213: The Earlier Alert

Rule as read. Days remaining is the exact count from today to the expiry day (REQ-046: 18 November to 6 December 2026 is 18). So the count does not add the day of expiry itself: on the day of expiry 0 days remain, and the day after, minus 1. The certificate is valid on its expiry day, so 0 is Due Soon and not Overdue (REQ-055: red only when past due). "Due Soon at 30 days" is read as inclusive: Due Soon when 0 <= remaining <= lead. The lead for a review certificate is the earlier alert when it is on, otherwise the calendar lead time. Nothing else takes the earlier lead.

Calendar lead time 30 (the default):

| Days Before Expiry | Off | Earlier Alert 60 |
|---|---|---|
| 61 | Not Due Soon | Not Due Soon |
| 60 | Not Due Soon | Due Soon |
| 31 | Not Due Soon | Due Soon |
| 30 | Due Soon | Due Soon |
| 0 (day of expiry) | Due Soon | Due Soon |
| Minus 1 | Overdue (expired) | Overdue (expired) |

Allowed values: more than the calendar lead time and at most 365. With the default 30: smallest 31, largest 365; 30 and 366 refused. At 31: 31 days Due Soon, 32 not. At 365: 365 days Due Soon, 366 not. With a calendar lead time of 0 the smallest is 1. With a calendar lead time of 365 no value is allowed, so the alert cannot be on.

Sample aircraft, today 18 November 2026:

| Aircraft | Valid To | Days by Hand | Off (30) | On, 60 | On, 365 |
|---|---|---|---|---|---|
| G-DGHI | 19 May 2027 | 12+31+31+28+31+30+19 = 182 | No | No | Due Soon |
| G-EJKL | 6 December 2026 | 12+6 = 18 | Due Soon | Due Soon | Due Soon |
| G-ABCD | 14 March 2027 | 12+31+31+28+14 = 116 | No | No | Due Soon |
| G-BXYZ | 2 August 2027 | 182+12+30+31+2 = 257 | No | No | Due Soon |
| G-FMNO | 27 April 2027 | 12+31+31+28+31+27 = 160 | No | No | Due Soon |
| G-CDEF | 2 December 2027 | 365+12+2 = 379 | No | No | No |
| G-HKLM | None | | No certificate | No certificate | No certificate |

First day Due Soon: G-EJKL on 6 November 2026 with the alert off, 7 October 2026 at 60. G-ABCD on 12 February 2027 off, 13 January 2027 at 60 (13 to 31 January 18, February 28, March 14: 60). The sample's "Airworthiness Review, 18 Days" for G-EJKL is unchanged by the alert.

Other limits with the alert at 60: a calendar task with 45 days remaining is not Due Soon; hours and cycles are untouched.

## Comparison

Read after the above was written: `src/airworthiness_rules/personnel.py`, `src/airworthiness_rules/programme.py`, `tests/test_golden_personnel.py`, `tests/test_settings.py`, and the callers in `people/services.py`, `programme/due.py`, `reviews/services.py`, `organisations/configuration.py`, `forms.py` and `models.py`. The functions were run with `uv run python`, importing only `airworthiness_rules`. No test was run and no database touched.

### REQ-206

`record_kept_until(left, approvals=..., review_staff=...)` was run on the sample leaver and cases 1 to 14, and on 29 February 2096 (to 1 March 2098 and 2099).

| Cases | By Hand | Code | Agree |
|---|---|---|---|
| Sample: [Former Review Name], 30 June 2025 | 30 June 2027, CAO.A.045(e) | 30 June 2027, 2 years, "CAO.A.045(e)" | Yes |
| 1 to 3, 29 February | 1 March 2026, 2027, 2031 | The same | Yes |
| 4 to 6, 28 February | 28 February 2026, 2028, 2028 | The same | Yes |
| 7 and 8, 31 December | 31 December 2027, 2028 | The same | Yes |
| 9 to 11, 13 and 14, Part-CAMO or Part-145 held | 3 years, review staff or not | The same; source "145.A.55, Personnel Records", "CAMO.A.220, Personnel Records" or both | Yes |
| 12, Part-CAO alone, other staff | No day | `None` | Yes |
| No approval held | Not worked by hand | `None` | No source gives a period; accepted |
| 15, has not left | No day | The rule is not called: `people/services.py` asks only for a person with a day of leaving | Yes |

The golden tests hold the same answers as mine where they overlap (30 June 2027; 30 June 2028 for each mix of approvals; 1 March 2026 and 1 March 2027; no day for other Part-CAO staff). The property tests cover the rest by rule. The tests have no written case for 31 December or for a 28 February that lands in a leap year; the property test covers both.

### REQ-213

`review_certificate_lead_days(calendar_days, earlier_alert_days)` with `limit_flag` over a calendar `Limit`, as `reviews.services.schedule_line` calls them.

| Days Before Expiry | Off: By Hand | Off: Code | 60: By Hand | 60: Code | Agree |
|---|---|---|---|---|---|
| 61 | No | No flag | No | No flag | Yes |
| 60 | No | No flag | Due Soon | Due Soon | Yes |
| 31 | No | No flag | Due Soon | Due Soon | Yes |
| 30 | Due Soon | Due Soon | Due Soon | Due Soon | Yes |
| 0 | Due Soon | Due | Due Soon | Due | The word differs: see Disagreements |
| Minus 1 | Overdue | Overdue | Overdue | Overdue | Yes |

At 31: 31 Due Soon, 32 not. At 365: 365 Due Soon, 366 not. Calendar lead 0 with the alert at 1: 1 Due Soon, 2 not. All as by hand. The sample aircraft give 182, 18, 116, 257, 160 and 379 days from `dates.days_between`, as by hand, and the same flags at off, 60 and 365. 7 October and 6 November 2026 are 60 and 30 days before 6 December; 13 January and 12 February 2027 are 60 and 30 before 14 March. A calendar limit that is not a review certificate, 45 days out, takes no flag from `thresholds_of`, which never reads the alert.

The golden test `test_a_review_certificate_can_be_given_an_earlier_alert` holds the same days for G-ABCD as mine (13 January 60, 12 January 61, 12 February 30, 11 February 31), and (0, Due), (minus 1, Overdue). The settings tests refuse 30 and 366 with a lead of 30, as by hand.

Days before expiry: the code counts as REQ-046 does. The day of expiry is 0, not 1; "from 60 days" means the day on which 60 remain is the first Due Soon day, inclusive.

## Disagreements

| Inputs | By Hand | Code | Which Is Right |
|---|---|---|---|
| Review certificate on its day of expiry (0 days), alert on or off | Due Soon | Due | The code. `Decisions.md` (Interface) lists Due as its own amber word, and REQ-056 has a limit due from the limit itself; the existing rule gives Due at 0 for every limit, and REQ-213 changes only where Due Soon starts. My reading of REQ-055 alone missed the word. No change to the code. Both are amber and neither is red |

No other calculation disagrees.

## Findings From Reading, Not Disagreements in the Calculation

| Finding | Where |
|---|---|
| "At most 365" is held only by the form (`MOST_DAYS`). `configuration.set_lead_times` and the database constraint `organisation_review_alert_is_the_earlier` check only that the alert is more than the calendar lead time, so another caller could store 366 or more. The same holds for the 365 of REQ-212's days. The rule itself (`max`) is safe with any value | REQ-212, REQ-213; `organisations/configuration.py`, `models.py` |
| With a calendar lead time of 365 no earlier alert is allowed (more than 365 and at most 365). The form then refuses every value; correct by the requirement, but the page gives no reason beyond the two messages | REQ-213 |
| Review staff is read from the person's staff group as it stands (`person.staff_group == StaffGroup.REVIEW`). A person of a Part-CAO who was review staff and was moved to another group before leaving is given no day, though CAO.A.045(e) covers "all its airworthiness review staff" | REQ-206; `people/services.py` |
| The approvals are those held on the day the page is read (`approvals.types_held`), not on the day the person left. An organisation that gives up Part-145 sees a former person's day fall from 3 years to 2, or to none | REQ-206; `people/services.py` |
| The golden test's docstring says "Four years later there is a 29 February again" beside a case that leaves on 28 February 2028; the case is right, the sentence explains nothing in it | `tests/test_golden_personnel.py` |

## Readings That Stay To Be Checked

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| 145.A.55: "or for 3 years after an authorisation issued to that person has been withdrawn" | Only the day of leaving is used. Authorisations are not recorded until Phase 2 | REQ-206 | To Be Checked: whether the "or" gives a second, later day for a person whose authorisation is withdrawn, and which governs |
| Whose records CAMO.A.220 and 145.A.55 cover | Every person of the organisation. The text names personnel in continuing airworthiness management or maintenance, compliance monitoring and safety management, and review staff | REQ-206 | Ours, and the longer way round. For Alex King to confirm |
| Whether the last day is itself a day the record must be held | The day shown is the same day N years on, "kept until" | REQ-206 | To Be Checked. The system deletes nothing, so no harm either way; the page's wording should not invite deletion on that day |
| 29 February to 1 March | 1 March | REQ-206 | Ours. Consistent with "at least"; differs on purpose from REQ-047, which goes to the last day of the shorter month |
| Approvals held now, or on the day of leaving; review staff now, or ever | Now, in both | REQ-206 | Question for Alex King (see findings) |
| A Part-CAO's other staff | No day shown | REQ-206 | Confirmed that CAO.A.035(e), CAO.A.040(d) and CAO.A.090 give no period. AMC and GM not read in full; an exposition may set its own |
| Point letters of the Personnel Records paragraphs of CAMO.A.220 and 145.A.55 | Cited by heading | REQ-206 | The Regulatory Library page shows none; to be read in the PDF or the statutory instrument |
| The word on the day of expiry | Due | REQ-055, REQ-213 | Settled by `Decisions.md`; REQ-055's wording does not mention Due |
| The earlier alert's numbers and that it moves the one Due Soon mark and is not a second alert | One mark, from the alert's days | REQ-213 | Ours (decision 4); for Alex King, since the board shows two alerts, at 60 and 30 days |

## What Was Done With These Findings

Added 27 November 2026. No calculation disagreed, so no rule was changed. Of the findings from reading: the most a lead time or the earlier alert may be is now held by the service and the database as well as the form, and the docstring of the 29 February case was corrected, in pull request 116; review staff read from the staff group as it stands, and approvals read as held today, were corrected in pull request 117, so that the day uses the approvals held on the day the person left and counts a person who was ever review staff. The page's wording where a calendar lead time of 365 days leaves no earlier alert allowed was not changed. The readings that stay to be checked stay as listed (`code-review-2026-11-24.md`).
