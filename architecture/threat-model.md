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
Browser ──1──> Reverse proxy (HTTPS) ──2──> Django application ──3──> PostgreSQL
                                                          │                        │
                                                          6 export file            4 backup (encrypted)
                                                          ▼                        ▼
                                                       Browser              Off-server storage

GitHub repository ──5──> GitHub Actions (checks, build) ──5──> Deployment ──> host
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
| TH-064 | Spoofing | GitHub account or hosting account taken over | High | Two-factor authentication on both, set by Alex King; deployment credential limited to this application | NCSC principle 2.1 | Inspection, recorded in `operations/` (Step 8) |

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

Recorded 18 November 2026, to be settled when the verification level was chosen in Step 7. It was: OWASP ASVS 5.0 Level 2, assessed in `assurance/asvs.md` on 19 November 2026.

- The key shared with the authenticator application is stored as it is, not encrypted, in a column kept out of the history. Encrypting it needs a cryptography dependency and a key in the server environment. Decided 19 November 2026 not to do so in private beta, with the reasons in `operations/keys-and-secrets.md`.
- A new password is checked for length and against Django's list of common passwords, not against a list of breached passwords (threat TH-001).
- The first time, the second factor is set up by whoever holds the password. An account's first password must therefore reach its user by a route that is not the system itself.
- The key is shown as text and as a set-up address, with no code to scan.
- Closed 18 November 2026: the Users page lets an Administrator add a user, set roles, make a user inactive, set a new first password and reset a second factor; a user changes their own password. A first password is changed before any other page answers (`tests/test_users.py`).
- An Administrator who resets a second factor and sets a password could then sign in as that user. Both acts are in the access log with the Administrator's name; nothing prevents them. Weighed on 19 November 2026: see the next line.
- Changed 19 November 2026 (OWASP ASVS 5.0 6.4.1, 7.5.1): a first password is made by the system, shown once and good for 7 days; a change of password, a new first password and a reset of a second factor need a sign-in within the last 5 minutes or a code (`tests/test_users.py`). A session left open on an Administrator's machine can no longer be used to take over another user's sign-in. An Administrator acting on purpose still can.
- The access log holds the network address of each attempt, which is personal data. It is in `operations/data-protection/record-of-processing.md`, where how long it is kept is an open question.
- A failed sign-in with a user name that belongs to nobody is logged with the name as typed. A person who types a password into the user name box by mistake leaves it in the log. Whether to keep the typed name is an open question in the same document.
- Closed 19 November 2026: behind the reverse proxy the address logged is the one the proxy saw, when `AIRWORTHINESS_BEHIND_PROXY` is set (`tests/test_security.py`). The proxy must overwrite, not pass on, the forwarded headers; that is checked at deployment.
- Found by the sweep over every address on 19 November 2026 and fixed: a sign-in sent with no user name caused a server error instead of a refusal.
- Django's development server reads the migrations table, which the application's database role cannot. The service runs under a WSGI server, to be chosen and added as a dependency before the first deployment.

## Added on 19 November 2026

What the build of 19 November 2026 added to the surface, and what answers it. Each belongs to a threat already listed; none is a new kind of threat.

| Added | Threat | What Answers It |
|---|---|---|
| A user's list of their own sessions, and ending one by an identifier in the address | TH-002, TH-020 | Only the user's own live sessions are listed or found; the identifier is a one-way hash of the session key; ending one needs a fresh sign-in or a code (`tests/test_users.py`) |
| Changes on the Users page made from a session left open | TH-002, TH-008 | Every change asks for a code once the sign-in is more than 5 minutes old, and five wrong codes lock the name. The first build asked only for the two resets, which the independent review of 19 November 2026 showed could be got round by adding an Administrator (`tests/test_users.py`) |
| The browser and address a session gave at sign-in, shown back on a page | TH-004 | Shown as text, escaped, as the independent review of 19 November 2026 confirmed; no script runs from a page under the Content Security Policy (`tests/test_security.py`) |
| The Access Log page | TH-008, TH-020 | The Administrator only; the database shows an organisation its own entries (`tests/test_users.py`) |
| A certificate recorded as the organisation's own from before these records | TH-009 | Dated no later than the person's last review before these records, which is never after the day the person was recorded as review staff, in the service and in the database; uses no serial; cannot be altered afterwards (`tests/test_reviews.py`) |
| A first password shown once to the Administrator | TH-001 | Made by the system, stored only as a hash, good for 7 days, changed before any page answers (`tests/test_users.py`) |
| The first Administrator's password, typed when an organisation is set up or kept in Render for the test site | TH-001 | A first password like any other: changed at the first sign-in, good for 7 days. Before the independent review of 20 November 2026 it never had to be changed (`tests/test_test_site.py`) |
| The export of an organisation asked for again and again | TH-007 | 6 in an hour for each organisation, taken one at a time (`tests/test_exports.py`) |
| Sorting and searching a table in the browser | TH-004 | The script reads and moves what the page already holds; it builds nothing from text as markup (`tests/test_browser.py`) |

