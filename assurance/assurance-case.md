# Assurance Case

Method: Claims, Arguments, Evidence, as the National Cyber Security Centre uses in its Assurance Principles and Claims for the Software Security Code of Practice. A claim is a statement that must be true. An argument says why the evidence shows it. Evidence is something that can be opened and checked.

Scope: the private beta slice, the Part-CAO core loop for Part-ML aircraft (`prompts/private-beta.md`, Part 5).

Status of every item of evidence is one of: Planned (named, does not exist yet), Partial, Available. At the start of private beta all evidence is Planned. The readiness review (`assurance/readiness-review.md`) checks every row is Available.

References marked To Be Checked have not yet been confirmed against the UK text of Regulation (EU) No 1321/2014, CAA edition of September 2026.

## Top Claim

**C0. Airworthiness+ records and calculates continuing airworthiness data correctly, securely and acceptably to the CAA for a Part-CAO.**

Argument: the claim holds if each of the seven sub-claims holds. Correctness (C1, C7) covers what the system tells the user. Integrity, access and availability (C2, C3, C4) cover what the system keeps. Secure development (C5) covers how the system is built and changed. CAA acceptability (C6) covers whether the authority can accept it in place of hard copy records.

Context: hazards caused by the software are in `assurance/hazard-log.md`. Each sub-claim lists the hazards it answers.

## C1. Correctness of Calculations

**Claim: every due date, remaining time, validity date and period the system shows is the one the regulation and the maintenance programme give.**

Hazards answered: H-001, H-006, H-010, H-011.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C1.1 Every calculation rule is a numbered requirement with a source reference | A rule that is written down and sourced can be checked against the regulation by someone other than its author | `requirements/requirements.md` | Partial |
| C1.2 Every calculation requirement has at least one test | A requirement with no test is a visible gap | `requirements/traceability.csv` | Partial |
| C1.3 Golden cases from the sample fleet pass, each with an expected result worked by hand and cited to its rule | Fixed worked cases catch a wrong rule, not only a wrong implementation | Golden fixtures and test results in continuous integration (G-EJKL, G-CDEF, G-ABCD, G-BXYZ, G-FMNO, early review window, whichever comes first, tolerance, exact day counts, date boundaries) | Partial |
| C1.4 Interval arithmetic holds for generated inputs, not only chosen ones | Property-based tests explore cases nobody thought to write | Property-based test results in continuous integration | Partial |
| C1.5 Each calculation module is recomputed independently | A second party who has not seen the implementation recomputes the golden cases from the regulation and fixtures alone, mirroring an independent inspection | `assurance/independent-verification/` one report per module | Partial |
| C1.6 Dates are handled by one explicit rule | Regulatory periods are counted in UK local dates; leap years, month ends and British Summer Time changes are tested | Architecture Decision Record on dates and time zones; boundary tests | Planned |

## C2. Integrity and Permanence of Records

**Claim: once entered, a record is never lost or silently changed, and its full history can always be shown.**

Hazards answered: H-003, H-007, H-008, H-012.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C2.1 Every record has an append-only history: who, what, when, before and after | CAP 562 C-90 expects the full input history to be kept; a terminating action must not erase earlier repetitive inspection entries | `architecture/decisions/ADR-0002-data-layer.md`; `tests/test_data_layer.py`: update and delete of history refused for the application and for the owner | Partial |
| C2.2 Nothing is deleted, only superseded | Same as C2.1 | `tests/test_data_layer.py`: the catalogue test on privileges and triggers for every table | Partial |
| C2.3 Records are protected against unauthorised alteration | 145.A.45(e), adopted as a design requirement for Part-CAO | Access control tests; threat model, tampering threats; hash chain tests in `tests/test_data_layer.py` | Partial |
| C2.4 Certificate serials are allocated by the server, unique and never reused | CAP 562 C-90 expects control of serial numbers for certificates the system generates | Concurrency tests on serial allocation: `tests/test_reviews.py` | Partial |
| C2.5 Records are kept for the required periods | ML.A.305 and CAO.A.090; staff records CAO.A.045(e) | Retention requirements and tests | Planned |
| C2.6 A complete aircraft record can be exported at any time in an open format | The owner's records must be transferable; the export also proves nothing is held only in a proprietary form | Export tests comparing export against database content | Planned |
| C2.7 Migrated data is verified against its source | CAP 562 C-90: up to 100% checking of airworthiness directive and maintenance review data | Migration verification report for each load (Step 9) | Planned |

