# Independent Review of the Code of 18 November 2026 and the Test Site

The code merged on 18 November 2026, and the test site's start-up code added on 20 November 2026, were reviewed on 20 November 2026 by a reviewer that did not write them: a separate session, read-only, given the code and no account of what it was meant to show. It confirmed each finding marked Confirmed by running it, as a throwaway test or a script against a database of its own, which it then deleted.

No finding lets one organisation read or change another's records. None is an injection, and no owner credential or secret reaches the running test site, a log or a page.

## Findings and What Was Done

| Number | Finding | How Found | Outcome |
|---|---|---|---|
| 1 | The task of an airworthiness directive could be retired from the programme by a direct request. An overdue directive then left the Fleet and the programme page, still Applicable, with no terminating action | Confirmed | Fixed, pull request 102. The task of a directive ends only by a terminating action or a decision of Not Applicable |
| 2 | Making a user inactive held their sessions instead of ending them. A browser that kept asking kept its session for up to 12 hours, and it resumed if the user was made active again | Confirmed | Fixed, pull request 103. The session is removed at its next request, and one made before cannot resume |
| 3 | An export holding a forged copy of a file, placed before the genuine one, passed its check | Confirmed | Fixed, pull request 104. Two files of one name fail the check |
| 4 | A programme's basis or category could be changed under its inspections, leaving an inspection the system itself refuses, with a tolerance the regulation does not give | Confirmed | Fixed, pull request 102. The change is refused, and a tolerance is given only while the programme is on the Minimum Inspection Programme |
| 5 | A finding could be recorded on a point at the moment the review's certificate was issued, by a second request | Confirmed | Fixed, pull request 104. The review is read under a lock in the service and in the database. Run again by hand with two connections: without the fix the finding was committed on the issued review; with it, the second request waited for the issue and was refused |
| 6 | The lock after five failed sign-ins lasted 15 minutes from the first failure, not the fifth | Confirmed | Fixed, pull request 103 |
| 7 | Server errors from odd input: a user name with a NUL character or of more than 254 characters; a code in digits other than 0 to 9; a correction of another counter's entry; cycles above 2,147,483,647 on three pages; a NUL character on the import check | Confirmed | Fixed, pull requests 103 and 105. Every whole number on every form is limited to what the database holds |
| 8 | The sample Administrator's first password never had to be changed and never expired, so it stayed usable while it was readable in Render | Confirmed | Fixed in this pull request. It is a first password like any other: changed at the first sign-in, good for 7 days |

## Tests That Could Not Fail for What They Claimed

| Test | Why It Could Not Fail | Outcome |
|---|---|---|
| `test_test_site: a_role_with_powers_or_other_memberships_is_not_taken_over` | It never gave the role the application's role and another, so a check of membership alone would have passed | Strengthened in this pull request |
| `test_sign_in: a_user_made_inactive_is_signed_out_and_cannot_sign_in` | It asserted only a redirect, which passed while finding 2 was live | Two tests added in pull request 103 |
| `test_sign_in: five_failures_lock_the_name_for_15_minutes` | All five failures fell at one instant | The rule is tested with chosen times and a property test, pull request 103 |
| `test_security: every_write_refuses_a_forged_request` | Its client was never signed in, so the token was never what refused a request | Signed in as the application sees it, in this pull request. Shown to fail when the token check is turned off |
| `test_security: a_line_of_the_server_log...` | It said one line for each event and tested a record with no traceback; a traceback ran over many lines | Each event is now one line, a traceback included, in this pull request. ASVS 16.2.4 was recorded as Met on this claim |
| `test_exports: an_altered_export_fails_verification` | Its comment said a file was removed; none was | A test of its own, pull request 104 |

## Found While Fixing

An interval of 2,147,483,647 days stopped the programme page with a server error, and one in months was shown with the wrong reason. Not in the review. Fixed in pull request 105: such an interval is refused, and one already held cannot be calculated and comes first on the Fleet (`review-and-dates.md`).

## Where Nothing Was Found

The test site's handling of the owner's credentials, its SQL, the checks on its roles and the mark on its database. User-name enumeration, timing included; code reuse; session fixation; the 5-minute step between password and code; the forwarded address. Every record table has forced row-level security, its history trigger and the refusal of delete and truncate; every foreign key has its same-organisation trigger; the application's role holds no delete except on sessions; no function runs with its owner's rights. Organisation scoping of records fetched by identifier; the role on each view against the matrix; the import's all-or-nothing load, its limits and formula neutralising; secrets in an export.

The reviewer read `test_imports.py`, `test_reviews.py` and `test_review_checklist.py` only as far as their fixtures.

## What This Shows

- As on 19 November 2026, the tests written with the code missed the most serious defects. Findings 1, 2 and 4 each broke a rule written in `design-system/Decisions.md`.
- Three of the six weak tests were of sign-in and security, where a test that cannot fail is most costly.
- One risk was raised and not confirmed: the test site's first start counts the views in the new database, so a database that Render makes with an extension's views would be refused. It is to be watched at the next remake (Issue 100).
