# Independent Verification: The Calculations of Phase 1

Module: `airworthiness_rules`, the calculations of Phase 1 of the canvas build: REQ-222, REQ-223, REQ-226, REQ-231, REQ-232, REQ-233, REQ-234, REQ-243, REQ-255, REQ-256, REQ-264, REQ-281 and REQ-291.

Date: 27 November 2026.

Method: duplicate inspection, as `prompts/canvas-build.md` Part 4 step 7 asks. A separate agent read the thirteen requirements and those they name, the Canvas Build, Interface and Regulation Facts parts of `Decisions.md`, `SampleData.md` and the UK text in the Civil Aviation Authority Regulatory Library. It worked every case below by hand and wrote them to this file before opening any implementation or test. Only then did it read the tests and the code and run the functions. Nothing in the repository was changed; no database was used and no test was run.

What was worked before and after the code was seen is said at the head of each part. Everything under Worked by Hand was written before; everything from Comparison with the Code onward was written after.

## Sources Read

Read on 27 November 2026 at regulatorylibrary.caa.co.uk/1321-2014 (build of 12 October 2026), each on its own page. Every page asked for was reached.

| Point | What the Text Says | Confirmed |
|---|---|---|
| ML.A.403 | A defect that seriously endangers flight safety is rectified before further flight. Four kinds of person may defer: the pilot, non-required equipment; the pilot using the minimum equipment list, required equipment, otherwise only authorised certifying staff; the pilot, other defects, where the aircraft is operated under Part-NCO and the owner or contracted CAMO or CAO agrees; appropriately qualified certifying staff, other defects where those conditions are not met. A defect that does not seriously hazard flight safety "shall be rectified as soon as practicable from the date on which the defect was first identified and within the limits specified in the maintenance data" | Yes. Point letters are not shown on the page; the order is that of (a), (b)(1) to (4), (c), (d). No number of days is given |
| GM1 ML.A.403 | The pilot should consider consulting certifying staff; what "required" equipment means. No period | Yes |
| ML.A.305 | The certificate of release to service is entered in the records "as soon as possible but not later than 30 days after the day of the completion of the maintenance task". The records hold the current status of service-life-limited components, the current mass and balance report and the current list of deferred maintenance. For a component: its identification, what it has been fitted to with the installation and removal, and "the date together with the component's accumulated total flight time, flight cycles, landings and calendar time" | Yes. Point letters not shown; the first paragraph is (a) |
| ML.A.503 | A certified life limit, after which the component is retired; a service life limit, after which it undergoes maintenance. An installed one "shall not exceed the approved service life limit as specified in the AMP and ADs, except as provided for in point ML.A.504(c)". The life is in calendar time, flight hours, landings or cycles | Yes. Point letters not shown |
| ML.A.504 | A component is unserviceable on expiry of its service life limit, among other cases | Yes |
| GM1 ML.A.302(c)(4) | The intervals of mandatory continuing airworthiness information cannot be extended by a CAMO or CAO | Yes |
| Appendix I to Part-ML | "In case of any non-conformity with this contract, by either of the signatories, the contract will become null. In such a case ... the owner will inform the CAA within 2 weeks about the termination of the contract." The organisation informs the CAA whenever the contract has not been respected, and whenever it is denounced by either party; the owner informs the CAA whenever it is denounced. No period for either. The owner informs the organisation "no later than 30 days after completion of any Pilot-owner maintenance task" | Yes |

Not from the regulation, and so ours (D), as the requirements already say: the 30 days of a deferral and counting them from the decision; Due Soon, Due and Overdue; what counts as the same defect, the 12 months and the 3, 2 and 1; how a component's hours are counted; marking a manufacturer's recommendation as a life limit is marked; the on-condition review interval; Due in 6 Months; 2 weeks counted as 14 days; that a change of the day of a weighing was weighed with the aircraft; In the Weight Schedule; the reweigh threshold; the Fleet's 30 days; the forecast date.

Not read: ML.A.302 and ML.A.201 (not needed for a figure below); the AMC to ML.A.305 and to ML.A.403.

## Worked by Hand, Before Reading the Code

Today is 18 November 2026 unless said. Days are exact counts (REQ-046): 18 November to 30 November is 12. A month lands on the same day or the last day of a shorter month (REQ-047). Lead times are the defaults: 30 days, 10.0 hours, 10 cycles (REQ-212). A limit with 0 remaining is Due, not Overdue (`Decisions.md`, Readings Kept as Built).

### REQ-222: The Limit of a Deferred Defect

Rule as read: the day of the decision plus the organisation's default for the point of ML.A.403(b), in days; or the limit in the maintenance data when that is the earlier. Under the minimum equipment list, the limit the list gives and no default. Never before the decision, never more than 365 days after it.

