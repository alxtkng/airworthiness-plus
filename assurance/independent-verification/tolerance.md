# Independent Verification: Tolerance for the Minimum Inspection Programme

Module: the tolerance rules in `airworthiness_rules.intervals` (`Tolerance`, `TaskKind`, `State`, `limits`, `task_state`, `tolerance_outlasts_certificate`).

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the quoted rules (ML.A.302(c)(2), (c)(4), (d)(1)(a), (d)(1)(b); ML.A.303; AMC1 ML.A.302(d); GM1 ML.A.302; GM1 ML.A.302(c)(3); GM1 ML.A.302(c)(4)), the project conventions (exact day counts, month ends, exact decimal hours, the states of a limit) and the cases. It read no files and ran no code, worked each answer by hand, and was told to answer "not determined by the rules given" instead of guessing. This mirrors an independent inspection.

The rules were read in the UK text in the Civil Aviation Authority Regulatory Library on 18 November 2026.

## Result

Every case agrees with the golden tests in `tests/test_golden_tolerance.py`.

| Case | Independent Answer | Agree |
|---|---|---|
| G-BXYZ on 18 November 2026 at 3,318.0 hours | Hours due 3,359.0, 41.0 remaining; tolerance ends 3,369.0, 51.0 remaining. Calendar due 30 July 2027, 254 days; tolerance ends 30 August 2027, 285 days. Not due | Yes |
| G-FMNO on 18 November 2026 at 4,950.2 hours | Hours due 5,012.0, 61.8 remaining; tolerance ends 5,022.0, 71.8 remaining. Calendar due 4 February 2027, 78 days; tolerance ends 4 March 2027, 106 days. Not due | Yes |
| G-BXYZ on 1 June 2027 at 3,359.0, 3,359.1, 3,365.0, 3,369.0, 3,369.1 hours | Due; Within Tolerance (9.9 left); Within Tolerance (4.0); Within Tolerance (0.0); Overdue (0.1 past). Calendar limit 59 days away. Task due in every case | Yes |
| G-FMNO on 4, 5 and 20 February, 4 and 5 March 2027 | Due (28 days of tolerance); Within Tolerance (27); Within Tolerance (12); Within Tolerance (0); Overdue (1 day past). 52.0 hours to the hours limit | Yes |
| G-FMNO inspected 20 February 2027 at 4,960.0 hours | Next due 5,060.0 hours or 20 February 2028; tolerance ends 5,070.0 or 20 March 2028 | Yes |
| G-FMNO inspected early, 10 January 2027 at 4,955.0 hours | Next due 5,055.0 hours or 10 January 2028. The unused 25 days and 57.0 hours are not carried over | Yes |
| Inspections on 31 January 2026, 31 January 2027, 28 February 2026, 31 December 2026, 29 February 2028 | Due 31 January 2027, 31 January 2028, 28 February 2027, 31 December 2027, 28 February 2029; tolerance ends 28 February 2027, 29 February 2028, 28 March 2027, 31 January 2028, 28 March 2029 | Yes |
| Sailplane inspected 15 May 2026 | One calendar limit. Due 15 May 2027, 178 days; tolerance ends 15 June 2027, 209 days | Yes |
| Tolerance on a repetitive airworthiness directive | No (ML.A.303) | Yes: refused |
| Tolerance on an airworthiness limitation inspection | No (GM1 ML.A.302(c)(4)) | Yes: refused |
| Tolerance on the retirement life of a life-limited part | No (GM1 ML.A.302(c)(4)) | Yes: refused |
| Tolerance on a task of a programme based on the design approval holder's instructions | Not determined by the rules given; the safe default is none | Yes: refused until sourced |
| Tolerance of 2 months or 15 hours | No (ML.A.302(d)(1), GM1 ML.A.302) | Yes: refused |
| G-BXYZ certificate valid to 2 August 2027 | Calendar tolerance ends 28 days after it | Yes |
| G-FMNO certificate valid to 27 April 2027 | Calendar tolerance ends 54 days before it | Yes |
| Hours limit passed by 5.0, calendar limit 40 days away | Hours Within Tolerance, calendar Not Due, task due | Yes |
| Hours limit passed by 10.1, calendar limit 40 days away | Hours Overdue, calendar Not Due. The state of the whole task is not defined by the conventions | See the first finding |