## C3. Access Control and Data Segregation

**Claim: each organisation sees and changes only its own data, and each person only what their role allows.**

Hazards answered: H-004, H-003.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C3.1 Organisation scoping is enforced in the data layer, not only in the interface | AMC1 CAO.A.100(f) point (d)(2): each organisation has access to its own data only and data is entered only by its own personnel. Enforcement below the interface survives an interface mistake | `architecture/decisions/ADR-0002-data-layer.md`; `tests/test_data_layer.py` | Partial |
| C3.2 Every endpoint refuses reads and writes of another organisation's records | Tested by trying, for every endpoint | Automated cross-organisation isolation tests in continuous integration (Step 7) | Planned |
| C3.3 Write access is by role | CAP 562 C-90: only authorised persons may alter records | Role matrix in `design-system/Decisions.md`; `tests/test_roles.py`, `tests/test_sign_in.py` | Partial |
| C3.4 Accounts resist takeover | Threat model, account takeover threats | `tests/test_sign_in.py`, `tests/test_totp.py`; `assurance/asvs.md` authentication and session results, to come | Partial |
| C3.5 An external tester has tried to defeat the controls | C-90 expects the assessor to try to beat the system; independent testing before customer data | Penetration test report (Issue, cost is Alex's decision) | Planned |

## C4. Availability and Recovery

**Claim: the records survive the loss of the server, and the service is restored within a stated time.**

Hazards answered: H-009.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C4.1 Backups are taken at least daily and held away from the server | 145.A.45(e): backup updated within 24 hours, adopted as a design requirement | `operations/backup-and-restore.md`; backup job logs | Planned |
| C4.2 A restore has been carried out and its result recorded | A backup that has never been restored is not evidence of recovery | `operations/restore-tests/` dated record of each test | Planned |
| C4.3 The recovery point objective and recovery time objective are stated with reasoning | The user must know how much data could be lost and for how long the service could be down | `operations/backup-and-restore.md` | Planned |
| C4.4 Failures are noticed | A failed backup or outage raises an alert | `operations/monitoring.md`; alert test record | Planned |
| C4.5 Incidents are handled by a written procedure | | `operations/incident-response.md` | Planned |

## C5. Secure Development

**Claim: the software is built, changed and released by a process that keeps vulnerabilities out and finds those that get in.**

Hazards answered: H-003, H-004 (as causes), and supply-chain threats in the threat model.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C5.1 Development follows an established framework | NIST SP 800-218 Secure Software Development Framework, and the NCSC Software Security Code of Practice | `assurance/ncsc-self-assessment.md` | Partial |
| C5.2 Every change is reviewed and checked before merge | Protected `main`, pull requests only, continuous integration: tests, type checks, linting, dependency vulnerability scan, secret scanning | Branch protection rule on `main` (pull request required, checks must pass, administrators included); `.github/workflows/checks.yml` and its run history | Available |
| C5.3 The composition of the software is known | Pinned dependencies and a software bill of materials generated at each build | Lock file; software bill of materials artefact | Available |
| C5.4 Secrets are never in the repository | Secrets only in the server environment | Secret scanning results; `.gitignore` | Partial |
| C5.5 Threats are identified and each is linked to a requirement and a test | STRIDE against the data flows | `architecture/threat-model.md` | Partial |
| C5.6 The application meets a chosen and justified verification level | OWASP Application Security Verification Standard 5.0 | `assurance/asvs.md` | Planned |
| C5.7 Vulnerabilities can be reported and are handled | | `SECURITY.md`; `operations/vulnerability-management.md` | Partial |

## C6. CAA Acceptability

**Claim: the system meets the conditions under which the CAA accepts computerised records, so a Part-CAO can put it in its exposition.**

Hazards answered: H-008, H-003, H-007.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C6.1 Each CAP 562 C-90 condition is a requirement with a test or a documented procedure | C-90 is the published basis for accepting computer records and programmes: amendment history that cannot be deleted, write access by role, up to 100% check of directive and review data on migration, backup, serial control, 6-month parallel run with a bound problem log, written approval to keep records other than in logbooks | `requirements/requirements.md` C-90 section; `requirements/traceability.csv` | Planned |
| C6.2 The system supports the parallel run and problem log | The 6-month parallel run happens in public beta; private beta must deliver the means: a problem log whose entries cannot be removed | Problem log requirement and tests | Planned |
| C6.3 The system records the customer's written CAA approval | Reference and date for each organisation | Requirement and test | Planned |
| C6.4 The system can be described in an exposition | AMC1 CAO.A.025 Part B (records, B.9 in `design-system/Procedures.md`): functions, authorised persons, security, backup, training | Draft exposition text for the records system | Planned |
| C6.5 Contracted software conditions are met | AMC1 CAO.A.100(f) point (d)(2): own data only, data entered only by the organisation's personnel, data retrievable at any time | C3.1, C3.2, C2.6 | Partial |
| C6.6 Forms and terms are the CAA's | CAA Form 15c, CAA Form 3-CAO, SRG1782 type ratings verbatim (`design-system/Decisions.md`) | Interface review against Decisions.md and Writing.md. The certificate page carries every entry of CAA Form 15c, Issue 2, inspected against Appendix IV to Part-ML on 18 November 2026: `tests/test_review_checklist.py` | Partial |

Limit of this claim: acceptance is the CAA's decision for each organisation. This case shows the conditions are met; it does not assert approval.

## C7. Maintenance Data Currency

**Claim: the system never presents maintenance data as current when it is not, and shows when currency was last checked.**

Hazards answered: H-005.

| Sub-claim | Argument | Evidence | Status |
|---|---|---|---|
| C7.1 Each set of data held carries author, applicability, revision and the date its amendment status was last checked | M.A.401, ML.A.401, CAO.A.055; AMC M.A.401(c), AMC1 145.A.45(g) | Requirements and tests; golden case G-FMNO (Grob G 115 manual amendment to check by 20 November 2026): `tests/test_maintenance_data.py` | Partial |
| C7.2 A superseded revision is marked superseded everywhere it appears and is never selectable as current | Supersession is an append-only event (C2.2), so the earlier revision stays visible in history only | Tests on revision supersession: `tests/test_maintenance_data.py` | Partial |
| C7.3 An overdue amendment check is flagged | Currency rests on the check being done, with special attention to mandatory instructions and airworthiness limitations | Tests on amendment check due dates: `tests/test_maintenance_data.py` | Partial |
| C7.4 Customer-provided data is held only while work is in progress or for the length of the contract, with its amendment status evidenced | CAO.A.055(a), CAO.A.080 | Requirements and tests; sample case G-BXYZ owner-provided instructions confirmed 2 June 2026: `tests/test_maintenance_data.py` | Partial |
| C7.5 Data needed for a job is confirmed held and current before the work | AMC1 CAO.A.055. Work packages are outside this slice, so the slice delivers the check, not the work package | Requirement recorded; test of the currency check: `tests/test_maintenance_data.py` | Partial |

## Maintaining This Case

- A pull request that adds evidence changes the Status here in the same pull request.
- A new hazard is added to the hazard log and to the sub-claim that answers it.
- The case is reviewed in full at the readiness review.