| Defect | Decided | Working | Limit |
|---|---|---|---|
| G-ABCD Left Landing Light | 3 November 2026 | 27 days to 30 November, 3 more | 3 December 2026 |
| G-BXYZ Cabin Entry Step | 28 October 2026 | 3 days to 31 October, 27 more | 27 November 2026 |
| G-EJKL Right Headset Socket | 12 November 2026 | 18 to 30 November, 12 more | 12 December 2026 |
| G-ABCD Landing Light (closed) | 10 February 2026 | 18 to 28 February, 12 more | 12 March 2026 |
| G-DGHI Landing Light (closed) | 16 June 2026 | 14 to 30 June, 16 more | 16 July 2026 |
| G-DGHI Trim Cable Wear (closed) | 9 December 2025 | 22 to 31 December, 8 more | 8 January 2026 |

All six agree with `SampleData.md`.

Boundary cases of my own:

| No. | Decided | Default | Maintenance Data or List | Limit |
|---|---|---|---|---|
| 1 | 3 November 2026 | 30 | Maintenance data 20 November 2026 | 20 November 2026, the earlier |
| 2 | 3 November 2026 | 30 | Maintenance data 3 December 2026 | 3 December 2026 |
| 3 | 3 November 2026 | 30 | Maintenance data 10 December 2026 | 3 December 2026, the default is the earlier |
| 4 | 3 November 2026 | 30 | Maintenance data 3 November 2026 | 3 November 2026: on the day is not before it |
| 5 | 3 November 2026 | 30 | Maintenance data 2 November 2026 | Refused: before the decision |
| 6 | 3 November 2026 | 1 | | 4 November 2026 |
| 7 | 3 November 2026 | 365 | | 3 November 2027 |
| 8 | 1 March 2027 | 365 | | 29 February 2028: 2028 is a leap year, so 365 days stop a day short of the anniversary |
| 9 | 30 January 2028 | 30 | | 29 February 2028 |
| 10 | 30 January 2027 | 30 | | 1 March 2027 |
| 11 | 29 February 2028 | 30 | | 30 March 2028 |
| 12 | 3 November 2026 | Not used | List gives 13 November 2026 | 13 November 2026 |
| 13 | 3 November 2026 | Not used | List gives 3 November 2027 (365 days) | 3 November 2027 |
| 14 | 3 November 2026 | Not used | List gives 4 November 2027 (366 days) | Refused |
| 15 | 3 November 2026 | Not used | List gives 2 November 2026 | Refused |
| 16 | 3 November 2026 | 30, then the setting is changed to 10 | | Stays 3 December 2026 |

### REQ-223: Days Remaining and the Mark

Rule as read: remaining is the exact days from today to the limit. Due Soon when remaining is more than 0 and no more than the calendar lead time; Due at 0; Overdue below 0. Not Deferrable: Grounded, Unserviceable.

| Defect | Limit | Days by Hand | Mark |
|---|---|---|---|
| G-DGHI Stabilator Trim Cable | Grounded | | Unserviceable; first |
| G-BXYZ Cabin Entry Step | 27 November 2026 | 9 | Due Soon |
| G-ABCD Left Landing Light | 3 December 2026 | 12 + 3 = 15 | Due Soon |
| G-EJKL Right Headset Socket | 12 December 2026 | 12 + 12 = 24 | Due Soon |

Order: G-DGHI, G-BXYZ, G-ABCD, G-EJKL.

Edges, G-BXYZ's limit of 27 November 2026, lead time 30: 28 October (30 days, the day it was deferred) Due Soon; 26 November (1) Due Soon; 27 November (0) Due; 28 November (minus 1) Overdue. A limit 31 days away, no mark.

Other lead times, on 18 November: at 15, G-ABCD (15) is Due Soon; at 14 it is not. At 10, only G-BXYZ (9). At 0: nothing is Due Soon; a limit 1 day away has no mark, 0 is Due, minus 1 is Overdue.

### REQ-226: Repeat Defects

Rule as read: the window is from the day after the same day a year before, to today, both included: 19 November 2025 to 18 November 2026. A defect counts by the day it was found, open or closed, for its type rating and chapter. 3 or more Repeat, 2 Watching, 1 No Action. Most first.

| Type Rating | Chapter | Defects Counted | Count | Says |
|---|---|---|---|---|
| Piper PA-28 Series (Lycoming) | 33 | G-ABCD 10 February 2026; G-DGHI 16 June 2026; G-ABCD 3 November 2026 | 3 | Repeat |
| Piper PA-28 Series (Lycoming) | 27 | G-DGHI 9 December 2025; G-DGHI 14 November 2026 | 2 | Watching |
| Piper PA-28 Series (Lycoming) | 32 | G-ABCD 22 October 2026 | 1 | No Action |
| Cessna/Reims-Cessna 172/F172 Series (Lycoming) | 53 | G-BXYZ 28 October 2026 | 1 | No Action |
| Cessna/Reims-Cessna 152/F152 Series (Lycoming) | 23 | G-EJKL 12 November 2026 | 1 | No Action |
| Robin DR 400 series (Lycoming) | 61 | G-CDEF 2 November 2026 | 1 | No Action |

Six lines, nine defects. `SampleData.md` agrees.

Edges:

| No. | Today | Window Starts | Result |
|---|---|---|---|
| 1 | 18 November 2026 | 19 November 2025 | A defect found 18 November 2025 is out; 19 November 2025 in; 18 November 2026 in |
| 2 | 8 December 2026 | 9 December 2025 | Chapter 27 still 2 |
| 3 | 9 December 2026 | 10 December 2025 | Chapter 27 falls to 1, No Action |
| 4 | 9 February 2027 | 10 February 2026 | Chapter 33 still 3 |
| 5 | 10 February 2027 | 11 February 2026 | Chapter 33 falls to 2, Watching |
| 6 | 29 February 2028 | 1 March 2027 (no 29 February 2027: the last day of the shorter month, 28 February, and the day after) | 28 February 2027 out, 1 March 2027 in |
| 7 | 28 February 2029 | 29 February 2028 | 28 February 2028 out, 29 February 2028 in |
| 8 | 1 March 2028 | 2 March 2027 | 1 March 2027 out |
| 9 | Any | | 4 in a chapter is Repeat; the same chapter on another type rating is its own line; the second organisation's Piper PA-28 is never counted with the first's |

Edge 6 is my reading of "the day after the same day a year before" where that day does not exist. The requirement does not say; 2 March 2027 would be the other reading.

### REQ-231: Hours and Cycles Since New or Overhaul

Rule as read: the hours the component had when fitted, and what the airframe has flown since: to today while fitted, to the removal after it. Cycles alike.

| Component | Hours When Fitted | Airframe Then | Airframe Now or at Removal | Working | Hours |
|---|---|---|---|---|---|
| G-CDEF Engine | 0.0 | 5,951.5 | 7,731.5 | 0.0 + 1,780.0 | 1,780.0 |
| G-ABCD Vacuum Pump | 0.0 | 6,230.6 | 6,412.6 | 0.0 + 182.0 | 182.0 |
| G-DGHI Engine | 0.0 | 7,734.3 | 9,874.3 | 0.0 + 2,140.0 | 2,140.0 |
| G-ABCD Emergency Locator Transmitter Battery | 0.0 | 5,890.0 | 6,412.6 | | 522.6 |
| G-BXYZ Fire Extinguisher | 0.0 | 2,950.0 | 3,318.0 | | 368.0 |
| Loan Propeller on G-CDEF | 0.0 | 7,715.0 | 7,731.5 | | 16.5 |
| G-CDEF's Own Propeller, removed | 16.5 | 6,319.5 | 7,715.0 at removal | 16.5 + 1,395.5 | 1,412.0, and no more whatever G-CDEF flies after |
| G-HKLM Propeller and Engine | Not given | 2,150.0 | None entered | | Cannot be worked out |

Edges: on the day of fitting, airframe unchanged, the hours are those when fitted (16.5). Tenths are exact: 0.1 when fitted, 0.2 flown since, is 0.3. Cycles, made up: 100 when fitted at 2,000 airframe cycles, airframe now 2,350, is 450.

### REQ-232: What Remains of a Life

Rule as read: hours remaining is the limit less the hours since new or overhaul; cycles alike; a calendar life in months runs from the day new or last overhauled; a date on the component is due on that date. No tolerance. Due Soon when more than 0 and within the lead time, Due at 0, Overdue below.

| Component | Limit | Working | Remains | Mark |
|---|---|---|---|---|
| G-CDEF Engine | 2,000 hours | 2,000.0 less 1,780.0 | 220.0 hours; due at 7,951.5 airframe hours | None |
| G-ABCD Vacuum Pump | 500 hours | 500.0 less 182.0 | 318.0 hours; due at 6,730.6 | None |
| G-ABCD Battery | 28 February 2027 | 12 + 31 + 31 + 28 | 102 days | None |
| G-BXYZ Fire Extinguisher | 31 March 2027 | 102 + 31 | 133 days | None |
| G-CDEF's Own Propeller | 2,000 hours or 72 months from 2 November 2020 | 72 months on is 2 November 2026; 2,000.0 less 1,412.0 | Calendar limit 2 November 2026, reached on the day it was removed; 588.0 hours | Off-wing; by today the calendar limit is 16 days past |
| Loan Propeller | None recorded | | Nothing | None |
| G-HKLM Propeller | 2,000 hours or 72 months, no overhaul day | | Calendar: cannot be calculated, shown first. Hours: no airframe hours entered | Cannot Be Calculated |

Edges:

| No. | Case | Result |
|---|---|---|
| 1 | G-CDEF engine at 7,941.4 airframe hours | 10.1 remain, no mark |
| 2 | At 7,941.5 | 10.0, Due Soon |
| 3 | At 7,951.4 | 0.1, Due Soon |
| 4 | At 7,951.5 | 0.0, Due |
| 5 | At 7,951.6 | Minus 0.1, Overdue. No tolerance |
| 6 | Battery, on 28 January 2027 | 31 days, no mark |
| 7 | On 29 January 2027 | 30 days, Due Soon |
| 8 | On 28 February 2027 | 0, Due |
| 9 | On 1 March 2027 | Minus 1, Overdue |
| 10 | Fire extinguisher | Due Soon from 1 March 2027 (30 days); Due 31 March; Overdue 1 April 2027 |
| 11 | 72 months from 29 February 2020 | 28 February 2026 |
| 12 | 48 months from 29 February 2020 | 29 February 2024 |
| 13 | 6 months from 31 August 2020 | 28 February 2021 |
| 14 | 1 month from 31 January 2024 | 29 February 2024 |
| 15 | Cycles: limit 1,000, lead 10 | 989 used: 11, no mark. 990: 10, Due Soon. 1,000: Due. 1,001: Overdue |
| 16 | Two limits | The worse governs: 588.0 hours and a calendar limit past is Overdue |

