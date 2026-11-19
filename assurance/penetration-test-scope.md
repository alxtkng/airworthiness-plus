# External Penetration Test: Scope

Step 7 of private beta. Date: 19 November 2026. Tracked as Issue 40. The test happens before any customer data enters the system. Choosing the tester and accepting the cost are Alex King's decisions.

## Why

CAP 562 C-90 expects the assessor of a computer records system to try to beat it. `assurance/asvs.md` is a self-assessment by the people who wrote the code. This test is the independent check that the controls hold against someone trying to defeat them (assurance case C3.5).

## What Is Tested

The application as deployed for the test, at its own address, with two organisations set up from the sample data in `design-system/SampleData.md` and one user for each role in each. No real records.

| Area | What the Tester Tries | Threats | Our Own Evidence |
|---|---|---|---|
| Sign-in | Guessing and stuffing of passwords; getting past the second factor; reuse of a code; the lock; telling real user names from unknown ones; the first password and its forced change; reset of a password or second factor by an Administrator, and the code asked for before it | TH-001 | `tests/test_sign_in.py`, `tests/test_totp.py`, `tests/test_users.py` |
| Sessions | Fixing, stealing or replaying a session; the time limits; sign-out; use of a session after the user is made inactive or their sessions are ended; the list of a user's own sessions, and ending someone else's by its identifier | TH-002 | `tests/test_sign_in.py`, `tests/test_security.py` |
| Forged requests | A write made from another site; a write by GET | TH-003 | `tests/test_security.py` |
| Injection | SQL, markup, template code and spreadsheet formulas through every field, the import file and the address | TH-004, TH-082 | `tests/test_security.py`, `tests/test_exports.py` |
| Access by role | Every action of the matrix in `design-system/Decisions.md` as every role, including by changing a request by hand; an Administrator giving themselves a role | TH-008 | The role matrix test of each module |
| Isolation between organisations | Reading and writing organisation A's records as a user of organisation B through every address, by guessing or substituting identifiers, through the import and through both exports | TH-006, TH-020, TH-080 | The other-organisation test of each module; `tests/test_data_layer.py` |
| Record tampering | Changing or removing a record, a history entry, an access log entry or an issued certificate through the application; issuing a certificate out of turn or as lapsed staff; recording one as from before these records to stand in for a review; taking a serial twice | TH-009, TH-021, TH-023, TH-025 | `tests/test_data_layer.py`, `tests/test_reviews.py`, `tests/test_review_checklist.py` |
| Import | Files that are too large, of the wrong kind, malformed or hostile; half-loaded files | TH-007 | `tests/test_imports.py` |
| Export | Another organisation's export; an altered export passed off as genuine; what an export gives away | TH-080, TH-081 | `tests/test_exports.py` |
| Transport and headers | TLS versions and ciphers at the reverse proxy; redirects; Strict Transport Security; the Content Security Policy; cookies; what is cached | TH-005 | `tests/test_security.py`; server checks in `operations/` |
| The server as seen from outside | Which ports answer; whether the database, the backups or any administration surface can be reached; whether this service can reach, or be reached from, the other projects on the server | TH-024, TH-025 | `operations/`, Step 8 |
| Backups | Whether a backup can be fetched or read by someone who should not | TH-040, TH-041 | `operations/backup-and-restore.md`, Step 8 |

The threat numbers are those of `architecture/threat-model.md`.

## What Is Not Tested

- Every other project on the same server, and the server's own management. They are not ours to offer for testing, and nothing of theirs is to be touched.
- The airworthiness.co domain and its email.
- Attempts to make the service unavailable by volume.
- Social engineering of anyone, and physical access.
- GitHub itself. The repository settings are reviewed by us (`assurance/ncsc-self-assessment.md`).

## How

- **Grey box.** The source code, this scope, the threat model and `assurance/asvs.md` are public and are given to the tester. Accounts for both organisations and every role are provided.
- **Against the standard.** OWASP Application Security Verification Standard 5.0, Level 2, is the checklist; the tester states which requirements were tested and how.
- **A separate deployment.** The same build as would go live, on its own address, holding sample data only. It is rebuilt from clean before the test and destroyed after the retest.
- **Evidence.** Requests and responses for each finding, enough to reproduce it.

## What Comes Back

- A report with each finding, how to reproduce it, its severity under a named scheme, and the ASVS requirement it bears on.
- A retest of everything fixed.
- A statement of what was and was not tested.

Each finding becomes an Issue linked to its requirement and threat. No customer data enters the system while a finding of high severity is open (the readiness review).

## To Be Decided by Alex King

1. The tester. A firm accredited under a recognised United Kingdom scheme is suggested; which schemes the Civil Aviation Authority or customers would expect is To Be Checked.
2. The cost and the date.
3. Whether the test is repeated each year and after any large change, which `operations/vulnerability-management.md` proposes.