## Added on 20 November 2026

The test site (ADR-0003, `operations/test-site.md`): a second place the application runs, on a host that is not ours, holding the sample organisation and no real record.

| What Was Added | Threat | How It Is Met |
|---|---|---|
| The owner's work done by a program when the container starts | TH-024 | The service is started with the owner's credentials and the Administrator's first password removed from its environment, and as its own role (`tests/test_test_site.py`; shown on the running processes in the rehearsal) |
| A role for the service made by that program | TH-020, TH-024 | A member of `airworthiness_application` and nothing more, with no power of its own. An existing role that is anything else is refused, not altered. Its password is hashed before it is sent to the database (`tests/test_test_site.py`) |
| The sample set up without a person at a prompt | TH-024 | Only in a database the program found empty and marked as the test site's own; any other is refused, so the sample cannot reach real records (`tests/test_test_site.py`) |
| A set-up file for the host in the repository | TH-063 | Every secret is generated by the host or taken from its database. A test fails the build if the file holds a value for one |
| A sign-in page on a public address, for the sample | TH-001 | As on the server: a password and a second factor, and a user name locked for 15 minutes after 5 failures. The first password is 256 random bits |

Accepted for the test site and not for the server: the owner's database password is stored by the host with the service's settings, and whoever can sign in to the host's account can read it.

## Added on 24 November 2026

The canvas build, Phase 0 (`prompts/canvas-build.md`): approvals held, person records.

| What Was Added | Threat | How It Is Met |
|---|---|---|
| A record of each approval an organisation holds, which decides what the sidebar shows | TH-008, TH-020 | A record like any other: row-level security, history, no delete. The sidebar is navigation only. Every address still checks the role matrix on the server, and the database still shows an organisation its own rows alone (`tests/test_approvals.py`, `tests/test_navigation.py`) |
| A migration that reads each organisation in turn as the owner of the tables | TH-020, TH-025 | The forcing of row-level security is lifted from the organisation table alone, inside the migration's transaction and under the lock that changing a table takes, and put back before it ends. Each organisation's rows are written with that organisation set, and the history records the database role (ADR-0002; `tests/test_approvals.py` checks the forcing is back) |
| A person record for everyone, linked to a sign-in where there is one | TH-020, TH-022 | A record like any other. A person and the person they report to belong to one organisation, by trigger. The database refuses a sign-in with no person. The check sets the organisation of the sign-in it is checking and puts back what was set before, so it shows nothing of another organisation (`tests/test_people.py`) |
| A new sign-in linked to the person already recorded under the same name | TH-008 | Only within the organisation, only to a person with no sign-in who has not left, and only when there is exactly one. The link gives the sign-in nothing: what a user may do comes from their roles alone. A wrong link is seen on the Staff page and is in the history. Withdrawn after the independent review of 24 November 2026: nothing is linked by name (Corrections of 24 November 2026, below) |
| A customer record for each owner, and each aircraft held to a customer of its own organisation | TH-020 | A record like any other. The database refuses an aircraft with no customer, and one whose customer belongs to another organisation, by trigger (`tests/test_customers.py`). A choice of customer on a form offers only the organisation's own |
| A second sample organisation on the test site, and a start that adds to a sample already there | TH-020, TH-024 | The second organisation is kept from the first by the same row-level security as any two; a test signs in to each and finds nothing of the other (`tests/test_second_organisation.py`). The start still works only on a database marked as the test site's own. What it adds is added as the owner, with the organisation set, and is in the history against the database role. Its first password is a first password like any other: changed at first sign-in, good for 7 days, never written to the log |
| A Dashboard that reads across every section for one organisation | TH-020 | It reads through the same services and the same database session as the pages, so row-level security shows it one organisation alone; another organisation's Dashboard is tested to show nothing of ours (`tests/test_dashboard.py`). It writes nothing: reading it as each role adds no entry to the history |
| A Settings page where the Administrator changes the organisation's name, approvals held, lead times and default limits | TH-003, TH-008 | Each change is a POST that carries the forgery token and is checked against the role matrix on the server, under Change Organisation Record; the generic tests of every address cover them (`tests/test_security.py`, `tests/test_settings.py`). Every change is in the history of the organisation record. The approval an organisation was set up with cannot be ended on the page |
| Names of owners, who may be private people, now records of their own | TH-020 | As the free text was: personal data inside the aircraft's record. In `operations/data-protection/record-of-processing.md` |
| Names, roles and licences of people who do not use the system | TH-020 | Personal data of the organisation's staff, protected as its other records are. Added to `operations/data-protection/record-of-processing.md` |