### REQ-233: On Condition

Rule as read: next review at the airframe hours of the last review plus the interval.

G-DGHI engine: 9,800.0 + 100 is 9,900.0. 9,900.0 less 9,874.3 is 25.7 hours. No mark at a lead time of 10.0. `SampleData.md` agrees.

| No. | Case | Result |
|---|---|---|
| 1 | Airframe 9,889.9 | 10.1 remain, no mark |
| 2 | 9,890.0 | 10.0, Due Soon |
| 3 | 9,900.0 | 0.0, Due |
| 4 | 9,900.1 | Minus 0.1, Overdue |
| 5 | Review recorded at 9,874.3 on 18 November 2026 | Next at 9,974.3 |
| 6 | Review recorded late, at 9,905.0 | Next at 10,005.0: from the review, not from 9,900.0 |
| 7 | Review at 9,799.9, or dated 19 October 2026 | Refused: before the last review |
| 8 | Review at 9,874.4 | Refused: above the hours the aircraft has |
| 9 | Review at 9,800.0 on 20 October 2026 sent again | Recorded once |
| 10 | Never reviewed | The requirement does not say; not worked |

### REQ-234: Due in 6 Months, the Counts and the Order

Rule as read: the same day 6 months on is 18 May 2027, 12 + 31 + 31 + 28 + 31 + 30 + 18 = 181 days. Counted: a fitted component with a limit reached; a calendar limit on or before 18 May 2027; hours or cycles projected (hours remaining over planning utilisation, rounded down) to on or before it; or one that cannot be projected or calculated.

| Component | Working | Days | In 6 Months |
|---|---|---|---|
| G-DGHI Engine, review | 25.7 over 0.8 is 32.125 | 32, 20 December 2026 | Yes |
| G-ABCD Battery | | 102 | Yes |
| G-BXYZ Fire Extinguisher | | 133 | Yes |
| G-HKLM Propeller | No overhaul day | Cannot be calculated | Yes |
| G-CDEF Engine | 220.0 over 0.6 is 366.67 | 366, 19 November 2027 | No |
| G-ABCD Vacuum Pump | 318.0 over 0.8 is 397.5 | 397, 20 December 2027 | No |
| Loan Propeller, G-HKLM Engine | No limit recorded | | No |
| G-CDEF's Own Propeller | Off-wing, not fitted | | No; counted as off-wing |

Counts: 9 tracked, 1 off-wing, 1 on condition, 4 due in 6 months. `SampleData.md` agrees.

Order by hand: G-HKLM propeller (cannot be calculated); G-CDEF's own propeller (due back 25 November 2026, 7 days); G-DGHI engine (32); battery (102); fire extinguisher (133); G-CDEF engine (366); vacuum pump (397); then the two with nothing due.

Edges: a calendar limit on 18 May 2027 is in, on 19 May 2027 out. At 0.8 hours a day, 145.5 hours remaining is 181.875, 181 days, in; 145.6 hours is exactly 182 days, out. An hours limit on an aircraft with no planning utilisation is in. From 31 August 2026 the day 6 months on is 28 February 2027; from 30 August 2027, 29 February 2028; from 29 February 2028, 29 August 2028.

### REQ-243: The Owner's Last Day to Tell the Civil Aviation Authority

Rule as read: the day the contract ended plus 14 days, for non-conformity only. The sample has no ended contract, so every case is my own.

| Ended | Last Day |
|---|---|
| 4 November 2026 | 18 November 2026 |
| 18 November 2026 | 2 December 2026 |
| 18 December 2026 | 1 January 2027 |
| 14 February 2027 | 28 February 2027 |
| 15 February 2027 | 1 March 2027 |
| 15 February 2028 | 29 February 2028 |
| 16 February 2028 | 1 March 2028 |
| 29 February 2028 | 14 March 2028 |
| Any, denounced or other | No day shown |

The organisation's day of telling: on or after the day ended, not after today; for non-conformity or denounced only.

### REQ-255: Net Mass Change

Rule as read: the sum, with signs, of changes embodied strictly after the day of the last weighing. In progress: not counted. No weighing: nothing counted.

