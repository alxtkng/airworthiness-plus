# Description of the System, for an Exposition

Step 8 of private beta. Date: 19 November 2026. REQ-175; AMC1 CAO.A.025; AMC1 CAO.A.100(f) point (d); OWASP ASVS 5.0, 13.1.1, 15.1.3.

An organisation that keeps its records in Airworthiness+ describes the system in its exposition and has it accepted by the Civil Aviation Authority. This is the text to start from. It describes the private beta slice as built. What CAP 562 Leaflet C-90 asks of such a description is **To Be Checked**: the leaflet could not be read in the build session.

## What It Is

A web application for the continuing airworthiness records of aircraft managed by a Part-CAO organisation: Part-ML aircraft in this version. It is used in a browser. Each organisation sees and changes its own records only.

## Main Functions

| Function | What It Does |
|---|---|
| Aircraft | The record of each aircraft; hours and cycles for the airframe, each engine and each propeller, entered as totals on a date and checked against the entries around them |
| Maintenance Programme | The tasks of each aircraft's programme with their limits in hours, cycles and calendar time; what is due and when, with the tolerance of the Minimum Inspection Programme where it applies; work done and its release to service |
| Airworthiness Directives | Each directive, the decision whether it applies to each aircraft with its basis, compliance, and what is next due |
| Maintenance Data | The data held, its revision, when its amendment status was last checked and when the next check is due |
| Airworthiness Review | The review against each point of ML.A.903, the certificate (CAA Form 15c), extensions, the copy to the Civil Aviation Authority, and the recency of review staff |
| Records | Import from paper or spreadsheet with a verification report; export of an aircraft's or the organisation's whole record; the Problem Log |

Every calculated figure can be opened to show the rule, the inputs and the source reference it came from.

## How Records Are Kept

- Nothing is deleted. A wrong entry is superseded by a new one, and both remain.
- Every change is written to a history by the database itself: who, when, what changed, the value before and after. The application cannot alter or remove history, and nor can the owner of the tables without it showing: each entry carries a hash chained to the one before.
- A certificate's serial is given by the database, once, and never reused, including after a restore from backup.
- Dates that matter under the regulation are United Kingdom dates with no time. The time of each entry is kept in Coordinated Universal Time.

## How Records Are Read

On the pages, by aircraft or by subject. By export at any time: a ZIP file of JSON and CSV holding every record and its whole history, which describes itself and can be checked against the system (`python -m django verify_export`). Nothing is held in a form only this software can read.

## Who Is Authorised

Each person has their own account. Sign-in needs a password and a code from an authenticator application. What each person may do is set by role:

| Role | In Short |
|---|---|
| Administrator | Manages users and the organisation record; does not change airworthiness records |
| Continuing Airworthiness Manager | Changes programmes, decides whether directives apply, records work and data, extends certificates, imports records |
| Airworthiness Review Staff | Carries out reviews and issues certificates, when on the review staff record and recent |
| Planning and Records | Adds aircraft, enters hours and cycles, records work, compliance and data |
| Read Only | Views |

The full matrix is in `design-system/Decisions.md`, Roles and Permissions. Every refused action is logged. How the organisation gives and removes access is in `user-administration.md`.

## Security

- Each organisation's records are separated in the database itself, not only in the pages.
- Connections are encrypted. The service asks nothing of any other site and sends nothing to one.
- Sign-in is locked after 5 failures for 15 minutes; a session ends after 30 minutes without use and after 12 hours whatever happens.
- The measures are assessed against OWASP ASVS 5.0 Level 2 (`assurance/asvs.md`) and the threat model (`architecture/threat-model.md`). An external penetration test comes before any customer's records are held.

## What the Service Connects To

Its own database, and nothing else. No user can make it connect anywhere. It sends no email. Backups leave the server encrypted, to storage elsewhere.

## What Takes Time or Resources

| Function | Why | How It Is Kept in Bounds |
|---|---|---|
| Sign-in | A password is checked by a deliberately slow calculation | A name is locked after 5 failures; rate limits at the reverse proxy |
| Import | Every row makes records | A file is at most 1 megabyte and 2,000 rows |
| Export of an organisation | Reads every record and its history | Run by a signed-in user with the right to export, and logged. Not otherwise limited yet |

## Backup

Daily, encrypted, kept away from the server, with a restore tested and recorded (`backup-and-restore.md`). The most that could be lost is 24 hours of entries; the service is restored by the next working day. Both are proposed figures.

## Training

Not yet written. What a user needs to know before using the system, and how the organisation records that they do, is to be written before public beta.

## Changes

A change that takes the system into a new function regulated by the Civil Aviation Authority is recorded as an architecture decision before it is released (`CONTRIBUTING.md`), so that the organisation can tell the authority that the system it described has changed.

## Before Relying on the System

CAP 562 Leaflet C-90 is the published basis for accepting computer records: a period of parallel running, a problem log, and the authority's written approval. The system records the start of the parallel run, the Problem Log and the approval's reference and date (Organisation page). The details of what the leaflet requires are To Be Checked against its current issue.
