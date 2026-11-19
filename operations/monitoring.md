# Monitoring, Alerting and Logs

Step 8 of private beta. Date: 19 November 2026. REQ-152; assurance case C4.4; OWASP ASVS 5.0, 16.1.1, 16.2.3, 16.4.3.

## Status

Written, not yet running: there is no deployed service to watch. Where the checks run from, and whether a paid monitoring service is used, are Alex King's decisions (Issue 27).

## What Is Watched

| What | How It Is Known | Alert When | Who Is Told |
|---|---|---|---|
| The service is up | `/health/` asked every minute from outside the server | Two answers in a row are not OK | Alex King |
| The database answers | The same page: it says Unavailable when the database does not | As above | Alex King |
| A backup was taken | `check_backup_age.sh <directory> 26`, run from somewhere other than the server | The newest backup is more than 26 hours old, missing, or fails its checksum | Alex King |
| The records agree with their history | `check_records`, as the backup role, daily after the backup | It ends with an error | Alex King |
| The certificate is about to run out | The date in the certificate, checked daily from outside | Fewer than 14 days remain | Alex King |
| Disk space on the server | The server's own measure | Less than 20% free | Alex King |
| Errors in the service | The server log, lines at level ERROR | Any | Alex King, in a daily summary; at once if repeated |
| Sign-in under attack | Entries of Sign-In Refused While Locked in the access log | More than 10 in an hour | Alex King |
| A vulnerable dependency | `pip-audit` in the pipeline, and GitHub's alerts | Any | Alex King (`vulnerability-management.md`) |

The numbers are ours and are tuned once the service has run.

One person receives every alert. Who is told when that person is away is a question for Alex King, and is in the readiness review.

## Logs: What Is Kept, Where, and for How Long

| Log | What Is In It | Where It Is Kept | Who Can Read It | Kept For |
|---|---|---|---|---|
| History | Every change to every record: who, when, what, before and after, with a chained hash | The database | Users of the organisation, through the records; the backup role | As long as the record (REQ-133). Never changed or removed |
| Access log | Sign-ins, failed sign-ins, locks, sign-outs, changes of password and second factor, ended sessions, refused actions, exports. User name, time, network address | The database | The organisation's Administrator, on the Access Log page; the organisation, in its export; the backup role | Not yet decided. See `data-protection/record-of-processing.md`: it holds personal data, and at present nothing removes it |
| Server log | One line for each request (time, address, method, path, status, size, browser) and one for each warning or error | The server's log collection for the container | Whoever administers the server | Proposed: 90 days |
| Reverse proxy log | Requests as the proxy saw them | The proxy | Whoever administers the server | Proposed: 90 days |
| Pipeline log | Each build and its checks | GitHub | Anyone who can read the repository | GitHub's own period |

No log holds a password, a one-time code, a session identifier or the body of a request. The application writes to no other file or service.

All times are Coordinated Universal Time. The server's clock is kept right by the hosting provider's time service, which is checked at first deployment.

## What Is Not Yet Met

- **Logs kept apart from the server** (ASVS 16.4.3). The history and the access log leave the server once a day, in the backup. The server log and the proxy log stay on the one server, so someone who took the server could remove them. Sending them elsewhere as they are written needs a second system. Not proposed for private beta; to be decided before customer data.
- **Someone to tell when Alex King is away.**
