# Requirements

Scope: the private beta slice, the Part-CAO core loop for Part-ML aircraft (`prompts/private-beta.md`, Part 5).

Each requirement has an identifier, the requirement in plain words, its source, its priority and how it is verified. Identifiers are never reused. A withdrawn requirement stays in this file, marked Withdrawn.

## Reading the Source Column

- **(R)** the reference is in the record: `design-system/Decisions.md`, Regulation Facts or National Regime.
- **(N)** the reference comes from the research notes in `research/`, which were made from the European Union Aviation Safety Agency text or from CAP 562. It is To Be Checked against UK Regulation (EU) No 1321/2014, CAA edition of September 2026, before the requirement is relied on (Issue #38).
- **(D)** a design decision of this project, with where it is recorded.
- No requirement is verified until every (N) reference on it has been confirmed and changed to (R).
- References marked "confirmed 18 November 2026" were read in the UK text in the Civil Aviation Authority Regulatory Library on that date.

Priority: Must (the slice is not complete without it) or Should.

Verification: Test (automated), Golden (a fixed worked case from `design-system/SampleData.md`, expected result worked by hand), Independent (recomputed by a second party who has not seen the implementation), Inspection (a person checks a document or screen), Demonstration (a recorded procedure, such as a restore).

## 1. Organisation and Access

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-001 | The system holds one record for each organisation: name, approval type, approval reference (UK.CAO.[Number]), privileges and scope of work | SampleData.md, Organisation; CAO.A.095 (N) | Must | Test |
| REQ-002 | Every record belongs to exactly one organisation | AMC CAO.A.090, AMC CAMO.A.220 (R); the notes place the software conditions in AMC1 CAO.A.100(f) (N) | Must | Test |
| REQ-003 | A user can read only the records of their own organisation. This is enforced in the data layer, so a fault in the interface cannot expose another organisation's data | AMC CAO.A.090, AMC CAMO.A.220 (R); (D) brief Step 4 | Must | Test: every endpoint tried against another organisation's records |
| REQ-004 | Only users who belong to the organisation can enter or change its data. There is no support or administrator account that can write to a customer organisation's records | AMC CAO.A.090, AMC CAMO.A.220 (R) | Must | Test |
| REQ-005 | Every user has their own named account. There are no shared accounts | CAP 562 C-90 (R); (N) research/cap562/03.md 6.3 | Must | Test, Inspection |
| REQ-006 | Write access is by role. Each role's permissions are listed in one role matrix, and an action outside the matrix is refused | CAP 562 C-90 (R) | Must | Test: every action against every role |
| REQ-007 | The roles in the slice are Administrator, Continuing Airworthiness Manager, Airworthiness Review Staff, Planning and Records, and Read Only | (D) derived from SampleData.md, People. Role matrix to be recorded in Decisions.md | Must | Inspection |
| REQ-008 | Sign-in requires a second factor | (D) threat model, account takeover; level set in `assurance/asvs.md` | Must | Test |
| REQ-009 | Every sign-in, failed sign-in, refused action and change of role is logged with the user, the time and the action | CAP 562 C-90 (R); 145.A.45(e) (R, adopted) | Must | Test |
| REQ-010 | A user who leaves is deactivated, not deleted. Their past entries keep their name | (D) brief Step 4, nothing deleted; CAO.A.045(e) (R) | Must | Test |

## 2. Aircraft

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-020 | The aircraft record holds: Aircraft Registration, type rating, serial number, owner, airframe hours, cycles, and the hours and cycles of each engine and propeller | Brief Part 5; ML.A.305(b), (c) (R, confirmed 18 November 2026); ML.A.903(a)(1) (R, confirmed 18 November 2026) | Must | Test |
| REQ-021 | The type rating is chosen from SRG1782 (Version 16, 11 August 2026) and stored and shown verbatim, never re-cased or shortened | Decisions.md, Product | Must | Test: stored value equals source value byte for byte |
| REQ-022 | Every aircraft record carries a regime: Part 21 or Non-Part 21. The slice calculates for Part 21 aircraft under Part-ML only; a Non-Part 21 aircraft can be recorded but shows that its calculations are not yet supported | Decisions.md, National Regime | Must | Test |
| REQ-023 | Aircraft status is Serviceable or Unserviceable. Unserviceable carries a reason and a date | Decisions.md, Interface | Must | Test |
| REQ-024 | Hours and cycles are entered as dated utilisation entries. Each entry is kept; the current total is the latest entry | ML.A.305 (R); CAP 562 C-90 (R) | Must | Test |
| REQ-025 | A utilisation entry lower than the previous one is refused. An unusually large increase needs confirmation. A correction is a new entry that supersedes the wrong one, which stays in the history | Hazard H-011; CAP 562 C-90 (R) | Must | Test |
| REQ-026 | Every screen that takes an entry for an aircraft shows its Aircraft Registration | Hazard H-011 | Must | Inspection |
| REQ-027 | An aircraft being transferred in is held as Transfer In, outside the Fleet, until its records are complete. No due item is shown as calculated for it until then | Decisions.md, Interface; hazard H-008 | Must | Test |
| REQ-028 | Hours are held and shown to one decimal place. Arithmetic on hours is exact decimal arithmetic, never binary floating point | Writing.md, Dates, Hours and Numbers; hazard H-001 | Must | Test, property-based |

## 3. Maintenance Programme

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-040 | Each aircraft has one maintenance programme, which records its basis: the design approval holder's instructions or the Minimum Inspection Programme | ML.A.302 (R); ML.A.302(d) (N) | Must | Test |
| REQ-041 | A programme task has an interval in hours, calendar time, cycles, or any combination | Brief Part 5; ML.A.302 (R) | Must | Test |
| REQ-042 | For each task the system calculates the next due point for each limit it has: a due date, due hours and due cycles | ML.A.302 (R) | Must | Test, Golden, Independent |
| REQ-043 | Whichever limit comes first governs. The system shows which limit governs and the remaining amount in that limit's unit | Brief Part 5; AMC ML.A.302 (R, Minimum Inspection Programme: annual or 100 hours, whichever first) | Must | Golden (G-BXYZ, 100-Hour or Annual Check, 41.0 hours), property-based, Independent |
| REQ-044 | Hours and cycles limits are ranked against calendar limits by projecting them to a date with the aircraft's planning utilisation, rounded down to whole days. Limits on the same day are shown together. With no planning utilisation recorded, no limit is ranked above another and every limit is shown. The projection is never used to decide that a task is not yet due | Decisions.md, Interface (D, decided 18 November 2026); hazard H-001 | Must | Test |
| REQ-045 | Remaining hours are due hours minus current hours. Golden: G-ABCD 50-Hour Check, 12.4 hours | ML.A.302 (R); SampleData.md, Fleet | Must | Golden, Independent |
| REQ-046 | Remaining days are an exact count of UK local dates from today to the due date. From 18 November 2026 to 6 December 2026 is 18 days. Golden: G-FMNO Annual Check, 78 days | Decisions.md, Interface | Must | Golden, Independent, boundary tests (leap years, month ends, British Summer Time changes) |
| REQ-047 | A calendar interval in months lands on the same day of the month, or the last day of a shorter month. The rule is stated once and used everywhere | Decisions.md, Interface (D, decided 18 November 2026). Our rule, not the regulation's | Must | Test, property-based |
| REQ-048 | For the Minimum Inspection Programme the tolerance is 1 month or 10 hours, and when the tolerance is used the next interval runs from when the task was done | AMC ML.A.302 (R) | Must | Test, Independent |
| REQ-049 | A tolerance or permitted variation is never applied to an airworthiness directive, an airworthiness limitation or a life limit | CAP 562 5-30, 5-40 (R, national regime); Part-ML equivalent To Be Checked | Must | Test |
| REQ-050 | Each accomplishment of a task is recorded with the date, hours and cycles at accomplishment and the release to service reference. Earlier accomplishments are kept | ML.A.305 (R); CAP 562 C-90 (R) | Must | Test |
| REQ-051 | A certificate of release to service must be in the records within 30 days of the work being completed. The system shows the deadline and flags a completed task with no release recorded. Golden: G-ABCD tyre replaced 22 October 2026, deadline 21 November 2026 | ML.A.305(a) (R, confirmed 18 November 2026): not later than 30 days after the day of completion; M.A.305 (R) | Must | Golden, Independent |
| REQ-052 | Pilot-owner maintenance is recorded with the date the pilot-owner told the organisation, and flagged when that is more than 30 days after the task | Appendix I to Part-ML (R); the notes cite ML.A.305(a) (N) | Should | Test |
| REQ-053 | The programme is reviewed at least annually. The system shows the date of the last review and when the next is due | ML.A.302 (R); ML.A.302(c)(9) (N) | Must | Test |
| REQ-054 | Stale utilisation is visible: every remaining-hours or remaining-cycles figure shows the date of the utilisation entry it was calculated from | Hazard H-001 | Must | Inspection, Test |
| REQ-055 | An item is Due Soon (amber) inside a threshold and Overdue (red) only when past due. The defaults are 30 days, 10.0 hours or 10 cycles, adjustable for each organisation; a regulatory deadline of 30 days or fewer is Due Soon from the day it starts | Decisions.md, Interface (D, decided 18 November 2026) | Must | Test |

## 4. Airworthiness Directives

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-060 | An airworthiness directive record holds its number, issuing authority, subject, effective date, revision and what it supersedes | M.A.401(b) (R, directives are applicable maintenance data); ML.A.305 (R) | Must | Test |
| REQ-061 | For each aircraft and each directive that could affect its type, engine, propeller or equipment, an applicability decision is recorded: Applicable or Not Applicable, with the basis, the person and the date | ML.A.903(a)(5) (R, confirmed 18 November 2026); hazard H-002 | Must | Test |
| REQ-062 | There is no default applicability. A directive with no decision shows as Applicability to Assess and is flagged | Hazard H-002 | Must | Test |
| REQ-063 | Not Applicable cannot be set in bulk, and needs a stated basis | Hazard H-002 | Must | Test |
| REQ-064 | A compliance record holds the method, date, hours, cycles and release to service reference | ML.A.305 (R) | Must | Test |
| REQ-065 | A repetitive directive has an interval in hours, calendar time or cycles, and its next due is calculated by the same rules as a programme task, with no tolerance | REQ-042 to REQ-047, REQ-049 | Must | Test, Independent |
| REQ-066 | A terminating action ends the repetition and never erases the earlier repetitive inspection records | CAP 562 C-90 (R); (N) research/cap562/03.md | Must | Test |
| REQ-067 | The system produces the current directive status of each aircraft: every directive assessed, its applicability, compliance and next due | ML.A.305(d)(1), (h)(5) (R, confirmed 18 November 2026); ML.A.903(a)(5) (R, confirmed 18 November 2026) | Must | Test, Golden |
| REQ-068 | A superseded directive stays in the record marked superseded, with the directive that replaced it | (D) brief Step 4, nothing deleted | Must | Test |

## 5. Maintenance Data

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-080 | Each set of maintenance data held is recorded with its title, author, the types or ratings it applies to, its revision and revision date | M.A.401, ML.A.401, CAO.A.055 (R, Decisions.md, Navigation) | Must | Test |
| REQ-081 | Each set records its kind: Civil Aviation Authority requirement, airworthiness directive, instructions for continued airworthiness from a type or supplementary type certificate holder, component manufacturer's instructions | M.A.401(b) (R) | Must | Test |
| REQ-082 | Each set records its amendment service and the date its amendment status was last checked, with the person who checked | AMC M.A.401(c) 5, AMC1 145.A.45(g) (R) | Must | Test |
| REQ-083 | Each set has a date by which the next amendment check is due. An overdue check is flagged. Golden: Grob G 115 manual, amendment to check by 20 November 2026 | AMC M.A.401(c) 5, AMC1 145.A.45(g) (R); SampleData.md, Documentation | Must | Golden |
| REQ-084 | Data carrying mandatory instructions or airworthiness limitations is marked, and its overdue checks are shown first | AMC M.A.401(c) 5, AMC1 145.A.45(g) (R) | Must | Test |
| REQ-085 | A new revision supersedes the old one. Exactly one revision of a set is current; a superseded revision is shown as superseded wherever it appears and cannot be selected as current | Hazard H-005; M.A.401, ML.A.401 (R) | Must | Test |
| REQ-086 | Customer-provided data is recorded with who provided it and how its amendment status is shown: written confirmation, the work order, or the customer's amendment list, with the date. Golden: G-BXYZ, confirmed current in writing 2 June 2026 | 145.A.45(a)(g), CAO.A.055(a), CAO.A.080 (R) | Must | Golden |
| REQ-087 | Customer-provided data is held only while the work is in progress or for the length of the contract. When that ends it is marked No Longer Held with the date; the record of having held it stays | CAO.A.055(a), CAO.A.080 (R); CAO.A.090(b) (N) | Must | Test |
| REQ-088 | Data needed for an aircraft in the fleet but not held is shown as Not Held. Golden: Piper PA-38 Series manual, needed for G-HKLM | AMC1 CAO.A.055 (R); SampleData.md, Documentation | Must | Golden |
| REQ-089 | The system can answer, for an aircraft, whether the data for its type is held and current, with the date last checked | AMC1 CAO.A.055 (R) | Must | Test |

## 6. Airworthiness Review

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-100 | Each aircraft shows the date its airworthiness review certificate is valid to and the exact days remaining. Golden: G-EJKL, 6 December 2026, 18 days on 18 November 2026 | ML.A.901 (R); Decisions.md, Interface | Must | Golden, Independent |
| REQ-101 | An airworthiness review certificate is valid for 1 year | ML.A.901(a) (R, confirmed 18 November 2026) | Must | Test, Independent |
| REQ-102 | A review done in the 90 days before expiry keeps the pattern: the new certificate is valid to 1 year after the previous expiry. A review done 91 or more days before expiry does not. Golden: G-CDEF reviewed 11 November 2026, valid to 2 December 2027 | ML.A.903(d) (R, confirmed 18 November 2026) | Must | Golden, boundary tests at 90 and 91 days, Independent |
| REQ-103 | The exact last day of validity for a review that does not keep the pattern (the anniversary of issue, or the day before) follows the UK text and CAA Form 15c | To Be Checked: no source in the record | Must | Golden once sourced |
| REQ-104 | A certificate can be extended at most twice in a row, for 1 year each time, and only in a controlled environment. The system counts extensions and refuses a third | ML.A.901(c) (R, confirmed 18 November 2026) | Must | Test, Independent |
| REQ-105 | Before an extension the system records confirmation of each controlled environment condition: continuously managed by the organisation for the previous 12 months, maintained by approved organisations, and no evidence the aircraft is not airworthy | ML.A.901(c)(1) to (3) (R, confirmed 18 November 2026) | Must | Test |
| REQ-106 | An extension done up to 30 days before expiry keeps the pattern | ML.A.901(d) (R, confirmed 18 November 2026) | Must | Boundary tests at 30 and 31 days |
| REQ-107 | The documented review of records is a checklist of the items the regulation lists. Each item has a result, the evidence sampled and any finding | ML.A.903(a)(1) to (11) (R, confirmed 18 November 2026) | Must | Inspection against the UK text; Test |
| REQ-108 | The physical survey is a checklist of the items the regulation lists, with the same fields, and records who assisted if the review staff member is not qualified under Part-66 | ML.A.903(b), (c)(1) to (5) (R, confirmed 18 November 2026) | Must | Inspection against the UK text; Test |
| REQ-109 | A certificate can be issued only when the review is complete, every finding is closed, and the person issuing it is airworthiness review staff with a current authorisation | ML.A.903(e) (R, confirmed 18 November 2026); CAO.A.045 (R) | Must | Test |
| REQ-110 | The certificate is CAA Form 15c. Its serial is allocated by the server, unique, and never reused, including after a void or a restore from backup | Decisions.md, Product; CAP 562 C-90 (R) | Must | Test, concurrency test |
| REQ-111 | A copy of each certificate issued or extended goes to the Civil Aviation Authority within 10 days. The system shows the deadline, records the date sent, and flags an unsent copy. Golden: G-CDEF issued 11 November 2026, deadline 21 November 2026 | ML.A.903(f) (R, confirmed 18 November 2026): within 10 days of the date of issue or extension | Must | Golden, Independent |
| REQ-112 | A copy of each certificate issued or extended is kept with all supporting documents | CAO.A.090(a)(3) (N) | Must | Test |
| REQ-113 | Review staff recency is 6 months of continuing airworthiness work in 2 years, or 1 review in 12 months. The system calculates the date recency lapses. Golden: lapse on 2 December 2026 for the review staff member in SampleData.md | CAO.A.045(c), AMC1 CAO.A.045(c) (R, confirmed 18 November 2026); CAMO.A.305 (R) | Must | Golden, Independent |
| REQ-114 | A lapsed review staff member is restored by 1 review under supervision, which the system records | AMC1 CAO.A.045(d) (R, confirmed 18 November 2026) | Should | Test |
| REQ-115 | Review staff records are kept for 2 years after the person leaves | CAO.A.045(e) (R) | Must | Test |
| REQ-116 | The review schedule lists every aircraft by days remaining to expiry and shows whether today is inside the 90-day window | REQ-100, REQ-102 | Must | Test |

## 7. Records

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-130 | Every record has an append-only history. Each entry holds who made it, when, what changed, the value before and the value after | CAP 562 C-90 (R); (D) brief Step 4 | Must | Test |
| REQ-131 | Nothing is deleted. A wrong or outdated entry is superseded by a new one, and both remain | CAP 562 C-90 (R); (D) brief Step 4 | Must | Test: no delete path in the application; the database refuses update and delete on history |
| REQ-132 | Records are protected against unauthorised alteration, damage and theft | 145.A.45(e) (R, adopted for Part-CAO); CAO.A.090(d) (N) | Must | Test; penetration test |
| REQ-133 | The system keeps every record for at least the longest applicable period: maintenance records 36 months after release; totals and directive status 12 months after the aircraft is withdrawn; Part-CAO records 3 years from release and continuing airworthiness records 2 years after permanent withdrawal | ML.A.305 (R); CAO.A.090(b), (c) (N) | Must | Inspection: the system has no automatic removal at all in private beta |
| REQ-134 | A complete record of an aircraft can be exported at any time in an open, documented format. It includes the full history and superseded entries | ML.A.305 (R); CAO.A.090(f) (N, transfer of records); (D) brief Step 4 | Must | Test: export compared with the database for every record type |
| REQ-135 | A complete record of an organisation can be exported in the same way | (D) brief Step 4; CAO.A.090(g) (N) | Must | Test |
| REQ-136 | A new type of record cannot be added without adding it to the export | Hazard H-012 | Must | Test: the build fails |
| REQ-137 | The time of every entry is stored in Coordinated Universal Time. A regulatory date (due, valid to, deadline) is a UK local date with no time, and periods are counted in UK local dates | (D) brief Step 4; hazard H-006 | Must | Boundary tests |
| REQ-138 | A write is reported as saved only after it is committed | Hazard H-003 | Must | Test |
| REQ-139 | Every calculated figure can be expanded to show the rule, the inputs and the source reference it was calculated from | Hazard H-014 | Must | Inspection, Test |

## 8. Backup and Recovery

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-150 | The records are backed up at least every 24 hours | 145.A.45(e) (R, adopted for Part-CAO); CAP 562 C-90 (R) | Must | Demonstration; backup logs |
| REQ-151 | Backups are stored in a different location from the main data | CAO.A.090(e) (N) | Must | Inspection |
| REQ-152 | A failed or missing backup raises an alert | Hazard H-009 | Must | Demonstration |
| REQ-153 | A restore from backup is carried out and recorded before private beta ends, and repeated on a schedule | Hazard H-009; CAP 562 C-90 (R) | Must | Demonstration |
| REQ-154 | After a restore, certificate serials continue from the highest serial ever issued | Hazard H-007; CAP 562 C-90 (R) | Must | Demonstration |

## 9. CAA Acceptance of Computer Records

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-170 | Records are loaded from paper or spreadsheets only through an import that produces a verification report: every imported value beside its source value, with who checked it | CAP 562 C-90 (R) | Must | Test |
| REQ-171 | Airworthiness directive data and maintenance review data can be checked 100% on migration, and the report shows the proportion checked | CAP 562 C-90 (R) | Must | Test |
| REQ-172 | The system has a problem log. An entry records the problem, the action and the solution, with dates and people. Entries cannot be changed or removed; a later note is added to an entry | CAP 562 C-90 (R, bound problem log) | Must | Test |
| REQ-173 | The system records the start of an organisation's parallel run and shows when 6 months have passed | CAP 562 C-90 (R) | Should | Test |
| REQ-174 | The system records the reference and date of the organisation's written Civil Aviation Authority approval to keep records other than in logbooks | CAP 562 C-90 (R); (N) research/cap562/03.md cites C-50 5.11 | Must | Test |
| REQ-175 | A description of the system is kept for use in an exposition: main functions, how records are queried, who is authorised, security, backup and training | CAP 562 C-90 (N); AMC1 CAO.A.025 (R) | Must | Inspection |
| REQ-176 | A change that extends the system into a new function regulated by the Civil Aviation Authority is recorded as a decision before release, so the organisation can tell the authority | CAP 562 C-90 (N, scope of the assessed system) | Should | Inspection |

## 10. Interface and Writing

| Identifier | Requirement | Source | Priority | Verification |
|---|---|---|---|---|
| REQ-190 | Labels are terse Title Case with no full stops and no middle dots. Nothing is abbreviated except regulatory identifiers | Writing.md; Decisions.md, Writing | Must | Inspection; automated check of interface strings |
| REQ-191 | The registration column is always Aircraft Registration, and the type shown is the type rating | Decisions.md, Writing | Must | Inspection |
| REQ-192 | Dates are written 18 November 2026. Hours are written 6,412.6 | Writing.md | Must | Test |
| REQ-193 | Amber means due soon and red means overdue only. Green appears only in a Status column. Colour is never the only signal: a word sits beside it | Decisions.md, Interface; design-system/README.md | Must | Inspection |
| REQ-194 | Tables are one line per row, expand on click, and never wrap cell text | Decisions.md, Interface; Components.md | Must | Inspection |
| REQ-195 | Forms are named as Civil Aviation Authority forms: CAA Form 15c, CAA Form 3-CAO, CAA Form 1 | Decisions.md, Product | Must | Automated check that no interface string contains "EASA Form" |
| REQ-196 | The interface uses the tokens and components in `design-system/` | design-system/README.md | Must | Inspection |

## Open Points

These block verification of the requirements named, not the start of building.

| Point | Requirements | Tracked |
|---|---|---|
| Confirm every (N) reference against the UK text | All with (N) | Issue #38 |
| Last day of validity of a certificate that does not keep the pattern. ML.A.901(a) says only "valid for 1 year"; CAA Form 15c not yet read | REQ-103 | Issue #38 |
| Role matrix | REQ-006, REQ-007 | Decisions.md, with Step 4 |