## Corrections of 24 November 2026

The independent review of 24 November 2026 (`assurance/independent-verification/code-review-2026-11-24.md`) found what Phase 0 had added to the surface and not answered. Each belongs to a threat already listed. Built by 27 November 2026.

| What Was Found | Threat | How It Is Met |
|---|---|---|
| The Administrator could change what an issued certificate showed, by changing the organisation's details or a person's name | TH-008 | The certificate and the extension keep what they showed. The database writes the values when each is recorded, whatever the application sends, and refuses any later change (`tests/test_certificate_kept.py`) |
| A person with a sign-in could be renamed from a session left open, and that name is who the history says acted | TH-002, TH-022 | A fresh sign-in or a code, as every change on the Users page (`tests/test_users.py`) |
| A new sign-in was joined to a person of the same name, and so to that person's record | TH-008 | Nothing is joined by name. A sign-in is given a new person, or one the Administrator chooses who has no sign-in and has not left, read under a lock so that two sign-ins cannot be given one person (`tests/test_people.py`) |
| A person recorded as having left could keep, or be given back, an active sign-in | TH-008 | Recording the day makes the sign-in inactive and ends its sessions; it is not made active while the person is recorded as left (`tests/test_people.py`) |
| Every role read every colleague's user name on the Staff pages, and five wrong passwords lock a name for 15 minutes | TH-001, TH-007 | A user name is shown only to a role that may manage users. A name known by another route can still be locked, as at the sign-in page (`tests/test_people.py`) |
| The second sample organisation's Administrator was given the first Administrator's first password, and a taken user name stopped every start | TH-001, TH-007 | A generated value of its own, read only at the start that sets the organisation up. With none, with the first's, or with a user name taken, the start says so and carries on (`tests/test_test_site.py`) |
| The top-up of the test site rewrote and duplicated people once anyone had edited them, past the checks of the pages | TH-025 | It adds once, records that it has, and after that does nothing. Every write goes through the services the pages use. Tested as an owner of the tables who is not a superuser (`tests/test_top_up.py`) |
| Any organisation could record review staff and issue a review certificate, whatever its approval | TH-008, TH-009 | Open only to an organisation holding Part-CAO with the airworthiness review privilege, on every action on the server and in the services, with the refusal in the access log (`tests/test_review_privilege.py`) |
| The application's role could leave a sign-in with no person, and rewrite the reference of the approval an organisation was set up with | TH-008 | Two triggers. A sign-in has a person after every change. The type and reference of the set-up approval are changed only by the owner of the tables (`tests/test_people.py`, `tests/test_approvals.py`) |
| A form sent twice at the same moment gave a server error or two customers of one name | TH-007 | The work takes the organisation's row first; a conflict is refused with the reason (`tests/test_approvals.py`, `tests/test_customers.py`) |

Still open after these corrections: the privileges of an approval are not held by the database against the application's own role, so the check of the airworthiness review privilege rests on application code never changing them.

## Added on 27 November 2026

The canvas build, Phase 1 (`prompts/canvas-build.md`): Continuing Airworthiness, the Rest.

