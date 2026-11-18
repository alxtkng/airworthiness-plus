# Hazard Log

Hazards caused by the software itself. The method is the one an organisation's safety management system uses: identify the hazard, assess the risk, mitigate, verify the mitigation, and keep the entry.

Entries are never removed. A closed hazard stays with its status changed.

## Scales

Severity is the worst credible effect on airworthiness.

| Severity | Meaning |
|---|---|
| High | An aircraft could fly outside its approved limits: an overrun inspection, life limit or directive, or an invalid certificate |
| Medium | Records are wrong or incomplete but the error would be caught by a later control before flight outside limits |
| Low | Inconvenience or rework, no effect on airworthiness |

Likelihood is assessed before mitigation, for software built without the listed controls.

| Likelihood | Meaning |
|---|---|
| Likely | Expected to occur in ordinary use |
| Possible | Could occur in foreseeable conditions |
| Unlikely | Needs an unusual combination of conditions |

Status: Open (mitigation not built), Mitigated (built, not yet verified), Verified (evidence recorded), Accepted (Alex King accepts the remaining risk, with date).

Owner of every hazard in private beta: Alex King.

## Log

| Identifier | Hazard | Cause | Effect on Airworthiness | Severity | Likelihood | Mitigations | Verification | Owner | Status |
|---|---|---|---|---|---|---|---|---|---|
| H-001 | Wrong next-due date or remaining hours | Interval arithmetic error; wrong governing limit chosen among hours, calendar time and cycles; tolerance applied wrongly; stale utilisation figures | Inspection or component life overrun (ML.A.302) | High | Possible | Rules as numbered requirements with sources; golden cases; property-based tests; independent recompute; date the utilisation figures were last updated shown beside every remaining figure; a tolerance never moves a due point, is accepted only for a Minimum Inspection Programme inspection and is refused for a directive, an airworthiness limitation or a life limit (REQ-048, REQ-049, REQ-056) | Assurance case C1.1 to C1.5 | Alex King | Open |
| H-002 | Airworthiness directive wrongly marked not applicable | Applicability matched on wrong type, serial range or configuration; default of not applicable; bulk action | Mandatory action not carried out (ML.A.301, ML.A.303, To Be Checked against the UK text) | High | Possible | No default: applicability is an explicit recorded decision with the person, date and reason; not applicable needs a stated basis; decisions are append-only and reviewable; repetitive intervals feed the same next-due engine as H-001 | Tests on applicability decisions; 100% check of directive data on migration (CAP 562 C-90) | Alex King | Open |
| H-003 | Records lost or silently altered | Update or delete in place; failed write reported as success; direct database change; storage fault | The record no longer shows the aircraft's true status; compliance cannot be demonstrated (ML.A.305, CAO.A.090) | High | Possible | Append-only history, no delete path, and database permissions and triggers that deny update and delete on history (built and tested against the database 18 November 2026, ADR-0002); writes confirmed only after commit; backups; export | Assurance case C2.1 to C2.3, C4 | Alex King | Open |
| H-004 | One organisation sees or changes another's data | Missing organisation filter in a query; identifier guessed in an address; shared cache; role error | Breach of AMC1 CAO.A.100(f) point (d)(2); another organisation's records altered; UK GDPR breach | High | Possible | Organisation scoping in the data layer (built and tested against the database 18 November 2026, ADR-0002); every endpoint tested for cross-organisation access; non-guessable identifiers; external penetration test | Assurance case C3.1, C3.2, C3.5 | Alex King | Open |
| H-005 | Superseded manual revision shown as current | Amendment check not done or not recorded; new revision entered without superseding the old; customer data past its confirmation | Work done to out-of-date data (M.A.401, ML.A.401, AMC1 145.A.45(g)) | High | Possible | Revision supersession as an event; one current revision for each set of data; date last checked always shown; overdue check flagged; customer data shows the basis and date of its amendment status | Assurance case C7.1 to C7.4 | Alex King | Open |
| H-006 | Time zone or date boundary error | Timestamps in Coordinated Universal Time shown or compared as dates; British Summer Time change; leap year; month end; off-by-one in day counts | Due date or validity date one day wrong; a certificate treated as valid after expiry | High | Likely | One explicit rule: regulatory periods counted in UK local dates; date type separate from timestamp type; boundary tests; exact day count case (18 November to 6 December is 18 days) | Assurance case C1.6; boundary tests | Alex King | Open |
| H-007 | Certificate generated with a duplicate or wrong serial | Serial allocated in the browser; concurrent requests; serial reused after a void; restore from backup reusing numbers | Two certificates with one identity; a certificate that cannot be traced (CAP 562 C-90) | Medium | Possible | Server-allocated serials from a database sequence with a uniqueness constraint; voided serials kept, never reused; restore procedure checks the sequence against issued certificates | Assurance case C2.4; concurrency tests; restore test | Alex King | Open |
| H-008 | Migration errors from paper or spreadsheet records | Transcription error; unit or date format misread; missing history; hours and cycles swapped | The system starts from a wrong baseline: wrong totals, missed directive or life limit | High | Likely | Migration only through a verified import with a verification report; up to 100% check of directive and maintenance review data (CAP 562 C-90); second-person check of totals; aircraft held in Transfer In until records are complete (Decisions.md, Interface); parallel run in public beta | Assurance case C2.7; Step 9 comparison by hand | Alex King | Open |
| H-009 | Backups fail and were never tested by restoring | Backup job fails silently; backup incomplete or unreadable; backup held only on the same server; key lost | Records lost with the server (145.A.45(e), CAO.A.090) | High | Possible | Daily backups held off the server; alert on failure or absence; documented restore test repeated on a schedule; backup encryption key held separately | Assurance case C4.1 to C4.4 | Alex King | Open |
| H-010 | Airworthiness review certificate validity or anniversary miscalculated | Early review window boundary wrong (90 against 91 days); extension counted wrongly; copy-to-CAA date wrong | Aircraft flown without a valid certificate, or certificate issued with a wrong expiry (ML.A.901 to ML.A.903, clause references To Be Checked) | High | Possible | Rules as requirements; golden cases G-EJKL and G-CDEF; boundary tests at 90 and 91 days; independent recompute | Assurance case C1.3, C1.5 | Alex King | Open |
| H-011 | Hours or cycles entered wrongly and accepted | Decimal slip; hours entered as cycles; reading lower than the last; entry against the wrong aircraft | Remaining time overstated, leading to H-001 | High | Likely | Plausibility checks (not lower than the last reading, unusual jump needs confirmation); registration shown on every entry screen; corrections are new entries, the wrong one stays in history | Tests on entry validation | Alex King | Open |
| H-012 | Export of an aircraft record is incomplete | Export omits history, superseded entries or attachments; new record type not added to the export | Records handed to an owner or new organisation are incomplete on transfer (ML.A.305, clause To Be Checked) | Medium | Possible | Export built from the same history as the display; test compares export against database for every record type; a new record type fails the build until it is exported | Assurance case C2.6 | Alex King | Open |
| H-013 | Review staff or certifying staff shown as current when lapsed | Recency calculation error; record not updated | Review carried out or certificate issued by a person not entitled to (CAO.A.045) | High | Unlikely | Recency as a requirement with golden case (review staff recency lapses 2 December 2026); certificate issue blocked for lapsed staff | Tests; independent recompute | Alex King | Open |
| H-014 | User trusts the software over the source records | Software presented as authoritative before verification; no route to challenge a figure | An error in H-001 to H-013 goes unchallenged | Medium | Possible | Every calculated figure shows its rule, inputs and source reference on expansion; private beta is internal only; public beta is a parallel run with a problem log | Interface review; readiness review | Alex King | Open |

## Review

The log is reviewed at each step's pull request and in full at the readiness review. Every hazard must be Verified, or Accepted by Alex King, before public beta.