| Aircraft | Last Weighed | Changes | Counted | Net |
|---|---|---|---|---|
| G-BXYZ | 14 June 2019 | Navigator, 12 October 2026, +1.2 | Yes | +1.2 |
| G-DGHI | 9 March 2017 | Wingtip repair, 18 July 2025, 0.0 | Yes | 0.0 |
| G-ABCD | 20 May 2022 | Transponder, 10 May 2022, +0.4 | No, before the weighing | 0.0 |
| G-CDEF | 3 September 2021 | Propeller overhaul, in progress | No | 0.0 |
| G-EJKL | 22 July 2020 | None | | 0.0 |
| G-FMNO | 5 April 2018 | Landing light, 14 April 2026, minus 0.3 | Yes | Minus 0.3 |
| G-HKLM | None recorded | Transponder 2021 and radio 2018, 0.0 each | Nothing counted | No Weighing Recorded |

Edges: embodied on the day of the weighing, not counted; the day after, counted; the day before, not. +1.2 and minus 0.3 is +0.9. +1.2 and minus 1.2 is 0.0. +0.1 and +0.2 is +0.3 exactly.

### REQ-256: Where an Aircraft Stands

Rule as read: Reweigh when the size of the net change is more than the threshold; else Weight Schedule Update while a counted change with a mass effect other than 0.0 has no issue of the schedule dated on or after the day it was embodied; else Current. No threshold: nothing is Reweigh.

Sample, no threshold set:

| Aircraft | Working | Stands |
|---|---|---|
| G-BXYZ | Navigator 12 October 2026; latest issue 14 June 2019, before it | Weight Schedule Update |
| G-DGHI | The repair has no mass effect | Current |
| G-ABCD, G-CDEF, G-EJKL | Nothing counted | Current |
| G-FMNO | Light 14 April 2026; Issue 5 dated 20 April 2026, after it | Current, net minus 0.3 |
| G-HKLM | Transfer In, not of the Fleet | Not listed |

Edges:

| No. | Case | Stands |
|---|---|---|
| 1 | G-BXYZ, threshold 1.2 | Weight Schedule Update: +1.2 is not over 1.2 |
| 2 | G-BXYZ, threshold 1.1 | Reweigh |
| 3 | G-FMNO, threshold 0.3 | Current |
| 4 | G-FMNO, threshold 0.2 | Reweigh: the size counts, whichever way; Reweigh though the change is in the schedule |
| 5 | An issue dated the day the change was embodied | In the schedule: Current |
| 6 | An issue dated the day before | Weight Schedule Update |
| 7 | +1.2 and minus 1.2, neither in an issue, any threshold | Net 0.0; Weight Schedule Update, not Reweigh |

### REQ-264: Release to Service in the Records

Rule as read: the last day is the day the maintenance was completed plus 30 days (ML.A.305(a)); entered on that day is in time, the day after is late. Not yet in the records: Due Soon from the day it starts (REQ-055), Due on the last day, Overdue after.

| Work | Completed | Working | Last Day | State on 18 November 2026 |
|---|---|---|---|---|
| G-ABCD Right Main Tyre | 22 October 2026 | 9 to 31 October, 21 more | 21 November 2026 | Not in the records, 3 days, Due Soon |
| G-CDEF 100-Hour Check | 4 November 2026 | 26 to 30 November, 4 more | 4 December 2026 | In the records 5 November 2026, in time |
| G-CDEF Spinner | 4 November 2026 | | 4 December 2026 | In the records 5 November 2026, in time |

Counts: 2 issued in the last 30 days (4 November is 14 days ago); 1 not yet in the records; 0 incomplete maintenance; 0 pilot-owner notices overdue (told 23 October, 1 day after). `SampleData.md` agrees.

Edges: the tyre on 21 November 2026, 0 days, Due; on 22 November, Overdue, and an entry that day is late. Completed 2 December 2026, last day 1 January 2027. Completed 30 January 2027, 1 March 2027; 30 January 2028, 29 February 2028; 31 January 2028, 1 March 2028. Pilot-owner notice: told on the 30th day, not overdue; on the 31st, overdue; not told, overdue from the 31st day (the tyre: from 22 November 2026). The last 30 days: I read 19 October 2026 (30 days ago) as in and 18 October as out; the requirement does not say which.

### REQ-281: The Fleet's Due in 30 Days

Rule as read: an Unserviceable aircraft; one whose next due is 30 days away or fewer, hours placed by projected days; one with something that cannot be calculated. The 30 is the board's, whatever the lead time.

| Aircraft | Next Due | Days | In |
|---|---|---|---|
| G-DGHI | Unserviceable | | Yes |
| G-BXYZ | Cabin entry step limit | 9 | Yes |
| G-ABCD | Defect limit 15; 50-hour check 12.4 over 0.8 is 15.5, 15 | 15 | Yes |
| G-EJKL | Review certificate | 18 | Yes |
| G-FMNO | Annual check | 78 | No |
| G-CDEF | Engine overhaul, 220.0 over 0.6 | 366 | No |
| G-HKLM | Transfer In | | Not of the Fleet |

All 6; Due in 30 Days 4; Unserviceable 1. `SampleData.md` agrees.

Edges: G-FMNO on 4 January 2027 (31 days to 4 February) out; on 5 January 2027 (30) in. At 0.8 hours a day, 24.7 hours is 30.875, 30 days, in; 24.8 hours is 31, out. A lead time of 10 days changes nothing. Something overdue is in.

