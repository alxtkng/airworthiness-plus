# Readiness Review: Exit Gate for Private Beta

Date: 19 November 2026. Written by the build session for Alex King. Public beta does not start until he signs this off.

## Verdict

**Not ready for sign-off.** Added 20 November 2026: there is no existing server and no budget for one, so the items that need a server (deployment, backups running, the 17 server checks, the penetration test) cannot be met for now. Alex King has said this is expected, and the work carries on with sample data on the free test site.

As written on 19 November 2026: The private beta slice is built and tested. Three of the nine exit items are met, five are met in part, and one is not met. What remains is mostly outside the reach of a build session: the service is not deployed, no backup runs, the external test has not happened, and a number of decisions and confirmations are Alex King's to give.

| | Exit Item | State |
|---|---|---|
| 1 | Every requirement traced and tested | In Part |
| 2 | The golden cases pass, with an independent recompute | Met |
| 3 | No open high-severity defects or vulnerabilities | Met, as far as our own testing can say |
| 4 | A restore test passed | In Part: passed away from the server |
| 5 | The NCSC self-assessment completed | In Part |
| 6 | The ASVS level met | Not Met |
| 7 | Every hazard mitigated and verified, or accepted by Alex King | In Part |
| 8 | The threat model reviewed | Met, by its author; the independent review is the penetration test |
| 9 | Contract documents drafted | Met, as drafts for a solicitor |
| 10 | Every page meets WCAG 2.2 Level AA, with the manual pass done and the conformance report and statement completed | In Part: automated checks pass on every page; the manual pass is not done; SC 2.2.1 needs a decision |

## 1. Every Requirement Traced and Tested

**In Part.**

- Traced: 104 of 104. `requirements/traceability.csv`, checked by the pipeline on every change.
- Tested or inspected as its requirement asks: 93 of 104. Counted again on 19 November 2026 from the status of each row of the matrix, after those statuses were brought up to date with the interface as built.
- 877 tests pass (27 November 2026), on every change, against PostgreSQL in the pipeline. Ten of them run the table script in a real browser. There were 704 on 20 November 2026 and 814 when Phase 0 of the canvas build was merged on 24 November 2026.
- The code merged on 19 November 2026 was reviewed that day by a reviewer that did not write it. It found 15 defects and 4 tests that could not fail; all are fixed (`assurance/independent-verification/code-review-2026-11-19.md`). The code of 18 November 2026 and the test site's start-up code were reviewed the same way on 20 November 2026. It found 8 defects and 6 tests that could not fail; all are fixed (`assurance/independent-verification/code-review-2026-11-20.md`). Phase 0 of the canvas build was reviewed the same way on 24 November 2026, and its two calculations recomputed. The review found 14 defects and 6 groups of tests that could not fail; all are fixed, except that an existing second organisation on the test site keeps the first password it was given (`assurance/independent-verification/code-review-2026-11-24.md`, `personnel-and-alerts.md`).

The eleven that are not:

| Requirement | State | What It Needs |
|---|---|---|
| REQ-021 | The type rating is stored exactly as typed. It is not chosen from the SRG1782 list | The Civil Aviation Authority's list as data. For Alex King |
| REQ-103 | The last day of validity is taken as the anniversary of issue. No source says whether it is that day or the day before | A source (Issue 38). CAA Form 15c was read and does not settle it |
| REQ-112 | The review and its evidence are kept with the certificate. Files cannot be attached | Design of attachments |
| REQ-132 | The transport, cookie and header settings, the history and the least-privilege role are tested. ASVS Level 2 is not met in full, and there has been no penetration test | Section 6; Issue 40 |
| REQ-133 | Nothing is ever removed. The retention periods are not reported, and nothing can be removed when they end | A decision (see Questions) |
| REQ-150 to REQ-153 | Procedure, scripts and a restore test exist. Nothing runs on the server, and REQ-151 is not met: there is no storage away from the server | Deployment; Issue 27 |
| REQ-175 | The description of the system is written, with its training section and the flow of a record since 19 November 2026. What CAP 562 C-90 asks of it is taken from notes and unchecked. Written instructions for each role do not exist yet | CAP 562; instructions before public beta |
| REQ-196 | The pages use the tokens, the navigation and the table of the design system, and tests hold them to it. Sorting by a column, numbers aligned right and search within a long table were built on 19 November 2026. Filtering a table by facets, the summary strip and icons beside sidebar items are not built | Choices the design system does not make: the facets, what a summary counts, and the icons. |

Three requirements still rest on a claim with no confirmed source: REQ-058, REQ-103 and REQ-110, the last two because CAP 562 is not in the Regulatory Library and could not be read.

## 2. The Golden Cases Pass, With an Independent Recompute

**Met.**

- Golden and property tests: 165, all passing, including the whole sample compared with `SampleData.md` (`tests/test_sample_seed.py`, `assurance/dogfooding.md`).
- Each calculation was recomputed by a separate agent that had not seen the code, the tests or the repository, working by hand from the quoted rules. Records in `assurance/independent-verification/`: intervals, review and dates, tolerance, utilisation, programme, recency. Every case agreed, and the findings each raised were fixed in the same change.

