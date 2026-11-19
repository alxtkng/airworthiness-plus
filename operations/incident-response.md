# Incident Response

Step 8 of private beta. Date: 19 November 2026. Assurance case C4.5.

An incident is anything that has harmed, or could harm, the records or the people who rely on them: the service down, records lost or wrong, someone seeing or changing what they should not, a secret exposed, a vulnerability being used.

Legal duties named below are from memory and are **To Be Checked** against the legislation and the Information Commissioner's Office guidance before this is relied on. The build session could not read them.

## Who

One person, Alex King, is the incident lead. There is no one else yet. Where this runbook says tell or decide, it is him. Who acts if he cannot be reached is not yet decided and is in the readiness review.

## First Hour

1. **Write it down as it happens.** Start an entry in the incident log (below): the time, what was seen, who reported it. Keep adding to it.
2. **Decide what kind it is.**

| Kind | Signs | First Action |
|---|---|---|
| Service down | Health alert; users cannot reach it | Look at the server and the service log. If the database is the fault, do not restart blindly: see Records Lost or Wrong |
| Records lost or wrong | `check_records` fails; a user reports a figure that changed; a backup fails its check | Stop writes: take the service offline. Keep the database as it is. Do not repair in place |
| Someone saw or changed what they should not | A refused-action or sign-in pattern in the access log; a report from a user; an export that was not expected | End the sessions of the accounts involved. Keep the logs |
| A secret exposed | A key or password in a commit, a log or a message | Replace it at once (`keys-and-secrets.md`). Assume it was used |
| A vulnerability reported or being used | A report under `SECURITY.md`; an alert | Follow `vulnerability-management.md`. If it is being used, treat it as the kind of harm it is causing as well |

3. **Protect the evidence.** Take a backup of the database as it is, and a copy of the server and proxy logs, before changing anything.
4. **Tell the organisations affected** that there is a problem and what they should do meanwhile: work from paper and their last export.

## Then

5. **Find the extent.** Which organisations, which records, from when to when. The history and the access log say who did what; an export's manifest SHA-256 says whether a file is the one the system made.
6. **Put it right.**
   - Service down: restore the service. If the server is lost, restore from backup onto a new one (`backup-and-restore.md`).
   - Records lost or wrong: restore into a new database, check it, state the highest certificate serial for each organisation, and tell each organisation the time of the backup so that it can enter again what came after. A wrong record is corrected by a new entry that supersedes it, never by changing history.
   - Access: remove the cause, end sessions, reset what was exposed.
7. **Notify.**
   - **Each organisation affected**, in writing, without delay: what happened, to which records, what was done, what they need to do. They hold the regulatory duties for their records and decide whether to tell the Civil Aviation Authority.
   - **Personal data.** If personal data was lost, altered or seen by someone who should not have seen it, the organisation whose data it is must be told without undue delay, because it is the controller and has its own duty to report. A breach that is a risk to people is reported to the Information Commissioner's Office within 72 hours of becoming aware of it (UK GDPR Article 33, To Be Checked). In private beta the company is the controller of the only personal data held, its own users', and the duty is its own.
8. **Record the problem in each organisation's Problem Log**, with the action and the solution (REQ-172).

## Afterwards

9. Within a week, write what happened, why, and what changes. Each change becomes an Issue. Update the hazard log or the threat model if either missed it.
10. If a restore was done, record it in `restore-tests/` as a real restore.

## The Incident Log

Kept by Alex King, outside the repository, because it names organisations and people. One entry for each incident:

| Field | |
|---|---|
| Reference | Year and number |
| Opened, Closed | Dates and times |
| Reported By | |
| What Happened | As it was understood at the time, then as it turned out |
| Organisations and Records Affected | |
| Personal Data Involved | Yes or No; whose |
| Actions | Each with its time |
| Who Was Told, and When | Organisations, the Information Commissioner's Office, anyone else |
| Cause | |
| Changes Made | With Issue numbers |

A summary with nothing private in it goes in the repository when the incident shows a fault in the product.

## Practice

The runbook is walked through once before public beta, with a made-up incident of each kind, and what it gets wrong is corrected.