### REQ-291: Forecast Date

Rule as read: today plus the whole days: the exact days to a calendar limit; for hours or cycles, what remains over the planning utilisation, rounded down. Reached or passed: today. No planning utilisation: no date.

| Aircraft | Line | Working | Days | Forecast Date |
|---|---|---|---|---|
| G-ABCD | 50-Hour Check | 12.4 over 0.8 is 15.5 | 15 | 3 December 2026 |
| G-ABCD | Landing light limit | | 15 | 3 December 2026 |
| G-ABCD | Battery | | 102 | 28 February 2027 |
| G-ABCD | Review certificate | 12 + 31 + 31 + 28 + 14 | 116 | 14 March 2027 |
| G-ABCD | Vacuum pump | 318.0 over 0.8 is 397.5 | 397 | 20 December 2027 |
| G-BXYZ | Check, hours | 41.0 over 0.5 | 82 | 8 February 2027 |
| G-BXYZ | Check, calendar | | 254 | 30 July 2027 |
| G-BXYZ | Step limit | | 9 | 27 November 2026 |
| G-FMNO | Annual check, calendar | | 78 | 4 February 2027 |
| G-FMNO | Annual check, hours | 61.8 over 0.2 | 309 | 23 September 2027 |
| G-CDEF | Engine overhaul | 220.0 over 0.6 is 366.67 | 366 | 19 November 2027 |
| G-DGHI | Engine review | 25.7 over 0.8 is 32.125 | 32 | 20 December 2026 |
| G-DGHI | Annual review of the programme | | 106 | 4 March 2027 |
| G-EJKL | Review certificate | | 18 | 6 December 2026 |
| G-EJKL | Headset socket limit | | 24 | 12 December 2026 |

Edges:

| No. | Case | Forecast |
|---|---|---|
| 1 | 0 days or 0.0 hours remaining | Today |
| 2 | Minus 5 days, or minus 3.0 hours | Today, never a day past |
| 3 | 0.7 hours at 0.8 a day (0.875) | 0 days, today |
| 4 | 8.0 hours at 0.8 a day | 10 days, 28 November 2026 |
| 5 | 61.8 hours at 0.2 a day | 309 exactly. Binary arithmetic gives 308.99999999999994, which rounds down to 308: the rule must count in tenths |
| 6 | 2.4 hours at 0.8; 0.3 at 0.1 | 3 days each, 21 November 2026; the same trap |
| 7 | No planning utilisation | No date; the line says so |
| 8 | Today 28 February 2028, 1 day | 29 February 2028 |
| 9 | Today 29 February 2028, 365 days | 28 February 2029 |
| 10 | Next 120 Days | To 18 March 2027 (12 + 31 + 31 + 28 + 18), that day included |

## Comparison with the Code

Everything from here on was written after the code was seen.

Read after the above was written (the file was saved at 22:49 on 27 November 2026, before the first test or module was opened): `requirements/traceability.csv` for the thirteen rows; `src/airworthiness_rules/defects.py`, `components.py`, `contracts.py`, `mass.py`, `forecast.py`, `records.py`, `dates.py`, `intervals.py` and the flags of `programme.py`; `tests/test_golden_defects.py`, `test_golden_components.py`, `test_golden_forecast.py` in full, and the tests the traceability rows name in `test_defects.py`, `test_components.py`, `test_contracts.py`, `test_modifications.py`, `test_releases.py`, `test_sample_seed.py` and `test_aircraft_views.py`; and, for what the pure rules do not hold, the parts of `defects/services.py`, `defects/models.py`, `components/services.py`, `modifications/services.py`, `releases/services.py`, `contracts/services.py`, `aircraft/views.py` and `programme/due.py` that call them. `tests/test_golden_mass.py` was not opened: its functions were run instead.

Run: every hand value above that a pure function gives, 205 comparisons, with `uv run python`, importing only `airworthiness_rules`. No test was run and no database touched. So the pages themselves (the order of a list, a count on a page, the Fleet filter) were compared by reading the service and the expected values of its test, not by running them.

What was not blind. `SampleData.md` and `Decisions.md` state the sample's answers (3 December 2026, 220.0 hours, 4 due in 6 months and so on), and they were read before the hand work, as the method requires. The hand work is therefore independent of the code and the tests, not of the record's own arithmetic; each sample figure was still worked from its inputs, and the boundary cases are mine alone.