## Findings Acted On

| Finding | Action |
|---|---|
| The conventions gave a state for each limit but none for the whole task. A task shown by its calendar limit, or its best limit, would read Not Due or Within Tolerance while its hours limit is Overdue | Fixed in this change: `task_state` returns the worst state among the limits. Tests `test_the_worst_limit_gives_the_state_of_the_task` and the property test on tolerance. REQ-056 restated |
| A tolerance applied to a directive, an airworthiness limitation or a life limit would show Within Tolerance when the item is overdue | Already met: refused by `limits` for every kind of task but an inspection of the Minimum Inspection Programme, and refused when no kind is stated (REQ-049) |
| The next interval anchored to the old due point after an early inspection would show a task not due when it is | Already met: every limit runs from the reading at which the inspection was done; golden and property tests (REQ-048) |
| Binary floating point could misclassify at the boundaries 3,369.0 and 3,369.1 | Already met: hours are exact decimals (REQ-028) |
| The end of the calendar tolerance built as inspection date plus 13 months differs by a day from due date plus 1 month | The rule is stated once: the due date plus 1 month. Golden case 29 February 2028 |

## Readings the Implementation Makes

The quoted text does not state these outright. Each needs a source or a decision by Alex King before its requirement counts as verified.

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| "1 month or 10 h": whether both may be used, each on its own limit, or only one of the two | Each on its own limit: 1 month on the annual limit, 10 hours on the 100-hour limit. The sailplane and touring motor glider programme in AMC1 ML.A.302(d) says "as applicable" | REQ-048 | To Be Checked |
| Whether the tolerance may be used at two inspections in a row. GM1 ML.A.302(c)(3) calls it a one-time interval extension | Not refused. Each use is visible from the reading at which the inspection was done | REQ-056 | To Be Checked |
| Whether a programme based on the design approval holder's instructions may carry a tolerance stated in those instructions | Refused: ML.A.302(d)(1) gives a tolerance to the Minimum Inspection Programme only | REQ-049 | To Be Checked |
| Whether the last hour or day of the tolerance may be used | Yes: reaching the end of the tolerance exactly is Within Tolerance; passing it is Overdue. The same reading as a limit reached exactly | REQ-056 | To Be Checked, with the open reading on a calendar limit at 0 days |
| What 1 month and annual mean in days | 12 months and 1 month by the month-end rule of REQ-047. Our rule, not the regulation's | REQ-047, REQ-048 | Decision on record |
| Whether G-BXYZ and G-FMNO are on the Minimum Inspection Programme | Taken to be, for the golden cases. `SampleData.md` does not record the basis of any programme | REQ-040 | To be confirmed by Alex King |

## Findings Carried Forward

| Finding | Where It Goes |
|---|---|
| Within Tolerance must not read as an automatic permission to fly: the tolerance "may be applied", and someone decides to apply it | Interface, REQ-056 and REQ-139; who records the decision is a question for the accomplishment record (REQ-050) |
| The category of aircraft decides the programme: a touring motor glider follows the aeroplane rule, a sailplane has no hours limit, and airships and rotorcraft have no Minimum Inspection Programme (ML.A.302(d)) | Requirement to add with the aircraft and programme models (REQ-020, REQ-040) |
| An inspection that spans several days: which date and hours the next interval runs from | Requirement to add with the accomplishment record (REQ-050). The earliest date and lowest hours are the safe choice |
| A partial inspection or a wrong entry would reset both limits falsely | Accomplishment record and entry checks (REQ-025, REQ-050) |
| A stale or wrongly sourced hours figure overstates what remains; rounding to one decimal place can hide a small exceedance | REQ-054 (date of the reading shown), REQ-059 (counter named); rounding on entry is a point for the utilisation entry screen (REQ-024) |
| The warning about the review certificate is separate from the state of the task: Within Tolerance to 30 August 2027 does not show that the certificate ends 2 August 2027 | Interface: REQ-057 beside every calendar tolerance |
| Whether the valid-to date of a certificate is itself a valid day | Already open in `review-and-dates.md` |
| "Unless otherwise specified by the CAA" in ML.A.303, and any allowance written in a directive itself | Airworthiness directive module (REQ-065): the directive's own requirements are the limit |
