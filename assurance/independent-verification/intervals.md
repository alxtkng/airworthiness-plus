# Independent Verification: Intervals and Next Due

Module: `airworthiness_rules.intervals`, and `add_months` in `airworthiness_rules.dates`.

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the project rules for next due (ML.A.302 requires intervals in hours, calendar time or cycles, whichever comes first; the ranking and month-end rules are in `design-system/Decisions.md`) and the cases. It worked each answer by hand.

## Result

Every case agrees with the golden tests in `tests/test_golden_next_due.py`.

| Case | Independent Answer | Agree |
|---|---|---|
| G-ABCD 50-Hour Check | Due 6,425.0; 12.4 hours remaining | Yes |
| G-BXYZ 100-Hour or Annual Check | Hours due 3,359.0, 41.0 remaining, 82 days projected; calendar due 30 July 2027, 254 days; hours come first | Yes |
| G-FMNO Annual Check | Hours due 5,012.0, 61.8 remaining, 309 days projected; calendar due 4 February 2027, 78 days; calendar comes first | Yes |
| 100 hours or 100 days from 31 October 2026 | Calendar due 8 February 2027, 82 days; hours 82 days; tie, both reported | Yes |
| Hours, cycles and days together | 20.0 hours (20 days), 30 cycles (15 days), 40 days; cycles come first | Yes |
| No planning utilisation | No limit ranked; all reported | Yes |
| 12.4 hours at 0.8 hours a day | 15 days | Yes |
| Limit reached exactly, then passed | Due and not overdue at 0; overdue at -0.1 hours and -1 day | Yes |
| Seven month-end cases | 28 February 2026, 29 February 2028, 28 February 2027, 28 February 2027, 15 January 2027, 28 February 2029, 4 February 2027 | Yes |

## Findings Acted On

| Finding | Action |
|---|---|
| With no planning utilisation, a limit already reached was returned as "not ranked" alongside limits not yet reached | Fixed in this change: a reached limit is returned first whatever the planning figures. Test `test_a_reached_limit_comes_first_without_any_planning_figure` |
| Binary floating point could put a projection one day out or show a false overdue | Already met: hours are exact decimals (REQ-028); property test on projection bounds |

## Findings Carried Forward

| Finding | Where It Goes |
|---|---|
| The ranked limit is an estimate; every limit must stay visible and the ranking labelled as a projection | Interface requirement, REQ-139 and REQ-044 |
| When no utilisation is recorded the interface must say the first limit is not determined | Interface, REQ-044 |
| Rounding down can make a tie where the calendar limit truly falls first | Accepted: both are shown |
| Remaining exactly 0 on a calendar limit: may the aircraft fly to the end of that day | To Be Checked; decision for Alex |
| A task never yet done (threshold since new or since overhaul) is not covered | Requirement to add before the programme module is built. Added 18 November 2026: REQ-058 |
| Tolerance and permitted variation (REQ-048, REQ-049) are not implemented | Next: needs AMC ML.A.302 read in the UK text. Done 18 November 2026: `tolerance.md` |
| Which counter a task runs against: airframe, engine or propeller | Requirement to add with the aircraft model (REQ-020). Added 18 November 2026: REQ-059 |
| Month-end rule is one way: done 28 February plus 1 month is 28 March | Intended; intervals run from the actual date done |