| Requirement | Compared | By Hand | Code and Tests | Agree |
|---|---|---|---|---|
| REQ-222 | 6 sample limits; cases 1 to 13, 15 | As above | `deferral_limit` gives the same days; the golden test holds the same three limits and cases 1 to 7 | Yes |
| REQ-222 | Case 14, a list limit 366 days after the decision | Refused | `deferral_limit` returns 4 November 2027; `defects.services.record_defect` then refuses it, "A Limit Is at Most 365 Days After the Decision" | Yes at the service; see Findings |
| REQ-222 | Case 16, the setting changed afterwards | Limit stays | The limit is stored on the defect (`limit_on`); read, not run | Yes |
| REQ-223 | 3 sample defects, 9, 15 and 24 days; every edge; lead times 0, 10, 14, 15, 30 | As above | `deferral_flag` the same; the golden test holds 27 October None, 28 October Due Soon, 26 November Due Soon, 27 November Due, 28 November Overdue | Yes |
| REQ-226 | Window, the six lines, edges 1 to 8 | As above | `counted_from` 19 November 2025; 1 March 2027 from 29 February 2028; 29 February 2028 from 28 February 2029; 2 March 2027 from 1 March 2028. `test_defects` holds the same six lines and counts, and 2 to 1 between 8 and 9 December 2026 | Yes |
| REQ-231 | 7 components, the day of fitting, tenths, cycles | As above | `hours_since`, `cycles_since` the same; 522.6, 368.0 and 16.5 are on the page test | Yes |
| REQ-232 | Sample figures; edges 1 to 16 | As above | `life_limits`, `dated_limit`, `limit_flag`, `task_flag`, `add_months` the same. The propeller on 2 November 2026: 588.0 hours and 0 days; on 18 November, minus 16, Overdue. A calendar life with no day is refused by the rule and shown as a problem by the service | Yes |
| REQ-233 | 9,900.0 and 25.7; edges 1 to 9 | As above | `review_limit` the same. `record_review` refuses 9,799.9, an earlier day, 9,874.4 and a day after today; `test_components` holds each. The same review sent again is refused with This Review Is Already Recorded, so it is recorded once | Yes |
| REQ-234 | 181 days; each component in or out; both edges | As above | `due_within_months` and `projected_days` the same: 32, 102, 133, 366, 397; 18 May in, 19 May out; 145.5 hours in, 145.6 out; no utilisation in | Yes, rule by rule |
| REQ-234 | The page's counts and order for the full sample | 9 tracked, 4 due in 6 months, G-DGHI's engine at 32 days | The golden page test expects 7 tracked and 3 due in 6 months, G-DGHI's engine first with no day | The test is of a smaller sample: see Findings |
| REQ-243 | 8 days | As above | `owner_notice_deadline` the same. The test holds 4 November to 18 November 2026. The day is shown for non-conformity only (`contracts/services.py`) | Yes |
| REQ-255 | 7 aircraft; the day of the weighing; sums | As above | `counted_since`, `net_change` the same; the service counts only changes with a day embodied | Yes |
| REQ-256 | Sample; edges 1 to 7 | As above | `in_schedule`, `over_threshold` the same; the service tries Reweigh first, then a change with a mass effect not 0 and no issue on or after it. `test_modifications` holds edges 1 to 4 | Yes |
| REQ-264 | 21 November and 4 December 2026; the counts; every edge | As above | `release_record_deadline`, `deadline_flag`, `pilot_owner_told_late` the same. The page test holds 2, 1, 0, 0. The last 30 days are 0 to 30 days ago, both included, as I read it: G-CDEF's work is listed on 4 December and not on 5 December | Yes |
| REQ-281 | 4 of 6; 30 in, 31 out | As above | The seed test holds All 6, Due in 30 Days 4, Unserviceable 1, and G-EJKL in on 6 November, out on 5 November. 24.7 hours at 0.8 is 30 days, 24.8 is 31 | Yes for every case worked; see Findings |
| REQ-291 | 15 lines; edges 1 to 10 | As above | `forecast_date` the same. `projected_days` divides in `Decimal`: 61.8 over 0.2 is 309, and 2.4 over 0.8 and 0.3 over 0.1 are 3. `test_aircraft_views` holds G-ABCD's five dates as mine. 18 March 2027 is in the window, 19 March is not | Yes |

## Disagreements

No calculation disagrees. Five differences printed by my own script were its fault: it expected the word None where the rule's no-mark flag has an empty value.

| Inputs | By Hand | Code | Which Is Right |
|---|---|---|---|
| REQ-222, case 14: `deferral_limit(3 November 2026, None, 4 November 2027)` | Refused, more than 365 days | The pure rule returns 4 November 2027 | Neither is wrong: the service refuses it. The pure rule alone does not hold "never more than 365 days after" |

## Findings From Reading, Not Disagreements in the Calculation