Carried with it: the readings of the regulation that those records mark for Alex King to confirm. The arithmetic is verified; a few of the rules it implements are our reading.

## 3. No Open High-Severity Defects or Vulnerabilities

**Met, as far as our own testing can say.**

- Open defect Issues: none. Issue 69 (seven ASVS requirements met in part) is settled: five met, two accepted for private beta. Issue 71 (differences found by dogfooding) is settled: D-3 and D-6 fixed, D-4 and D-5 decided.
- `pip-audit` passes on every change. No vulnerability report has been received.
- Defects found during the build were fixed as found, among them: a server error on a sign-in with no user name; work from before the records began shown as entered late; a certificate serial that would have repeated after a restore; a review that could be issued by someone other than its reviewer.

This cannot be stronger than it is: nobody outside has tried to break the system. That is item 6 and the penetration test.

## 4. A Restore Test Passed

**In Part.**

`operations/restore-tests/2026-11-19.md`: passed. The records came back with an identical history fingerprint and their protections intact, a backup could not be read without its key, and the next certificate serial did not repeat.

It was run in the build environment. It has not been run on the server, where no backup yet exists.

## 5. The NCSC Self-Assessment Completed

**In Part.** `assurance/ncsc-self-assessment.md`, assessed again today: 5 of 14 principles Met, 9 In Progress, none Not Started. Most of the nine wait on deployment and on there being customers. Two wait on Alex King: confirmation of two-factor sign-in on the GitHub account and of who can reach the server; and switching on GitHub's dependency alerts, secret scanning and push protection.

## 6. The ASVS Level Met

**Not Met.** `assurance/asvs.md`: OWASP ASVS 5.0 Level 2, 253 requirements.

| Result | Requirements |
|---|---|
| Met | 141 |
| Not Applicable | 89 |
| To Be Verified at Deployment | 17 |
| Partly Met | 4 |
| Not Met | 2 |

- The 17 are checks of the server and the reverse proxy, listed in `operations/deployment.md`.
- Of the 6 not met or met in part, two were accepted for private beta on 19 November 2026 after Alex King asked us to decide (a full check against breached passwords, and passkeys in place of codes; `design-system/Decisions.md`), and four are to be settled before customer data: a vault for secrets, logs kept apart from the server, encryption of second-factor keys with a period for the access log, and a named key management standard. Issue 69 has no item left that waits on a decision.

The level itself, Level 2, is our choice and is for Alex King to confirm.

## 7. Every Hazard Mitigated and Verified, or Accepted

**In Part.** `assurance/hazard-log.md`. No hazard is Open.

| State | Hazards |
|---|---|
| Verified | H-002, H-004, H-005, H-006, H-007, H-012 |
| Mitigated, not yet Verified | H-001, H-003, H-008, H-009, H-010, H-011, H-013, H-014 |
| Accepted | None |

What keeps each of the eight from Verified is stated in the log: readings of the regulation awaiting Alex King's confirmation (H-001, H-010, H-011, H-013), backups not yet running (H-003, H-009), no real records loaded (H-008), and a route for users to challenge a figure in real use (H-014). Accepting any remaining risk is his.

## 8. The Threat Model Reviewed

**Met, by its author.** `architecture/threat-model.md` was reviewed in full today. Every planned test, T-SEC-001 to T-SEC-020, exists. The demonstrations that need the server are not yet shown. A review by someone who did not write it is the penetration test: its scope is written (`assurance/penetration-test-scope.md`, Issue 40) and it has not been commissioned.

## 9. Contract Documents Drafted

**Met, as drafts.** `operations/contracts/`: data processing agreement, service level, data export on exit. They are for a solicitor and are not legal advice. Writing them found one thing the product cannot yet do: remove an organisation's data when it leaves.

## What Was Built

For the record, the slice named in the plan, each part with its tests and its entry in `design-system/Decisions.md`:

organisation and access, with roles, two-factor sign-in, users and an access log; aircraft and their hours and cycles; the maintenance programme and what is due, with tolerance; airworthiness directives; maintenance data; the airworthiness review, CAA Form 15c certificates, extensions and review staff recency; import with a verification report; export with verification; the Problem Log, parallel run and written approval; the interface from the design system; the service image; backup, restore and the check of records; the sample organisation as a seed.

## What Only Alex King Can Do

In rough order.

