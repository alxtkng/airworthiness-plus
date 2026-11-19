# Independent Review of the Code of 19 November 2026

The application code and tests merged on 19 November 2026 were reviewed the same day by a reviewer that did not write them: a separate session, given the changes and no account of what they were meant to show. It read about 3,400 changed lines across 71 files, and confirmed each finding marked Confirmed by running it, in the tests or in a real browser. It changed nothing.

No finding lets one organisation see or change another's records, and none is an injection or a script run from a page.

## Findings and What Was Done

| Number | Finding | How Found | Outcome |
|---|---|---|---|
| 1 | The code before an Administrator's reset could be skipped: adding a user or changing roles asked for none, so a session left open could add an Administrator, sign in as them, and reset anyone | Confirmed | Fixed, pull request 92. Every change on the Users page asks |
| 2 | Guesses at the code were not limited once signed in | Confirmed | Fixed, pull request 92. Five wrong codes lock the name, as at sign-in |
| 3 | An Administrator could end their own other sessions without the code, through the Users page | Confirmed | Fixed, pull request 92, by the fix to 1 |
| 4 | The Access Log page failed on a digit that is not a number, and on 5,000 digits | Confirmed | Fixed, pull request 92 |
| 5 | The limit on exports of an organisation could be passed by requests sent together | By reading | Fixed, pull request 92, by a lock for each organisation. It has no test of its own |
| 6 | Lowering a person's last review before these records could race with recording a certificate against it | By reading | Fixed, pull request 93, by locks on both sides. It has no test of its own |
| 7 | A restoration moved the limit on a certificate from before these records into these records, so a certificate with no review and no serial could be recorded as the organisation's own | Confirmed | Fixed, pull request 93. The restoration has its own date; the limit is never after the day the person was recorded as review staff |
| 8 | The working of a date of expiry contradicted its own inputs when the earlier certificate was recorded afterwards | Confirmed | Fixed, pull request 93 |
| 9 | The working of extensions gave a day for an extension that could not be made | Confirmed | Fixed, pull request 93 |
| 10 | An aircraft with no certificate and nothing ranked fell to the bottom of the Fleet | Confirmed | Fixed, pull request 94. It comes straight after an Unserviceable aircraft |
| 11 | A column of numbers sorted as text as soon as one was negative: the application writes a minus sign, and the script looked for a hyphen | Confirmed | Fixed, pull request 94 |
| 12 | A column of dates sorted as text when one cell was not a date | Confirmed | Fixed, pull request 94. A column is read as dates or numbers when most of its cells are; the rest come after |
| 13 | A Status column put Within Tolerance after Due Soon | Confirmed | Fixed, pull request 94. Within one colour the worse word comes first |
| 14 | A task that cannot be calculated travelled with an unrelated task when the table was sorted | Confirmed | Fixed, pull request 94. It is a row of its own and comes first by Status |
| 15 | The search matched what a form offers, so some words matched every row | Confirmed | Fixed, pull request 94. Forms, buttons and labels are not searched |
| 16 | The sort test wrote a negative number with a hyphen, which the application never does, so it passed while 11 was live | Confirmed | Fixed, pull request 94. The test writes what the application writes |
| 17 | Two assertions that the Access Log hides another organisation's entries had no such entries to find | Confirmed | Fixed, pull request 92 |
| 18 | "Shown once" for a new user was checked against a password the test never gave anyone | By reading | Fixed, pull request 92 |
| 19 | The test of the export limit made 7 exports at one instant, so a limit of 6 for ever would have passed | By reading | Fixed, pull request 92. The hour is tested |

## Where Nothing Was Found

The list of a user's sessions and ending one; the Access Log page apart from 4; first passwords; the name of the hashing method on history entries; the record of what each action may set; the import of certificates; the workings of the programme, the 30 days for a release, the parallel run, the windows, the copy deadline, recency and the tolerance; and the table script as a way to run script from text.

## What This Shows

- The tests written with the code missed the two most serious defects, 1 and 7. Both were in rules stated in `design-system/Decisions.md` as reasoned and safe. A reviewer who starts from the code and not from the reasoning found them in minutes.
- Four tests could not fail for what they claimed. Three of the four were written the same day as the code they tested.
- This review covers one day. The code merged on 18 November 2026 has had the independent recompute of its calculations and no review of this kind.
