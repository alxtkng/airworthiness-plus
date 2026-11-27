# Independent Review of Phase 0 of the Canvas Build

Phase 0 of `prompts/canvas-build.md`, Foundations, merged on 24 November 2026 in pull requests 110 to 115, was reviewed that day by a reviewer that did not write it: a separate session, read-only, given the code and no account of what it was meant to show. It confirmed each finding marked Confirmed by running it, in throwaway tests or in a rehearsal on an upgraded database whose owner was not a superuser. A second reviewer recomputed the two calculations of the phase by hand before reading the code (`personnel-and-alerts.md`).

No way was found for one organisation to read or change another's records. No hole was found in the role matrix, and no odd input gave a server error.

Each finding was decided as ours on 24 November 2026 (`design-system/Decisions.md`, Canvas Build, Corrections) and fixed test first in pull requests 116 to 120, merged by 27 November 2026.

## Findings and What Was Done

| Number | Finding | How Found | Outcome |
|---|---|---|---|
| 1 | The Administrator could change what an issued review certificate showed. The certificate page read the organisation's name and address and the signatory's name as they stood when the page was opened. Renaming Lucy Grant and blanking the organisation's address changed the certificate of G-CDEF, though issue refuses a blank address | Confirmed | Fixed, pull request 116. A certificate and an extension keep what they showed when recorded. The database writes the values and never lets them be altered. Existing certificates were given the values as they stood on the day of the migration, and the history of each says so |
| 2 | The name of a person with a sign-in, and so the name the history records as who acted, could be changed without the code every other change to a sign-in needs | Confirmed | Fixed, pull request 117. A fresh sign-in or the code, on the code page of the Users page |
| 3 | The test site's top-up changed and duplicated people once anyone had edited them. A person renamed was added again at every start, a reporting line taken off was put back past the check for circles, and an edit was wiped | Confirmed | Fixed, pull request 117. The people are added once, a record says so, and after that a start adds and changes nobody. Nobody is found by name, and every write goes through the services the pages use |
| 4 | A new sign-in was silently joined to a person of the same name, and no page could undo it. A user added as Sam Patel was given the certifying staff record | Confirmed | Fixed, pull request 117. A new sign-in is given a new person, unless the Administrator chooses a person with no sign-in on Add a User. A wrong link made before the fix is corrected by making the sign-in inactive and adding a new one |
| 5 | A person recorded as having left could have an active sign-in | Confirmed | Fixed, pull request 117. Recording the day makes the sign-in inactive at once and ends its sessions. A sign-in is not made active while its person is recorded as having left |
| 6 | Record Kept Until was wrong in two cases: it went by the staff group and not by being review staff, and by the approvals held today and not on the day the person left, so giving up Part-145 shortened it | Confirmed | Fixed, pull request 117. The approvals are those held on the day the person left; a person counts as review staff who ever was; the leaving day is recorded on the review staff record too |
| 7 | The Dashboard left aircraft looking clear: a programme never reviewed, a Non-Part 21 aircraft whose tasks are not calculated, and an aircraft whose type rating has no maintenance data recorded | Confirmed | Fixed, pull request 118. A row for each |
| 8 | Every role read every colleague's user name on the Staff pages, and five wrong passwords lock a name for 15 minutes. The same pages offered Add a Person, Add a Customer and change forms to roles the server refuses | Confirmed | Fixed, pull request 118. A user name is shown only to a role that may manage users. Links and forms are shown only to roles that may use them. The server check was sound and is unchanged |
| 9 | The second sample organisation's Administrator was given the first Administrator's first password. And if any of its three user names was already taken, every start of the test site failed | By reading; the values and the failure confirmed in the rehearsal | Fixed, pull request 117. A generated value of its own in `render.yaml`. With no value, with the first's, or with a user name taken, the start says so and carries on. Not changed: a second organisation set up before the fix keeps the password it was given |
| 10 | Nothing checked the approvals or privileges an organisation holds. An organisation holding Part-CAMO and Part-145 could record review staff and issue a review certificate | By reading | Fixed, pull request 116. Review staff, reviews and review certificates are offered only to an organisation holding Part-CAO with the airworthiness review privilege, CAO.A.095(c). Any other is refused with the reason, on the page and on the server, and the refusal is logged |
| 11 | The database did not hold "every sign-in has a person" after the sign-in was made: the application's role could take a sign-in off its person. It could also rewrite the reference of the approval an organisation was set up with | Confirmed | Fixed, pull request 119. Two triggers. The privileges of the approval and the day the set-up approval ended are not held this way: see What This Shows |
| 12 | The export of one aircraft lost the names of earlier owners: its history held only their identifiers | Confirmed | Fixed, pull request 119. The export holds every customer that has ever owned the aircraft |
| 13 | Migration aircraft 0003: texts differing only in outer spaces made two customers of one name; a blank owner became Not Recorded; going back failed part way | Confirmed, low | Fixed, pull request 119. Text is trimmed first. The migration says it cannot be reversed, with the reason, before it changes anything. A blank owner is still named Not Recorded, which is now written down |
| 14 | Recording an approval and naming a new customer read and then wrote with no lock: a double submit gave a server error, or two customers of one name. Changing an owner with a choice that was not valid redirected in silence | By reading, low | Fixed, pull request 119. Both take the organisation's row first, and a conflict is refused with the reason. The owner form shows its error |