| What Was Added | Threat | How It Is Met |
|---|---|---|
| Defects of each aircraft, with who deferred each and its limit, and the action on a repeat defect | TH-008, TH-020, TH-021 | Records like any other: row-level security, history, no delete, and each refers only to an aircraft, a person and work done of its own organisation, by trigger. Recording and closing are POSTs with the forgery token, checked against the role matrix on the server (Record Defect, Record Repeat Defect Action). The decision, who made it and the limit are fixed by the database once recorded, so a signed-in user with the role cannot quietly lengthen a limit or change who deferred a defect; a closed defect is fixed whole (`tests/test_defects.py`) |
| A change of an aircraft's status that the database now refuses | TH-021 | An aircraft with an open defect that is Not Deferrable is not made Serviceable, by a trigger on the aircraft table as well as in the service, so no path through the application can clear it (`tests/test_defects.py`) |
| Contracts with owners and work orders, which hold owners' names and addresses | TH-008, TH-020, TH-021 | Records like any other, each held to an aircraft, a customer, a contract and work done of its own organisation by trigger. What a contract or a work order says is fixed by the database once recorded; an ending and the day the authority was told are each recorded once. Drawing up and ending are for the Continuing Airworthiness Manager, checked on the server (`tests/test_contracts.py`). An owner's address is personal data where the owner is a private person, held inside the organisation's own records as the owner's name already is |
| Certificates of release to service, recorded for work done | TH-008, TH-020, TH-021 | A record like any other, held to work done and a person of its own organisation by trigger. The application's role has no right to change the table at all; what a certificate says of the work, the certifying staff and the approval is written by the database. Recording is a POST with the forgery token, checked against the role matrix on the server (`tests/test_releases.py`). The name and licence number of a pilot-owner or of independent certifying staff are personal data inside the aircraft's record |
| Components, their limits, and each fitting to an aircraft and its removal | TH-008, TH-020, TH-021 | Records like any other: row-level security, history, no delete, and a fitting refers only to a component and an aircraft of its own organisation, by trigger. Every change is a POST with the forgery token, checked against the role matrix on the server (Record Aircraft Configuration). What was recorded of a fitting, and the registration it names, are fixed by the database, so a signed-in user with the role cannot quietly move the hours a component had when fitted; a change of limit is in the history (`tests/test_components.py`) |
| Service bulletin decisions, changes and repairs, weighings and issues of the weight schedule, and the organisation's reweigh threshold | TH-008, TH-020, TH-021 | Records like any other: row-level security, history, no delete, each referring only to an aircraft of its own organisation, by trigger. Every change is a POST with the forgery token, checked against the role matrix on the server (Record Aircraft Configuration; Change Organisation Record for the threshold). A decision on a bulletin and a change or repair are fixed by the database, and a weighing and an issue are insert-only, so a signed-in user with the role cannot quietly alter a mass effect or an owner's decision (`tests/test_modifications.py`) |
| Departures of a programme, its annual review point by point, and the sources checked for directives | TH-008, TH-020, TH-021 | Records like any other: row-level security, history, no delete, each referring only to a programme and a user of its own organisation, by trigger. Every change is a POST with the forgery token, checked against the role matrix on the server (Change Maintenance Programme, Record Maintenance Programme Review, Record Airworthiness Directive). A departure and a completed annual review are fixed by the database, which also writes who completed the review, so a signed-in user cannot alter a justification or put a review under another name (`tests/test_programme_departures.py`) |
| The transfer checklist, the positions of an aircraft's configuration and its signed baseline | TH-008, TH-020, TH-021 | Records like any other: row-level security, history, no delete, each referring only to records of its own organisation, by trigger. Every change is a POST with the forgery token, checked against the role matrix on the server (Add or Change Aircraft, Record Aircraft Configuration, Sign Configuration Baseline). The database refuses a move to the Fleet with an item open and a baseline with a tracked position not recorded, writes what a baseline shows itself, and gives the application no right to change one, so a signed-in user cannot sign over missing records or alter what was signed (`tests/test_configuration.py`) |

## Not Yet Covered

- Email (password reset, notifications): no email flow is designed yet. It is modelled when it is added.
- File attachments (scanned certificates, supporting documents for REQ-112): upload handling and malware scanning are modelled when attachments are designed.
- Corrected 20 November 2026: this said the Coolify server runs other projects. There is no existing server. The diagram above no longer names Coolify, and the hosting account is, for now, the Render account of the test site. If a rented server is shared with anything else, isolation between that and this application is checked at first deployment (`operations/deployment.md`); the build session could not reach the server.