| No. | Finding | Where |
|---|---|---|
| 1 | The golden page test of REQ-234 is not the sample of `SampleData.md`. Its fixture adds 7 components and gives G-DGHI no planning utilisation, and it expects 7 Tracked, 3 Due in 6 Months, with G-DGHI's engine first and no day. `SampleData.md` says 9 tracked and 4 due in 6 months, with G-DGHI's engine at 32 days at 0.8 hours a day and G-HKLM's propeller counted. No test was found that holds 9, 4 or the 32 days. Each part agrees with the rule when run alone, so I expect the page to be right; it is not tested, and I could not run it | `tests/test_components.py`, heading and `PAGE`; `SampleData.md`, Components |
| 2 | Due in 30 Days leaves out an aircraft whose tasks cannot be ranked. From reading `_next_due` and `due.next_due`, not run: a Serviceable aircraft with no planning utilisation, two tasks (a 50-hour check with 0.5 hours remaining, so Due Soon, and an annual check 200 days away), no open defect and a review certificate 200 days away. `next_due` returns no first task; the only candidate is the certificate at 200 days; the rank is (1, minus 1, 200) and `soon` is false. Nobody can place the check outside the 30 days, which is the reason `Decisions.md` gives for counting what cannot be calculated, and the reason REQ-234 counts a limit that cannot be projected. With one task and not two, the same aircraft is in: `days` is minus 1. REQ-281 names "cannot be calculated", not "cannot be placed", so this may be as intended; the two rules differ | `aircraft/views.py`, `_next_due` and `FleetRow.soon`; `programme/due.py`, `next_due` |
| 3 | The Fleet's next due holds the tasks of the programme, deferred defects and the review certificate. It does not hold a component's limit or the annual review of the programme, which the Maintenance Forecast (REQ-290) does. A battery date 5 days away does not put its aircraft among Due in 30 Days. REQ-281 says "next due" and does not say of what | `aircraft/views.py`, `_next_due` |
| 4 | "Never more than 365 days after its decision" is held by the service alone. `deferral_limit` checks the default, not the limit in the maintenance data or the list; the database constraint holds that a limit is not before its decision and that a default is from 1 to 365, not that the limit is within 365 days | REQ-222; `airworthiness_rules/defects.py`; `defects/models.py` |
| 5 | The words of ML.A.403(c) as recorded leave out a phrase. The text read today: rectified "as soon as practicable from the date on which the defect was first identified and within the limits specified in the maintenance data". `Decisions.md`, Regulation Facts, and the heading of `defects.py` give it without "from the date on which the defect was first identified". The default is counted from the decision (ours, and so recorded). A defect found on 1 November 2026 and deferred on 10 November has a limit of 10 December; counted from the day it was first identified it would be 1 December. In the sample every decision is on the day found | REQ-222; `Decisions.md` |
| 6 | A review of a component that is off-wing is not checked against any airframe hours: the check "not above the hours the aircraft has" needs a current fitting | REQ-233; `components/services.py`, `record_review` |
| 7 | A comment in the release test says the tyre "was completed 31 days ago: no longer among those issued in 30 days" beside a count that stays 2. The tyre has no certificate and was never one of the 2; the count is right, the comment explains nothing in it | `tests/test_releases.py`, `test_what_is_listed_and_counted_as_days_pass` |
| 8 | Repeat defects are grouped by the type rating the aircraft has today, not the one it had when the defect was found | REQ-226; `defects/services.py`, `repeat_lines` |

## Could Not Confirm, and Readings That Stay To Be Checked

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| The pages for the full sample: the order and counts of Components, the Fleet filter, the forecast of every aircraft but G-ABCD | Compared by reading the service and the expected values of its test | REQ-234, REQ-281, REQ-290 | Not run: they need a database. G-ABCD's forecast is tested; the other aircraft's forecast dates above have no test that I found |
| Where the default limit is counted from | The day of the decision | REQ-222 | Ours (D). To Be Checked against "from the date on which the defect was first identified" (finding 5); for Alex King |
| The 12 months that end on 29 February | Start on 1 March of the year before | REQ-226 | Ours. The code and my reading agree; the requirement does not say |
| "Within 2 weeks" | 14 days after the day the contract ended, that day being the last | REQ-243 | Ours (D), as recorded. Whether the day of ending is itself day 1 is not settled by Appendix I |
| "Not later than 30 days after the day of the completion" | The day completed plus 30, that day being the last | REQ-264 | Agrees with the words of ML.A.305(a) as read today |
| The last 30 days of the Release to Service page | 0 to 30 days ago, both included | REQ-264 | Ours; the board gives no edge |
| A component on condition never reviewed | A component on condition always has a last review; the service asks for one when the limit is set | REQ-233 | Not worked by hand; the requirement does not say |
| A manufacturer's recommendation marked Overdue as a life limit is | Marked alike | REQ-232 | Ours (D), recorded. ML.A.503 speaks of the approved service life limit specified in the maintenance programme and directives |
| Point letters of ML.A.403, ML.A.305 and ML.A.503 | Cited as (a), (b)(1) to (4), (c), (d), (e) | REQ-222, REQ-231, REQ-264 | The Regulatory Library page shows none; taken from the order of the paragraphs |
| The reweigh threshold; Due in 6 Months; the Fleet's 30 days; the forecast date | As built | REQ-256, REQ-234, REQ-281, REQ-291 | Ours (D); no rule was found or looked for beyond those read above |

## What Is Done About the Findings

None of the findings is a disagreement in a calculation. Findings 1 to 4 and 6 are taken into the fixes after the Phase 1 independent review, each test first. Finding 5, and where the default limit of a deferral is counted from, are for Alex King. Finding 7 is a comment, corrected with the fixes. Finding 8 is recorded as ours unless Alex King says otherwise.