## From the Recompute

The independent recompute agreed with the code on every calculation (`personnel-and-alerts.md`). It found by reading:

| Finding | Outcome |
|---|---|
| "At most 365" for the earlier alert, and the 365 of the calendar lead time, were held only by the form | Fixed, pull request 116. The service and a database constraint hold them, with the bounds on hours, cycles and the default deferral limits |
| Review staff was read from the staff group as it stands, and the approvals were those held today | The same as finding 6. Fixed, pull request 117 |
| The docstring of the 29 February case in `tests/test_golden_personnel.py` explained nothing in its case | Corrected, pull request 116 |
| With a calendar lead time of 365 days no earlier alert is allowed, and the page gives no reason beyond its two messages | Not changed. Correct by REQ-213; for Alex King if the wording matters |

## Tests That Could Not Fail for What They Claimed

Found by 68 single-line mutations that survived. Each mutation listed was put back in place after the fix and now fails a test; with it taken out every test passes.

| Claim | Why No Test Could Fail | Outcome |
|---|---|---|
| Nobody whose record already says more than their name is changed by the top-up | Removing the guard passed every test: one test asserted only a count on a complete sample, and the other never edited a record before the second start | `test_top_up`: a_sign_in_whose_record_says_more_than_a_name_is_left_as_it_is, a_top_up_after_people_were_edited_changes_and_adds_nothing. Pull request 117 |
| A person who already has a sign-in is not linked again | Removing the condition passed every test | `test_people`: a_sign_in_is_given_to_a_person_already_recorded_only_when_chosen. Pull request 117 |
| The earlier alert on the Fleet, and in the working shown beside the figure | Only the review schedule was tested | `test_settings`: the_earlier_alert_reaches_the_fleet_and_the_working_shown, worked by hand. Pull request 118 |
| Dashboard rows with no test: the annual programme review; review staff recency lapsed; a task that cannot be calculated; solved problems left out; wholly checked imports left out; held-and-current data left out; the Past the Limit wording; no No Maintenance Programme row for a Non-Part 21 aircraft | No test built the case | A test for each in `test_dashboard`, worked by hand from the sample. Pull request 118 |
| Migration 0003's handling of blank or untrimmed text | Replacing the trimming with the raw text passed | `test_customers`: owner_text_is_trimmed_before_customers_are_made. Pull request 119 |
| The owner's work, as the owner | Every test of it ran as a superuser, whom row-level security never holds | The top-up and migration 0003 are each tested as an owner of every table who is not a superuser, inside the test suite (`tests/conftest.py`, as_owner_who_is_not_a_superuser). Pull requests 117 and 119. The whole upgrade was also rehearsed that way on a database built from `main` before each merge that carried a migration |

Each fix was tested the same way: 79 mutations across pull requests 116 to 119, each taking one part of a fix out. A test fails with every one. Three survived at first and were dealt with: a look for a taken user name that the catch of the conflict already covered, which was removed; the check for a sign-in's person with no organisation set; and trimming where customers are made. The tests of the last two were strengthened.

## Found While Fixing

- A user added in the first organisation under the second sample Administrator's user name made the start report the second organisation as already set up. The start now reads the organisation that user belongs to. Pull request 117.
- A counter given the position Engine 1 is written Engine Engine 1 where a task cannot be calculated. Not in the review and not fixed here; for Phase 1, where Aircraft Configuration is built.

## Where Nothing Was Found

Reading or changing another organisation's records, on any page of Phase 0 or below it. The role matrix on every new address. Server errors from odd input on the new forms. The linking of a sign-in across organisations, which was not possible. The untouched case of the top-up: on a sample nobody had edited, it added what was missing and then nothing. The calculations of Record Kept Until and of the earlier alert, which the recompute worked by hand first and found to agree in every case.

## What This Shows

- As on 19 and 20 November 2026, the tests written with the code missed the most serious defects. Findings 1, 2 and 3 each broke a rule written in `design-system/Decisions.md` or a requirement.
- Four findings came from one cause: something read or matched later what should have been kept or chosen at the time. A certificate read the organisation as it stands today; a sign-in and the top-up found a person by name; a retention day read today's approvals.
- Tests that run the owner's work as a superuser cannot see what row-level security does to a real owner. The suite can now run such work as an owner with no other power.
- Still open, for Alex King. The privileges of an approval, and the day the set-up approval was no longer held from, are not held by the database against the application's own role; the decision of 24 November 2026 named the type and the reference. The check of finding 10 therefore rests on application code never changing the privileges, which it does not. And the second organisation on the test site as it stood on 24 November 2026 keeps the first password it was given, which was the first Administrator's: it is changed by signing in to it, or by remaking the database.
