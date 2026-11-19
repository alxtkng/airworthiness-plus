# Threat Model

Method: STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) applied to each data flow of the private beta slice, on the stack accepted in `architecture/decisions/ADR-0001-stack.md`.

Every threat is linked to the requirement that answers it and to a planned test. Test identifiers beginning T-SEC are created in Step 7 and entered in `requirements/traceability.csv`; until a test exists the threat is Open.

Reviewed: 18 November 2026, before any product code. Reviewed again at each step that adds a data flow, and in full at the readiness review.

Reviewed in full: 19 November 2026, for the readiness review, by the build session. Every planned test from T-SEC-001 to T-SEC-020 now exists and is named under Tests That Now Exist. The threats whose check is a demonstration on the server (TH-041, TH-042, TH-064 and the server's other services) are not yet shown, because the service is not deployed. Two things were added to Known Gaps in Sign-In by this review: an Administrator's power to reset both factors of another user, and the logging of a user name as typed. No new threat was found that is not already listed. A review by someone other than the author is the penetration test (`assurance/penetration-test-scope.md`).

## What Is Protected

| Asset | Why It Matters |
|---|---|
| Continuing airworthiness records and their history | A lost or altered record means an aircraft's status cannot be shown (ML.A.305, CAO.A.090) |
| Calculated due dates and validity dates | A wrong figure can lead to an overrun (hazards H-001, H-010) |
| Certificates and their serials | A certificate must be traceable and unique (CAP 562 C-90) |
| Separation between organisations | AMC1 CAO.A.100(f) point (d)(2) |
| Personal data of staff, owners and pilots | UK GDPR |
| Backups and their encryption key | They contain everything above |
| The source code, build pipeline and deployment credentials | Whoever controls these controls all of the above |

## Who Might Attack

| Actor | Aim |
|---|---|
| Outsider on the internet | Read or ransom records; use the server for something else |
| User of one organisation | Read or change another organisation's records |
| User inside an organisation | Change or remove a record to hide a missed inspection or directive; act beyond their role |
| Someone with a stolen account | Any of the above, as that user |
| Compromised dependency or build tool | Run code inside the application or the pipeline |
| Someone with access to the server or backup storage | Read or alter data beneath the application |

## Data Flows and Trust Boundaries

```
Browser ──1──> Reverse proxy (Coolify, HTTPS) ──2──> Django application ──3──> PostgreSQL
                                                          │                        │
                                                          6 export file            4 backup (encrypted)
                                                          ▼                        ▼
                                                       Browser              Off-server storage

GitHub repository ──5──> GitHub Actions (checks, build) ──5──> Coolify deployment ──> server
```

Trust boundaries: the internet to the proxy (1); the application to the database (3); the server to off-server storage (4); GitHub to the server (5). The browser is never trusted.

## Threats

Severity uses the hazard log scale: High, Medium, Low.

### Flow 1 and 2. Browser to Application

| Identifier | STRIDE | Threat | Severity | Mitigation | Requirement | Planned Test |
|---|---|---|---|---|---|---|
| TH-001 | Spoofing | Account takeover by guessed, reused or phished password | High | Second factor required; password checked against breached lists; rate limit and lockout on sign-in; sign-in events logged | REQ-008, REQ-009 | T-SEC-001 sign-in without second factor refused; T-SEC-002 repeated failures locked out and logged |
| TH-002 | Spoofing | Session stolen or fixed | High | Session cookie Secure, HttpOnly, SameSite; new session identifier at sign-in; idle and absolute time limits; sign-out ends the session on the server | REQ-008 | T-SEC-003 cookie flags; T-SEC-004 old session identifier refused after sign-in and sign-out |
| TH-003 | Tampering | Forged request made from another site while the user is signed in | High | Django cross-site request forgery protection on every state-changing request; SameSite cookies | REQ-132 | T-SEC-005 write without token refused, for every write endpoint |
| TH-004 | Tampering | Injection through a form field into the database or the page | High | Database access only through the query layer with parameters; template auto-escaping; Content Security Policy with no inline script | REQ-132 | T-SEC-006 injection strings stored and shown inert; T-SEC-007 policy header present |
| TH-005 | Information Disclosure | Traffic read in transit | High | HTTPS only; HTTP Strict Transport Security; no third-party requests from the page | REQ-132 | T-SEC-008 HTTP redirects; header present |
| TH-006 | Information Disclosure | Record identifiers guessed in an address | High | Access decided by organisation in the data layer, not by knowing an identifier; identifiers not sequential | REQ-003 | T-SEC-010 (below) |
| TH-007 | Denial of Service | Flood of requests or very large uploads | Medium | Request size and rate limits at the proxy; no file upload in the slice except import files, which are size limited | REQ-150 (recovery) | T-SEC-009 oversize request refused |
| TH-008 | Elevation of Privilege | User acts beyond their role by calling an endpoint directly | High | Permission checked on the server for every action from one role matrix; the interface hiding a button is never the control | REQ-006, REQ-007 | T-SEC-011 every action tried as every role |
| TH-009 | Elevation of Privilege | Lapsed or unauthorised person issues a review certificate | High | Issue checks role, current authorisation and recency on the server at the moment of issue | REQ-109, REQ-113 | T-SEC-012 issue refused for lapsed staff |

### Flow 3. Application to Database

| Identifier | STRIDE | Threat | Severity | Mitigation | Requirement | Planned Test |
|---|---|---|---|---|---|---|
| TH-020 | Information Disclosure, Tampering | One organisation reads or writes another's records because a query lacks its organisation filter | High | PostgreSQL row-level security on every table, keyed to the organisation set on the database session; with no organisation set, no rows | REQ-002, REQ-003, REQ-004 | T-SEC-010 every endpoint tried against another organisation's records, read and write; T-SEC-013 direct query with no organisation set returns nothing |
| TH-021 | Tampering | A record's history is changed or removed to hide an entry | High | Event tables: application database user has INSERT and SELECT only; trigger refuses UPDATE and DELETE; each event carries a hash chained to the previous event of that record so a gap or change is detectable | REQ-130, REQ-131, REQ-132 | T-SEC-014 UPDATE and DELETE refused as application user and as owner; T-SEC-015 chain verification detects an altered row |
| TH-022 | Repudiation | A user denies making an entry | Medium | Every event records the user, time and session; accounts are individual; users are deactivated, never deleted | REQ-005, REQ-009, REQ-010, REQ-130 | T-SEC-016 every write produces an attributed event |
| TH-023 | Tampering | Duplicate or reused certificate serial through concurrent requests or after a restore | Medium | Serial from a database sequence inside the issuing transaction, with a uniqueness constraint; restore procedure checks the sequence | REQ-110, REQ-154 | T-SEC-017 concurrent issue gives distinct serials |
| TH-024 | Elevation of Privilege | Privilege misuse through an administration interface or a support account | High | No vendor write access to customer organisations; Django administration interface not exposed for customer data; database migrations run with a separate user | REQ-004 | T-SEC-018 administration addresses return not found in production settings |
| TH-025 | Tampering | Someone with database owner access alters data beneath the application | High | Access to the server limited to Alex King by key; hash chain makes alteration detectable; off-server backups allow comparison | REQ-132, REQ-151 | T-SEC-015; operations access review (Step 8) |
| TH-026 | Tampering | The application's database role, driven through an injection, builds a trigger or table of its own to write history entries that no change to a record produced, or switches a trigger off | High | The role owns nothing and can create no table, temporary table, function or trigger; history accepts an entry only from the trigger on a record; every entry is attributed and chained by the database | REQ-130, REQ-131 | `tests/test_data_layer.py`: application_role_can_make_nothing_of_its_own, application_cannot_change_or_remove_history |

### Flow 4. Backup

| Identifier | STRIDE | Threat | Severity | Mitigation | Requirement | Planned Test |
|---|---|---|---|---|---|---|
| TH-040 | Information Disclosure | Backup storage read by an outsider or the provider | High | Backups encrypted before leaving the server; key held separately from the storage credentials | REQ-132, REQ-151 | Restore test record shows a backup is unreadable without the key (Step 8) |
| TH-041 | Tampering, Denial of Service | Backups deleted or encrypted by an attacker who has the server (ransomware) | High | Storage credentials on the server can add but not delete or overwrite; retention set on the storage side | REQ-150, REQ-151 | Demonstration: delete attempt with server credentials refused (Step 8) |
| TH-042 | Denial of Service | Backups silently failing | High | Alert on failure or absence; scheduled restore test | REQ-152, REQ-153 | Demonstration (Step 8) |

### Flow 5. Source, Build and Deployment

| Identifier | STRIDE | Threat | Severity | Mitigation | Requirement | Planned Test |
|---|---|---|---|---|---|---|
| TH-060 | Tampering | Malicious or compromised dependency | High | Few dependencies; versions and hashes pinned in the lock file; vulnerability scan on every pull request; software bill of materials at build; updates reviewed as pull requests | Assurance case C5.3 | Pipeline: install fails on hash mismatch; scan fails on a known vulnerability |
| TH-061 | Tampering | Compromised build action or pipeline step | High | Actions pinned to a commit, not a moving tag; pipeline has read-only repository permission and no deployment secrets on pull requests | Assurance case C5.2 | Inspection of workflow file |
| TH-062 | Tampering | Unreviewed change reaches `main` | High | `main` protected; merge by pull request with passing checks | Assurance case C5.2 | Inspection of branch protection settings |
| TH-063 | Information Disclosure | Secret committed to the repository | High | Secrets only in the server environment; secret scan on every pull request; `.gitignore` | Assurance case C5.4 | Pipeline: secret scan fails on a planted test secret |
| TH-064 | Spoofing | GitHub account or Coolify account taken over | High | Two-factor authentication on both, set by Alex King; deployment credential limited to this application | NCSC principle 2.1 | Inspection, recorded in `operations/` (Step 8) |

### Flow 6. Export

| Identifier | STRIDE | Threat | Severity | Mitigation | Requirement | Planned Test |
|---|---|---|---|---|---|---|
| TH-080 | Information Disclosure | Export of another organisation's aircraft | High | Export runs through the same data-layer scoping; export is a logged event, with the SHA-256 of its manifest | REQ-003, REQ-134, REQ-009 | T-SEC-010 includes export endpoints: test_exports: another_organisations_aircraft_cannot_be_exported |
| TH-081 | Tampering | Exported file altered after export and presented as the record | Medium | Export carries the event hash chain and a checksum, so it can be verified against the system | REQ-134 | T-SEC-019 altered export fails verification |
| TH-082 | Information Disclosure | Formula injection when a CSV export is opened in a spreadsheet | Low | Cells beginning with =, +, - or @ are neutralised in CSV | REQ-134 | T-SEC-020 |

## Design Additions From This Model

These go beyond ADR-0001 and are adopted here:

1. Each event carries a hash chained to the previous event of the same record (TH-021, TH-025, TH-081).
2. The application's storage credentials can add backups but not delete them (TH-041).
3. Database migrations run under a separate database user from the application (TH-024).
4. The application works as a database role that owns nothing and can create nothing, and history is written by the database, not the application (TH-021, TH-026). Recorded in `architecture/decisions/ADR-0002-data-layer.md`, added 18 November 2026.

## Tests That Now Exist

Added 18 November 2026, in `tests/test_data_layer.py` and `tests/test_application.py`. The rest of the T-SEC tests need endpoints and are created in Step 7.

| Planned Test | Test |
|---|---|
| T-SEC-001 | test_sign_in: password_alone_signs_nobody_in |
| T-SEC-002 | test_sign_in: five_failures_lock_the_name_for_15_minutes, wrong_codes_count_towards_the_lock |
| T-SEC-003 | test_application: cookies_are_secure_and_hidden_from_scripts; test_sign_in: session_cookie_is_secure_and_changes_at_sign_in; test_security: cookies_are_for_this_host_over_https_and_hidden_from_scripts |
| T-SEC-004 | test_sign_in: session_cookie_is_secure_and_changes_at_sign_in, sign_out_ends_the_session_on_the_server |
| T-SEC-005 | test_sign_in: forged_request_is_refused; test_security: every_write_refuses_a_forged_request, which goes over every address; and each module's own test of its pages |
| T-SEC-008 | test_application: plain_http_is_redirected_to_https |
| T-SEC-010 | test_aircraft: another_organisations_aircraft_is_not_found_on_any_page, record_cannot_refer_to_another_organisations_record. To be repeated for every endpoint as each is added |
| T-SEC-011 | test_aircraft: every_aircraft_page_follows_the_role_matrix. To be repeated for every endpoint as each is added |
| T-SEC-012 | test_reviews: review_staff_who_have_lapsed_cannot_issue, staff_who_have_left_or_been_made_inactive_cannot_issue; test_review_checklist: review_staff_whose_recency_has_lapsed_cannot_issue_and_the_lapse_is_recorded, only_the_person_carrying_out_the_review_records_and_issues_it, only_review_staff_start_a_review |
| T-SEC-013 | test_data_layer: with_no_organisation_set_there_are_no_rows |
| T-SEC-014 | test_data_layer: application_cannot_change_or_remove_history, owner_of_the_tables_cannot_change_or_remove_history_either |
| T-SEC-015 | test_data_layer: chain_holds, altered_entry_is_detected, removed_entry_is_detected |
| T-SEC-016 | test_data_layer: change_with_no_signed_in_user_is_refused, every_change_writes_who_when_what_before_and_after |
| T-SEC-017 | test_reviews: two_certificates_cannot_be_allocated_a_serial_at_the_same_moment, serials_run_in_order_and_a_void_serial_is_never_used_again |
| T-SEC-018 | test_application: administration_interface_is_absent |
| T-SEC-006 | test_security: hostile_text_is_stored_and_shown_as_text |
| T-SEC-007 | test_security: every_response_carries_the_security_headers; test_interface: the_fonts_stylesheet_and_script_are_the_applications_own |
| T-SEC-009 | test_security: a_request_that_is_too_large_is_refused; test_imports: a_file_that_is_not_as_described_is_refused. Limits at the proxy come with deployment |
| TH-040, demonstration | `operations/restore-tests/2026-11-19.md`, step 2a: a backup cannot be read without its key |
| T-SEC-019 | test_exports: an_altered_export_fails_verification, the_export_agrees_with_itself_and_with_the_chain_in_the_database, the_command_checks_an_export_without_the_database |
| T-SEC-020 | test_exports: a_value_that_looks_like_a_formula_is_not_run_by_a_spreadsheet |

## Known Gaps in Sign-In

Recorded 18 November 2026, to be settled when the verification level is chosen in Step 7 (`assurance/asvs.md`).

- The key shared with the authenticator application is stored as it is, not encrypted, in a column kept out of the history. Encrypting it needs a cryptography dependency and a key in the server environment.
- A new password is checked for length and against Django's list of common passwords, not against a list of breached passwords (threat TH-001).
- The first time, the second factor is set up by whoever holds the password. An account's first password must therefore reach its user by a route that is not the system itself.
- The key is shown as text and as a set-up address, with no code to scan.
- Closed 18 November 2026: the Users page lets an Administrator add a user, set roles, make a user inactive, set a new first password and reset a second factor; a user changes their own password. A first password is changed before any other page answers (`tests/test_users.py`).
- An Administrator who resets a second factor and sets a password could then sign in as that user. Both acts are in the access log with the Administrator's name; nothing prevents them. To be weighed in Step 7.
- The access log holds the network address of each attempt, which is personal data. It is in `operations/data-protection/record-of-processing.md`, where how long it is kept is an open question.
- A failed sign-in with a user name that belongs to nobody is logged with the name as typed. A person who types a password into the user name box by mistake leaves it in the log. Whether to keep the typed name is an open question in the same document.
- Closed 19 November 2026: behind the reverse proxy the address logged is the one the proxy saw, when `AIRWORTHINESS_BEHIND_PROXY` is set (`tests/test_security.py`). The proxy must overwrite, not pass on, the forwarded headers; that is checked at deployment.
- Found by the sweep over every address on 19 November 2026 and fixed: a sign-in sent with no user name caused a server error instead of a refusal.
- Django's development server reads the migrations table, which the application's database role cannot. The service runs under a WSGI server, to be chosen and added as a dependency before the first deployment.

## Not Yet Covered

- Email (password reset, notifications): no email flow is designed yet. It is modelled when it is added.
- File attachments (scanned certificates, supporting documents for REQ-112): upload handling and malware scanning are modelled when attachments are designed.
- The server's other services: the Coolify server runs other projects that are not to be touched. Isolation between them and this application is checked at first deployment (`operations/deployment.md`); the build session could not reach the server.
