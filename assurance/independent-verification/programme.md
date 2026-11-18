# Independent Verification: Flags, Deadlines and the Programme Review

Module: `airworthiness_rules.programme` (`Thresholds`, `limit_flag`, `task_flag`, `deadline_flag`, `programme_review_due`, `pilot_owner_notification_deadline`, `pilot_owner_told_late`), and the use of `airworthiness_rules.intervals.limits` for a task never yet done.

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the quoted rules (ML.A.305(a); ML.A.302(c)(9); ML.A.302(d)(1)(a); Appendices I and II to Part-ML), the project conventions (exact day counts, month ends, the states of a limit, the Due Soon thresholds, the worst flag governs) and nine cases. It read no files and ran no code, worked each answer by hand, and was told to answer "not determined by the rules given" instead of guessing. This mirrors an independent inspection.

The quoted rules were read in the UK text in the Civil Aviation Authority Regulatory Library on 18 November 2026. The pilot-owner's 30 days is in Appendix I (the owner's obligations under the contract) and Appendix II (pilot-owner maintenance) to Part-ML.

## Result

Every case agrees with the golden tests in `tests/test_golden_programme.py`.

| Case | Independent Answer | Agree |
|---|---|---|
| G-ABCD 50-Hour Check, due 6,425.0, at 6,412.6, 6,414.9, 6,415.0, 6,424.9, 6,425.0, 6,425.1 hours | No flag (12.4); no flag (10.1); Due Soon (10.0); Due Soon (0.1); Due; Overdue | Yes |
| G-FMNO Annual Check, calendar due 4 February 2027, tolerance ends 4 March 2027, 52.0 hours to the hours limit, on 4 and 5 January, 3, 4 and 5 February, 4 and 5 March 2027 | No flag (31 days); Due Soon (30); Due Soon (1); Due; Within Tolerance; Within Tolerance; Overdue | Yes |
| Cycles limit with 11 and 10 remaining | No flag; Due Soon | Yes |
| Thresholds of 60 days, 15.0 hours: 12.4 hours; 60 days; 61 days | Due Soon; Due Soon; no flag | Yes |
| Hours limit 3.0 remaining, calendar limit 17 days past | Due Soon; Overdue; task Overdue | Yes |
| G-ABCD tyre replaced 22 October 2026: release in the records by; flag on 22 October, 18, 21 and 22 November | 21 November 2026; Due Soon; Due Soon; Due; Overdue | Yes |
| Pilot-owner to inform the organisation by; informed 21 November, 22 November, 22 October | 21 November 2026; not late; late; not late | Yes |
| Programme last reviewed 11 November 2026; 29 February 2028 | Next by 11 November 2027; 28 February 2029 | Yes |
| G-CDEF engine overhaul, never yet done, counted from 0.0 hours on 12 March 2019, every 2,000 hours, engine at 1,780.0 | Due 2,000.0; 220.0 remaining; no flag | Yes |
| First at 500 hours since new then every 100; at 420.0 hours; then done at 498.0 | Due 500.0, 80.0 remaining; next 598.0, not 600.0 | Yes |

## Findings Acted On

| Finding | Action |
|---|---|
| A task never yet done with no stated starting point must be shown as unknown and needing attention, never as not due or with no flag | Fixed in this change: such a task is shown as Cannot Be Calculated with what is missing, and comes first on the Fleet. Test `test_a_task_that_cannot_be_calculated_is_shown_first_never_as_not_due` |
| A deadline had no record of being met, so it would either stay Overdue for ever or be cleared with nothing to show it was late | Fixed in this change: once the release is recorded the flag goes, and a release recorded after the 30 days is shown as recorded late; the same for a pilot-owner who told the organisation late. Test `test_g_abcd_release_to_service_deadline_is_shown_and_flagged` |
| The task's flag could hide which limit drives it | Already met: every limit is shown with its own flag, and the one projected first is marked (REQ-043, REQ-044) |
| A stale counter reading shows a limit as not due when it is | Already met in part: every figure shows the date its hours were entered for (REQ-054) |
| A tolerance applied to the wrong task; a missing tolerance setting | Already met: none unless the task is a Minimum Inspection Programme inspection, and that kind is refused outside a programme on that basis (REQ-049) |
| A threshold must never affect Due, Within Tolerance or Overdue | Already met: thresholds are used only for Due Soon |
| Binary floating point and rounding at the boundaries | Already met: hours are exact decimals (REQ-028) |
| An engine task measured against airframe hours | Already met: each task names its counter (REQ-059); golden case G-CDEF |

## Readings the Implementation Makes

| Point | Reading Implemented | Requirement | Status |
|---|---|---|---|
| "At least annually": within 12 months of the last review, or once in each calendar year | Within 12 months of the last review | REQ-053 | To Be Checked |
| The day a 30-day deadline starts | The day the work was completed | REQ-051, REQ-055 | Matches ML.A.305(a), "after the day of the completion" |
| Whether an organisation's day threshold changes the flag of a regulatory deadline | It does not: the deadline is Due Soon from its first day | REQ-055 | Decision on record |
| A programme never yet reviewed | No due date is shown until the first review is recorded | REQ-053 | Question for Alex King: should it run from the date the programme was approved |
| Annual and 100-hour inspections recorded as two tasks | Not prevented. The sample programmes record one task with both limits | REQ-048 | Requirement to consider with the import |

## Findings Carried Forward

| Finding | Where It Goes |
|---|---|
| Only the limits entered are evaluated: a task entered with hours only, when the data also sets a calendar limit, could be overdue by date with no flag | Import with a verification report (REQ-170); programme review (REQ-053) |
| An organisation can set a Due Soon threshold of zero, which removes the warning | Question for Alex King: whether there should be a floor |
| Within Tolerance must not read as acceptable | Interface (REQ-056, REQ-139) |
| Whether a contract exists, and whether a task is permitted pilot-owner maintenance, are not checked | Outside the slice: contracts and Appendix II task lists |
| How a reading in hours and minutes is converted to one decimal place | Question for Alex King, with REQ-059 |