1. **Rent a server, when there is a budget.** Corrected 20 November 2026: this asked for access to the server. There is no existing server; his search that day found none, and there is no budget for one now. Until there is a paid server this review stays Not Ready for Sign-Off, and that is expected. The only hosting is the free test site on Render, with the sample (`operations/test-site.md`).
2. **Paid services: none for now.** Corrected 20 November 2026: there is no budget, so backup storage, the penetration test (Issue 40) and Cyber Essentials Plus all wait. `operations/backup-storage-options.md` is kept for when a server is rented. Before 20 December 2026, remake the test site's free database (Issue 100).
3. **Confirm the readings of the regulation** listed under Questions. On 19 November 2026 he asked us to decide them; each is kept as built and recorded as ours in `design-system/Decisions.md`. That is a decision to proceed, not his confirmation of the reading, so the four hazards stay Mitigated and are not marked Verified.
4. **Confirm Level 2**, and the two ASVS items accepted for private beta on his instruction to decide (breached passwords, passkeys). The other five items of Issue 69 were met on 19 November 2026.
5. **Confirm the operating figures**: recovery point 24 hours, recovery time the next working day, how long backups and logs are kept.
6. **Say who acts when he is away.** One person receives every alert and leads every incident.
7. **Have the data protection documents and the contract drafts reviewed** by someone qualified, and fill in the company's details.
8. **Decide whether real records may be loaded**, and on what terms (Issue 28).
9. **Switch on, in the repository's settings**: dependency alerts, secret scanning and push protection. Confirm two-factor sign-in on the GitHub account.
10. **The decisions still open from before**: the licence for the open data standard (Issue 25) and Issues 29 to 36.

## Questions for Alex King

Each is recorded where it arose; this is the list in one place.

### Readings of the Regulation

| Question | What the System Does Now | Where |
|---|---|---|
| ML.A.302(d)(1): may the tolerance be used at two inspections in a row? | Does not refuse a second. Says when it was used, and at a second use in a row adds what GM1 ML.A.302(c)(3) says | `independent-verification/tolerance.md` |
| May a programme based on the design approval holder's instructions carry a tolerance stated in those instructions? | Refuses any tolerance outside the Minimum Inspection Programme | The same |
| Do the hours and the calendar tolerance each apply to their own limit? | Yes | The same |
| The last day of validity when a review does not keep the pattern: the anniversary, or the day before? | The anniversary | REQ-103, Issue 38 |
| Are the 90 days and the 30 days counted to include the day of expiry? | As in `independent-verification/review-and-dates.md` | The same |
| Is a calendar limit with 0 days remaining Due or Overdue? | Due | `independent-verification/intervals.md` |
| Does the day 12 months after a review still count for recency? | Yes | `independent-verification/recency.md` |
| How does an organisation count 6 months in 2 years, and when does the figure go stale? | A figure the organisation records, with its date | The same |
| Who may extend a certificate within the organisation? | The Continuing Airworthiness Manager and Airworthiness Review Staff | `Decisions.md`, Roles and Permissions |
| "At least annually" for the programme review: 12 months to the day? | Yes | `independent-verification/programme.md` |

### The Sample

| Question | Where |
|---|---|
| Are G-BXYZ and G-FMNO on the Minimum Inspection Programme, and G-ABCD and G-CDEF on the design approval holder's instructions? | `SampleData.md` |
| Lucy Grant's review of G-BXYZ taken as 2 August 2026, and the other reviewer's last review as 2 December 2025 | The same |
| 220 Hours in the sample, 220.0 Hours on the page | `dogfooding.md`, D-1 |

### The Product

| Question | What the System Does Now |
|---|---|
| What are hours for each counter, flight time or a meter reading, and what is a cycle? | Stores what is entered, as totals |
| Does a second person confirm an unusual increase in hours? | The person entering confirms it |
| The limits on an entry: 24 hours a day refused, more than 10.0 hours or 100 cycles a day confirmed | Ours |
| Due Soon at 30 days, 10.0 hours, 10 cycles, adjustable for each organisation | Ours |
| The certificate reference, UK.CAO.[Number]-ARC-0001 | Ours |
| An import's hours and cycles must be checked by a second person. A one-person organisation cannot complete that | Enforced |
| Which records a real migration needs beyond aircraft, directive status and certificates | Three kinds of file |
| A certificate the organisation's own review staff issued before these records is recorded as theirs only if dated no later than the person's last review before these records, which the Administrator states and which is never after the day the person was recorded as review staff. Is that the right limit? | Ours; built 19 November 2026 (Issue 71, D-3) |
| A first password works for 7 days. A change to how someone signs in needs a sign-in within the last 5 minutes or a code | Ours; built 19 November 2026 (Issue 69) |
| A one-time code is good for 30 seconds only. Workable in practice? | Enforced, to meet ASVS 6.5.5 |
| Authenticator codes now, passkeys before public beta | Decided as ours, 19 November 2026 |
| An Administrator can reset both factors of another user and so sign in as them. It is logged, not prevented | As stated |
| A failed sign-in logs the user name as typed, which could be a password typed in the wrong box | As stated |

### Records and Data Protection

| Question |
|---|
| Nothing is ever deleted. How long is the access log kept, and how is anything removed when its period ends or an organisation leaves, given that the application cannot delete? |
| Where are the server and the backup storage, by country? There is no server and no backup storage. The test site is on Render in Frankfurt, Germany, and holds the sample only; its access log does record the network address of anyone who signs in or tries to |
| Is the company registered with the Information Commissioner's Office? |
| What does CAP 562 Leaflet C-90 say, in its current issue, about the description of the system, the parallel run and the problem log? It could not be read in the build session |

## Sign-Off

| | Name | Date |
|---|---|---|
| Reviewed and accepted for public beta | | |
