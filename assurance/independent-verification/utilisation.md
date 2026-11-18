# Independent Verification: Hours and Cycles Entries

Module: `airworthiness_rules.utilisation` (`check_entry`, `current_total`).

Date: 18 November 2026.

Method: a separate agent that had not seen the implementation, the tests or the repository was given only the rules as numbered statements and 25 cases. It read no files and ran no code, worked each answer by hand, and was told to answer "not determined by the rules given" instead of guessing. This mirrors an independent inspection.

These rules are ours, not the regulation's (`design-system/Decisions.md`, Interface). They answer hazard H-011: hours or cycles entered wrongly and accepted.

## Result

Every case agrees with the golden tests in `tests/test_golden_utilisation.py`.

| Case | Independent Answer | Agree |
|---|---|---|
| G-ABCD, 6,412.6 hours and 4,236 cycles on 18 November 2026 after 6,375.0 and 4,180 on 2 October 2026 | Accepted: 37.6 hours and 56 cycles in 48 days counted | Yes |
| First entry for a counter | Accepted | Yes |
| 6,374.9 hours, or 4,179 cycles, after 6,375.0 and 4,180 | Refused: lower | Yes |
| 6,375.0 and 4,180 again | Accepted: equal is not lower | Yes |
| 6,402.6 after 6,412.6 the same day | Refused: lower | Yes |
| 64,126.0 after 6,375.0, 48 days counted | Refused: 57,751.0 hours against 1,152.0 | Yes |
| Same day, gain of 10.0, 10.1, 24.0, 24.1 hours | Accepted; Needs Confirmation; Needs Confirmation; Refused | Yes |
| Next day, gain of 20.0, 20.1, 48.0, 48.1 hours | Accepted; Needs Confirmation; Needs Confirmation; Refused | Yes |
| Same day, gain of 100 and 101 cycles | Accepted; Needs Confirmation | Yes |
| Late entry for 10 November 2026 before 6,412.6 and 4,236 on 18 November: 6,400.0 and 4,220; 6,412.6 and 4,236; 6,412.7; 4,237 cycles | Accepted; Accepted; Refused; Refused | Yes |
| Entry dated 19 November 2026 | Refused: after today | Yes |
| 6,412.65 hours | Refused: more than one decimal place | Yes |
| 6,412.60 hours | Accepted: the same as 6,412.6 | Yes |
| Current total of entries on 2 October and two on 18 November | 6,412.6 hours and 4,236 cycles; without that entry, 6,411.0 and 4,234 | Yes |

## Findings Acted On

| Finding | Action |
|---|---|
| A run of entries each within the limit could add up to a gain that is not: on one date, 10.0 hours at a time with no end and no confirmation; on following dates, 48.0 hours a step | Fixed in this change: a new entry is measured against every other current entry of the counter, not only its neighbours. Tests `test_a_run_of_same_day_entries_cannot_add_up_past_the_limits` and `test_steps_on_following_days_cannot_add_up_past_the_limits` |
| A late entry was tested against the entry after it only for "not above", so the rate it left to that entry was never looked at | Fixed in this change: the gain from the new entry to every later entry is measured the same way. Test `test_a_late_entry_is_measured_against_the_entries_after_it_too` |
| With two entries on one date the rules did not say which was "the earlier entry"; taking the lower would let the total fall | Fixed in this change: a new entry may not be below any entry dated on or before it, nor above any dated after it. Test `test_two_entries_on_one_date_are_both_respected`. The database trigger takes the highest of the date |
| Binary floating point could misjudge the one decimal place and the boundaries | Already met: hours are exact decimals (REQ-028) |
| Fractional cycles | Already met: cycles are whole numbers by type |
| "Today" needs a named clock | Already met: the UK local date (REQ-137) |

## Findings Carried Forward

| Finding | Where It Goes |
|---|---|
| The first entry for a counter is checked against nothing, so 641.2 for 6,412.6, or a year typed wrongly, would pass | Import with a verification report, every value beside its source (REQ-170, hazard H-008) |
| The limits are loose over a long gap: after 47 days a gain of up to 480.0 hours is accepted without confirmation | To be sharpened with the planning utilisation of the aircraft when the maintenance programme is built (REQ-044). Until then REQ-054 shows the date of every figure |
| There is no lower check: an aircraft that shows no gain for a long time, or a slip downwards that is still above the previous entry, is accepted | The same |
| An entry dated too late blocks true entries before it, and the total stays low | Corrected by superseding the wrong entry (REQ-025). The page for hours and cycles says which entry is in the way: interface, REQ-026 |
| Superseding an entry can lower the total | Intended: that is what a correction is. The superseded entry and who made the correction stay in the history (REQ-130) |
| Cycles are checked apart from hours: 20.0 hours with no cycles is accepted | Requirement to add with the counter model: what a cycle is for each kind of counter (REQ-059) |
| An engine or propeller can gain more than the airframe it is fitted to | Requirement to add with fitted components (REQ-059) |
| A zero-timed engine or a replaced meter needs a lower total | A different engine is a different counter. A replaced meter is a requirement to add (REQ-059) |
| Who confirms an unusual gain, and whether they must be someone other than the person entering it | The person entering it, in the slice; the entry is marked and the history names them. Whether a second person should confirm is a question for Alex King |
| What hours are: flight time, or a meter reading | Question for Alex King, with REQ-059 |
| A wrong server clock defeats the check on future dates | Operations: time synchronisation is checked in Step 8 |
