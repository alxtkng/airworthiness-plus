# OWASP Application Security Verification Standard 5.0: Level and Results

Step 7 of private beta. Date: 19 November 2026, brought up to date the same day after Step 8. Standard: OWASP Application Security Verification Standard 5.0.0, read from the OWASP repository (github.com/OWASP/ASVS, folder `5.0/en`) on 19 November 2026.

The standard is published under the Creative Commons Attribution-ShareAlike 4.0 licence. Its requirements are not copied here: each is given by its number, and the text is in the standard.

## Level

**Level 2.** Ours, to be confirmed by Alex King.

The standard has three levels. It says of Level 1 that it holds the minimum, first-layer requirements; of Level 2 that most applications should be striving for it; and of Level 3 that it is the goal for applications looking to demonstrate the highest levels of security, with a bank as its example.

- Level 1 is too little. The records decide whether an aircraft may fly, they must be shown to be unaltered (CAO.A.090(d), CAP 562 C-90), and the system holds the records of more than one organisation. Level 1 leaves out multi-factor sign-in, session time limits, the Content Security Policy and almost all logging.
- Level 2 fits. It adds the protections against less common attacks, and the documentation and logging an organisation needs in order to describe the system in its exposition and to investigate an event.
- Level 3 is not chosen now. Much of it is defence in depth that needs hardware-backed sign-in, a key vault and separate systems for logs, which a single small server does not have. Some Level 3 requirements are already met because the record rules ask for them, such as logging every refused action and history that cannot be changed; they are not assessed here. Level 3 is looked at again before records of commercial operators are held.

Level 2 means every Level 1 and Level 2 requirement: 70 and 183, 253 in all, of the standard's 345.

## Results

| Result | Meaning | Requirements |
|---|---|---|
| Met | Shown by a test, or by the code and settings named | 141 |
| Partly Met | Met in part; what is missing is stated | 4 |
| Not Met | Not met today; what is needed is stated | 2 |
| To Be Verified at Deployment | Depends on the server or the reverse proxy. The service is not yet deployed. Each is listed with its check in `operations/deployment.md` | 17 |
| Not Applicable | The application has nothing of the kind | 89 |
| Total | | 253 |

The level is not yet met. It is met when every row below is Met or Not Applicable, or Alex King has accepted what remains. The readiness review checks this.

### Not Met and Partly Met

| Requirement | Result | What Is Missing | Where It Goes |
|---|---|---|---|
| 6.2.12 | Partly Met | Checked against the 20,000 most common passwords, which come from breaches. A full set of breached passwords is not checked: it needs either a large file kept up to date or a request to another service | Accepted for private beta on 19 November 2026 (`design-system/Decisions.md`); looked at again before public beta |
| 11.1.1 | Partly Met | `operations/keys-and-secrets.md` gives the rules and when each key is replaced. It has not been set against a named key management standard | To be settled before customer data; in the readiness review |
| 11.4.1 | Partly Met | SHA-256 for the history chain, checksums and signatures of sessions. One-time codes use HMAC-SHA-1, which the standard lists as legacy and allows for compatibility: it is what RFC 6238 defaults to and what authenticator applications support. Passkeys would remove it | Accepted for private beta on 19 November 2026 (`design-system/Decisions.md`); looked at again before public beta |
| 13.3.1 | Not Met | Secrets are environment values on the server, not in a vault. A decision for private beta, with its reasons, in `operations/keys-and-secrets.md`; to be weighed again before customer data | To be settled before customer data; in the readiness review |
| 14.2.4 | Partly Met | Met except for two things the classification asks for. Second-factor keys are not encrypted in the database: decided on 19 November 2026 not to in private beta, because with the key on the same server it would protect only a backup, which is already encrypted (`operations/keys-and-secrets.md`). No period is set for keeping the access log | To be settled before customer data; in the readiness review |
| 16.4.3 | Not Met | The history and the access log leave the server once a day in the backup. The server and proxy logs stay on the one server (`operations/monitoring.md`). To be decided before customer data | To be settled before customer data; in the readiness review |

## V1 Encoding and Sanitization

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 1.1.1 | 2 | Met | Django decodes a request once; the application decodes nothing again |
| 1.1.2 | 2 | Met | Templates escape at output; SQL values are bound by the driver |
| 1.2.1 | 1 | Met | Template auto-escaping throughout; the one use of `format_html` is the status mark. `test_security: hostile_text_is_stored_and_shown_as_text` |
| 1.2.2 | 1 | Met | Addresses are built by `{% url %}` from record identifiers; no address supplied by a user is ever linked |
| 1.2.3 | 1 | Met | No JavaScript or JSON is built into a page from data. Export JSON is written by the standard library |
| 1.2.4 | 1 | Met | The query layer and bound parameters only. SQL in migrations is fixed text with checked identifiers (`history/sql.py`) |
| 1.2.5 | 1 | Not Applicable | No operating system command is run |
| 1.2.6 | 2 | Not Applicable | No LDAP |
| 1.2.7 | 2 | Not Applicable | No XPath |
| 1.2.8 | 2 | Not Applicable | No LaTeX |
| 1.2.9 | 2 | Met | Every regular expression is fixed text; input is matched, never used as a pattern |
| 1.3.1 | 1 | Not Applicable | No HTML is accepted as input |
| 1.3.2 | 1 | Met | No `eval`, `exec` or dynamic code |
| 1.3.3 | 2 | Met | Export file names are built from letters, digits and hyphens only; CSV cells are neutralised (`test_exports`, T-SEC-020); every field has a length limit |
| 1.3.4 | 2 | Not Applicable | No SVG is accepted |
| 1.3.5 | 2 | Not Applicable | No Markdown, stylesheet or template language is accepted |
| 1.3.6 | 2 | Not Applicable | The application makes no request to any other service |
| 1.3.7 | 2 | Met | Templates are files of the application; input is never compiled as a template (`test_security`) |
| 1.3.8 | 2 | Not Applicable | No JNDI |
| 1.3.9 | 2 | Not Applicable | No memcache |
| 1.3.10 | 2 | Met | No format string comes from input |
| 1.3.11 | 2 | Not Applicable | No mail is sent |
| 1.4.1 | 2 | Not Applicable | Python; no unmanaged code of ours |
| 1.4.2 | 2 | Not Applicable | Python integers do not overflow; column ranges are enforced by the database |
| 1.4.3 | 2 | Not Applicable | Python; no manual memory management |
| 1.5.1 | 1 | Not Applicable | No XML is parsed |
| 1.5.2 | 2 | Met | Only JSON and CSV are parsed. Sessions use Django's JSON serializer. No pickle |

## V2 Validation and Business Logic

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 2.1.1 | 1 | Met | `requirements/requirements.md` and `design-system/Decisions.md`: entries of hours and cycles, import file layouts, dates |
| 2.1.2 | 2 | Met | Decisions.md: an entry against the entries around it; certificate dates; extension conditions |
| 2.1.3 | 2 | Met | Decisions.md: sign-in lock, import of 1 megabyte and 2,000 rows, forms of 1 megabyte |
| 2.2.1 | 1 | Met | Forms, then the services, then database constraints |
| 2.2.2 | 1 | Met | All validation is on the server, in the services and the database. None is in the browser |
| 2.2.3 | 2 | Met | `airworthiness_rules.utilisation`; database constraints on records that go together. For REQ-301, access is checked on each evidence entry and withdrawal, with organisation scope at both parent links |
| 2.3.1 | 1 | Met | Password before code (`test_sign_in: the_code_pages_need_an_accepted_password`); first password changed before any page; certificate only from a completed review |
| 2.3.2 | 2 | Met | As documented: lock after 5 failures; size limits |
| 2.3.3 | 2 | Met | Each request is one transaction (REQ-138); an import loads whole or not at all |
| 2.3.4 | 2 | Met | Certificate serials are allocated one at a time under a database lock (T-SEC-017) |
| 2.4.1 | 2 | To Be Verified at Deployment | Sign-in is locked after 5 failures and requests are limited in size. The limit on the rate of requests is set at the reverse proxy (`operations/deployment.md`) |

## V3 Web Frontend Security

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 3.2.1 | 1 | Met | `X-Content-Type-Options: nosniff`, a content type on every response, exports sent as attachments, and a policy that loads nothing by default |
| 3.2.2 | 1 | Met | The one script copies nodes the server has already escaped and sets `textContent`; it never writes HTML |
| 3.3.1 | 1 | Met | `__Host-` cookies, Secure (`test_security: cookies_are_for_this_host_over_https_and_hidden_from_scripts`) |
| 3.3.2 | 2 | Met | SameSite Lax on both cookies; every write also needs the forgery token |
| 3.3.3 | 2 | Met | `__Host-sessionid`, `__Host-csrftoken` |
| 3.3.4 | 2 | Met | Both cookies are HttpOnly; the session identifier is sent only in Set-Cookie |
| 3.4.1 | 1 | Met | One year, including subdomains (`test_security`) |
| 3.4.2 | 1 | Not Applicable | No cross-origin sharing header is sent |
| 3.4.3 | 2 | Met | `interface/security.py`; no `unsafe-inline`, no wildcard (`test_security: every_response_carries_the_security_headers`) |
| 3.4.4 | 2 | Met | On every response |
| 3.4.5 | 2 | Met | `Referrer-Policy: same-origin` |
| 3.4.6 | 2 | Met | `frame-ancestors 'none'` on every response |
| 3.5.1 | 1 | Met | Django's forgery token on every POST (`test_security: every_write_refuses_a_forged_request`) |
| 3.5.2 | 1 | Not Applicable | The application does not rely on the preflight mechanism |
| 3.5.3 | 1 | Met | Every write is a POST, including sign-out and export (`test_security: nothing_is_changed_by_a_get`). One exception by design: the key of a second factor is made when its set-up page is first shown, after the password has been accepted |
| 3.5.4 | 2 | To Be Verified at Deployment | The service is to have a host name of its own, apart from every other project on the server |
| 3.5.5 | 2 | Not Applicable | No `postMessage` |
| 3.7.1 | 2 | Met | HTML, CSS and one script |
| 3.7.2 | 2 | Met | Every redirect is to an address of the application; the `next` value at sign-in is not followed |

## V4 API and Web Service

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 4.1.1 | 1 | Met | `text/html; charset=utf-8` on pages; `application/zip` on exports |
| 4.1.2 | 2 | Met | Every address is for a person in a browser; there is no interface for programs |
| 4.1.3 | 2 | To Be Verified at Deployment | The application takes only the last forwarded address, and only when told it is behind a proxy. That the proxy overwrites the forwarded headers is checked on the server |
| 4.2.1 | 2 | To Be Verified at Deployment | The reverse proxy and the application server, chosen in Step 8 |
| 4.3.1 | 2 | Not Applicable | No GraphQL |
| 4.3.2 | 2 | Not Applicable | No GraphQL |
| 4.4.1 | 1 | Not Applicable | No WebSocket |
| 4.4.2 | 2 | Not Applicable | No WebSocket |
| 4.4.3 | 2 | Not Applicable | No WebSocket |
| 4.4.4 | 2 | Not Applicable | No WebSocket |

## V5 File Handling

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 5.1.1 | 2 | Met | Decisions.md, Import: CSV in UTF-8, name ending .csv, 1 megabyte, 2,000 rows. The export describes itself in its README |
| 5.2.1 | 1 | Met | 1 megabyte (`test_imports`) |
| 5.2.2 | 1 | Met | The name ends .csv and the content must be UTF-8 CSV with the exact column headings, or it is refused |
| 5.2.3 | 2 | Not Applicable | No compressed file is accepted. `verify_export` is run by hand on a file the operator chooses |
| 5.3.1 | 1 | Not Applicable | An uploaded file is not stored; the values in it are |
| 5.3.2 | 1 | Met | The name of an uploaded file is kept as text and never used as a path |
| 5.4.1 | 2 | Met | The export file name is made by the application |
| 5.4.2 | 2 | Met | Letters, digits and hyphens only |
| 5.4.3 | 2 | Not Applicable | No uploaded file is served back |

## V6 Authentication

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 6.1.1 | 1 | Met | Decisions.md, Sign-in |
| 6.1.2 | 2 | Met | `accounts/passwords.py` |
| 6.1.3 | 2 | Not Applicable | One way in |
| 6.2.1 | 1 | Met | 12 characters |
| 6.2.2 | 1 | Met | Change Password |
| 6.2.3 | 1 | Met | `test_users: a_first_password_is_changed_before_anything_else` |
| 6.2.4 | 1 | Met | Django's list of 20,000 common passwords |
| 6.2.5 | 1 | Met | No rule on which characters are used |
| 6.2.6 | 1 | Met | Every password field is `type=password` |
| 6.2.7 | 1 | Met | Nothing prevents pasting or a password manager |
| 6.2.8 | 1 | Met | Passwords are not trimmed or changed in case |
| 6.2.9 | 2 | Met | Up to 200 characters |
| 6.2.10 | 2 | Met | No expiry by time |
| 6.2.11 | 2 | Met | `test_security: a_password_is_not_built_on_a_word_anyone_would_try` |
| 6.2.12 | 2 | Partly Met | Checked against the 20,000 most common passwords, which come from breaches. A full set of breached passwords is not checked: it needs either a large file kept up to date or a request to another service |
| 6.3.1 | 1 | Met | `test_sign_in: five_failures_lock_the_name_for_15_minutes`, `wrong_codes_count_towards_the_lock` |
| 6.3.2 | 1 | Met | No default account; the first Administrator is made when the organisation is set up |
| 6.3.3 | 2 | Met | A password and a code from an authenticator application, for every user |
| 6.3.4 | 2 | Met | One way in (`test_sign_in: a_password_alone_signs_nobody_in`) |
| 6.4.1 | 1 | Met | A first password is made by the system from the operating system's random source, passes the password rules, is shown once, works for 7 days and is changed before any page answers (`test_users: a_first_password_stops_working_after_7_days, a_first_password_is_changed_before_anything_else`) |
| 6.4.2 | 1 | Met | None |
| 6.4.3 | 2 | Met | The Administrator sets a new first password; the second factor is still asked for |
| 6.4.4 | 2 | Met | `operations/user-administration.md`: a lost authenticator is reset only after the person is identified as carefully as when first given access; the reset ends their sessions and is logged |
| 6.5.1 | 2 | Met | The step of each accepted code is logged and never accepted again (`test_sign_in: a_wrong_code_and_a_used_code_are_refused`) |
| 6.5.2 | 2 | Not Applicable | No lookup secrets |
| 6.5.3 | 2 | Met | 160 bits from the operating system (`test_totp`) |
| 6.5.4 | 2 | Not Applicable | No lookup secrets or out-of-band codes |
| 6.5.5 | 2 | Met | 30 seconds (`test_totp: a_code_is_accepted_for_its_own_30_seconds_and_no_longer`) |
| 6.6.1 | 2 | Not Applicable | No codes by telephone or text message |
| 6.6.2 | 2 | Not Applicable | No out-of-band codes |
| 6.6.3 | 2 | Not Applicable | No out-of-band codes. Codes from the authenticator count towards the lock |
| 6.8.1 | 2 | Not Applicable | No identity provider |
| 6.8.2 | 2 | Not Applicable | No identity provider |
| 6.8.3 | 2 | Not Applicable | No identity provider |
| 6.8.4 | 2 | Not Applicable | No identity provider |

## V7 Session Management

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 7.1.1 | 2 | Met | ADR-0005 sets 30 minutes idle, or 60 minutes in a managed-device-only deployment, and 12 hours overall. These are within NIST SP 800-63B-4 AAL2's recommended limits |
| 7.1.2 | 2 | Met | Decisions.md, Security settings: not limited; a user can end the others |
| 7.1.3 | 2 | Not Applicable | No federation |
| 7.2.1 | 1 | Met | Sessions are held in the database and checked on every request |
| 7.2.2 | 1 | Met | A reference token made at each sign-in |
| 7.2.3 | 1 | Met | Django session keys: 32 characters of 36, from the operating system's random source |
| 7.2.4 | 1 | Met | `test_sign_in: the_session_cookie_is_secure_and_changes_at_sign_in` and `test_passkeys: test_passkey_registration_and_revocation_need_recent_verification` cover session key rotation |
| 7.3.1 | 2 | Met | `test_sign_in: a_session_ends_after_30_minutes_without_a_request` and `test_passkeys: test_idle_limits_are_server_side` |
| 7.3.2 | 2 | Met | `test_sign_in: a_session_ends_12_hours_after_sign_in_however_busy` |
| 7.4.1 | 1 | Met | `test_sign_in: sign_out_ends_the_session_on_the_server` |
| 7.4.2 | 1 | Met | `test_users: a_user_made_inactive_is_signed_out_and_stays_in_the_record` |
| 7.4.3 | 2 | Met | Changing the password or removing a passkey ends other sessions. Resetting the second factor revokes all registered passkeys and ends every session |
| 7.4.4 | 2 | Met | Sign Out is in the sidebar of every page |
| 7.4.5 | 2 | Met | End Sessions of a user, on the Users page (`test_security: a_users_sessions_can_all_be_ended`) |
| 7.5.1 | 2 | Met | Passkey changes and account recovery require recent full verification with a passkey or the password and an authenticator code. See ADR-0005, `test_passkeys` and `test_users` |
| 7.5.2 | 2 | Met | The Change Password page lists the user's live sessions: when each began, when it was last used, where from and in what browser. One is ended, or every other, after a sign-in within the last 5 minutes or a code (`test_users: a_user_sees_their_sessions_and_ends_one, ending_a_session_needs_a_code_unless_just_signed_in`) |
| 7.6.1 | 2 | Not Applicable | No identity provider |
| 7.6.2 | 2 | Met | A session is made only by signing in |

## V8 Authorization

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 8.1.1 | 1 | Met | Decisions.md, Roles and Permissions: 21 actions against 5 roles; every record belongs to one organisation |
| 8.1.2 | 2 | Met | `architecture/fields-by-action.md`: what each role reads, every address that sets something with its action, roles and the values it accepts, the values no action sets, and those fixed by the state of the record. Its table is written from the forms and addresses, and a test fails if it falls behind (`test_roles: the_document_is_what_the_code_says`) |
| 8.2.1 | 1 | Met | `requires(Action)` on every view; each module's test of the role matrix (T-SEC-011) |
| 8.2.2 | 1 | Met | Row-level security in the database, keyed to the session's organisation; each module's test as another organisation (T-SEC-010) |
| 8.2.3 | 2 | Met | A form sets only its own fields; records that are fixed are fixed by database triggers |
| 8.3.1 | 1 | Met | On the server and again in the database; nothing is decided in the browser |
| 8.4.1 | 2 | Met | ADR-0002; `test_data_layer`; T-SEC-010 on every module |

## V9 Self-contained Tokens

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 9.1.1 | 1 | Not Applicable | No self-contained tokens; a session is a reference held by the server |
| 9.1.2 | 1 | Not Applicable | No self-contained tokens; a session is a reference held by the server |
| 9.1.3 | 1 | Not Applicable | No self-contained tokens; a session is a reference held by the server |
| 9.2.1 | 1 | Not Applicable | No self-contained tokens |
| 9.2.2 | 2 | Not Applicable | No self-contained tokens |
| 9.2.3 | 2 | Not Applicable | No self-contained tokens |
| 9.2.4 | 2 | Not Applicable | No self-contained tokens |

## V10 OAuth and OIDC

Not Applicable: No OAuth or OpenID Connect: the application is neither a client nor a server of either. Requirements 10.1.1 to 10.7.3 at Levels 1 and 2, 29 in all.

## V11 Cryptography

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 11.1.1 | 2 | Partly Met | `operations/keys-and-secrets.md` gives the rules and when each key is replaced. It has not been set against a named key management standard |
| 11.1.2 | 2 | Met | `operations/keys-and-secrets.md`, Inventory |
| 11.2.1 | 2 | Met | Python's `hashlib`, `hmac` and `secrets`, Django's password hashers, PostgreSQL's `sha256` |
| 11.2.2 | 2 | Met | Django upgrades a password hash at sign-in when the settings change. Each entry of the history names how it was hashed, so the method can change and earlier entries still be checked (`test_data_layer: every_entry_names_how_it_was_hashed`); the export carries a format version. Keys are replaced as `operations/keys-and-secrets.md` says |
| 11.2.3 | 2 | Met | SHA-256 throughout; 160-bit keys for one-time codes |
| 11.3.1 | 1 | Not Applicable | The application encrypts nothing itself |
| 11.3.2 | 1 | Not Applicable | The application encrypts nothing itself |
| 11.3.3 | 2 | Not Applicable | The application encrypts nothing itself |
| 11.4.1 | 1 | Partly Met | SHA-256 for the history chain, checksums and signatures of sessions. One-time codes use HMAC-SHA-1, which the standard lists as legacy and allows for compatibility: it is what RFC 6238 defaults to and what authenticator applications support. Passkeys would remove it |
| 11.4.2 | 2 | Met | PBKDF2-HMAC-SHA-256, 1,000,000 iterations; the standard asks for at least 600,000 |
| 11.4.3 | 2 | Met | SHA-256 |
| 11.4.4 | 2 | Not Applicable | No key is derived from a password |
| 11.5.1 | 2 | Met | Session identifiers, forgery tokens and second-factor keys come from the operating system's random source. Record identifiers are random too, but access never depends on their being secret (threat TH-006) |
| 11.6.1 | 2 | Not Applicable | No public key cryptography in the application |

## V12 Secure Communication

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 12.1.1 | 1 | To Be Verified at Deployment | Set at the reverse proxy |
| 12.1.2 | 2 | To Be Verified at Deployment | Set at the reverse proxy |
| 12.1.3 | 2 | Not Applicable | No client certificates |
| 12.2.1 | 1 | Met | Plain HTTP is redirected and Strict Transport Security is sent (T-SEC-008). The proxy's side is checked on the server |
| 12.2.2 | 1 | To Be Verified at Deployment | A publicly trusted certificate at the reverse proxy |
| 12.3.1 | 2 | To Be Verified at Deployment | The database, backups and remote access, in Step 8 |
| 12.3.2 | 2 | To Be Verified at Deployment | The backup tool is the only client; the application makes no outbound connection |
| 12.3.3 | 2 | To Be Verified at Deployment | Proxy to application, and application to database, on the server's private network. Whether that is encrypted is decided in Step 8 |
| 12.3.4 | 2 | To Be Verified at Deployment | As 12.3.3 |

## V13 Configuration

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 13.1.1 | 2 | Met | `operations/system-description.md`: the service connects to its own database and to nothing else |
| 13.2.1 | 2 | To Be Verified at Deployment | The database account and its password |
| 13.2.2 | 2 | Met | The application's database role owns nothing, cannot delete and is under row-level security (ADR-0002) |
| 13.2.3 | 2 | To Be Verified at Deployment | No default credential; checked on the server |
| 13.2.4 | 2 | To Be Verified at Deployment | The application needs no outbound connection; the server's firewall should allow it none |
| 13.2.5 | 2 | To Be Verified at Deployment | As 13.2.4 |
| 13.3.1 | 2 | Not Met | Secrets are environment values on the server, not in a vault. A decision for private beta, with its reasons, in `operations/keys-and-secrets.md`; to be weighed again before customer data |
| 13.3.2 | 2 | To Be Verified at Deployment | Who can read the server's environment values |
| 13.4.1 | 1 | Met | The pipeline builds the image on every change and fails if it holds a `.git` folder |
| 13.4.2 | 2 | Met | Debug is off unless switched on by an environment value (`test_security: an_error_page_says_nothing_of_the_inside`) |
| 13.4.3 | 2 | Met | No directory listing is served |
| 13.4.4 | 2 | Met | `test_security: a_method_the_application_does_not_use_is_refused` |
| 13.4.5 | 2 | Met | No documentation or monitoring address is exposed; there is no administration interface (T-SEC-018) |

## V14 Data Protection

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 14.1.1 | 2 | Met | `operations/data-protection/record-of-processing.md`: Secret, Personal, Safety Records |
| 14.1.2 | 2 | Met | The same document, Protection Required for Each Level |
| 14.2.1 | 1 | Met | Addresses hold record identifiers only; passwords, codes and tokens travel in the body or a cookie |
| 14.2.2 | 2 | Met | `Cache-Control: no-store` on everything but static files; the application keeps no cache |
| 14.2.3 | 2 | Met | No page asks anything of another site (`test_interface`) |
| 14.2.4 | 2 | Partly Met | Met except for two things the classification asks for. Second-factor keys are not encrypted in the database: decided on 19 November 2026 not to in private beta, because with the key on the same server it would protect only a backup, which is already encrypted (`operations/keys-and-secrets.md`). No period is set for keeping the access log |
| 14.3.1 | 1 | Met | `Clear-Site-Data` at sign-out; the application puts nothing in browser storage |
| 14.3.2 | 2 | Met | `test_security: every_response_carries_the_security_headers` |
| 14.3.3 | 2 | Met | Two cookies: the session identifier and the forgery token |

## V15 Secure Coding and Architecture

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 15.1.1 | 1 | Met | `operations/vulnerability-management.md`: 14 days for High, 30 for Medium; dependencies refreshed monthly |
| 15.1.2 | 2 | Met | `uv.lock` with hashes; a CycloneDX bill of materials from every pipeline run; the font files recorded with their checksums |
| 15.1.3 | 2 | Met | `operations/system-description.md`, What Takes Time or Resources |
| 15.2.1 | 1 | Met | `pip-audit` fails the pipeline on a known vulnerability; the time frames are in `operations/vulnerability-management.md` |
| 15.2.2 | 2 | To Be Verified at Deployment | `operations/system-description.md`, What Takes Time or Resources: imports and forms are limited in size, sign-in is locked, and the export of an organisation is limited to 6 in an hour (`test_exports: the_export_of_an_organisation_is_limited_to_6_in_an_hour`). The limit on the rate of requests is set at the reverse proxy (`operations/deployment.md`) |
| 15.2.3 | 2 | Met | No administration interface, no debug pages, no sample code |
| 15.3.1 | 1 | Met | A page shows the fields chosen for it; the export leaves out the password and the second-factor key (`test_exports`) |
| 15.3.2 | 2 | Not Applicable | The application calls no other address |
| 15.3.3 | 2 | Met | Each form names its fields; nothing is set from a request by name |
| 15.3.4 | 2 | Met | `test_security: the_address_of_a_request_is_what_the_proxy_saw`. The proxy's side is checked on the server |
| 15.3.5 | 2 | Met | Typed Python checked by mypy in strict mode; hours are decimals and dates are dates |
| 15.3.6 | 2 | Met | The one script uses no object as a map of names taken from data |
| 15.3.7 | 2 | Met | A view reads named fields from the body of a POST only |

## V16 Security Logging and Error Handling

| Requirement | Level | Result | Evidence or Reason |
|---|---|---|---|
| 16.1.1 | 2 | Met | `operations/monitoring.md`, Logs |
| 16.2.1 | 2 | Met | Access log: who, when, what and from where. History: who, when, what, before and after |
| 16.2.2 | 2 | Met | The database clock and the server log are in Coordinated Universal Time. That the server's clock is kept right is checked on the server |
| 16.2.3 | 2 | Met | The application writes to the database and to standard output only, as the inventory says |
| 16.2.4 | 2 | Met | One line for each event, in one format |
| 16.2.5 | 2 | Met | No password, code or session identifier is logged; the step of a code is, not the code |
| 16.3.1 | 2 | Met | Every sign-in, failure, lock, set-up, reset and sign-out, with which step failed |
| 16.3.2 | 2 | Met | Every refused action (`Action Refused`) |
| 16.3.3 | 2 | Met | Refused actions and failed sign-ins in the access log; forged requests and oversized requests in the server log |
| 16.3.4 | 2 | Met | Unexpected errors go to the server log |
| 16.4.1 | 2 | Met | Access log values are stored as values, never as text of a query; Django writes a request path into its log in escaped form |
| 16.4.2 | 2 | Met | The application can add to the access log and the history and cannot change or remove either; the database refuses (T-SEC-014) |
| 16.4.3 | 2 | Not Met | The history and the access log leave the server once a day in the backup. The server and proxy logs stay on the one server (`operations/monitoring.md`). To be decided before customer data |
| 16.5.1 | 2 | Met | `test_security: an_error_page_says_nothing_of_the_inside` |
| 16.5.2 | 2 | Met | The only outside resource is the database; if it fails, the request fails with a plain error and nothing is written |
| 16.5.3 | 2 | Met | Any error rolls back the whole request (REQ-138) |

## V17 WebRTC

Not Applicable: No WebRTC. Requirements 17.1.1 to 17.3.2 at Levels 1 and 2, 7 in all.

## How This Was Done

Each requirement was read in the standard and set against the code, the settings and the tests on 19 November 2026, by the same session that wrote the code. That is a self-assessment, not an independent one. The external penetration test (`assurance/penetration-test-scope.md`, Issue 40) is the independent check.

Reading the standard led to changes made before this record was written: the Content Security Policy and the other response headers, cookie names, one-time codes good for 30 seconds only, the list of words a password may not contain, ending of sessions, logging of errors, and the removal of the rule against passwords made of digits alone.


## Work package routes

The package and card forms use the existing role checks, CSRF controls and the generated fields-by-action inventory (8.1.2). PostgreSQL applies organisation scope and cross-record validation. Work card evidence and issue and release history are retained (16.2.2 and 16.4.2). The browser scenario covers the form sequence. The database suite verifies row scope and reference protection.


Staffing Plan routes use the generated action and field inventory (8.1.2). The hourly plan and absence inputs have date and numeric validation. Reviews and reports are insert-only with tenant scoping and hashed history (16.2.2 and 16.4.2).

Roster and Planning Settings actions are listed in the fields-by-action inventory (8.1.2). Withdrawal, publication and handover evidence is retained. The acknowledgement binds to the sign-in of the named recipient (16.2.2, 16.4.2).

## Supplier routes

Supplier routes reuse CSRF protection and server-side role checks, with generated fields-by-action entries (8.1.2). The database scopes the supplier and approval, and retains evaluation history and audit events (16.2.2 and 16.4.2).

Maintenance subcontractor assessments use the role and field inventory (8.1.2), scoped references, and append-only history (16.2.2 and 16.4.2).

Goods In uses the generated action and field inventory (8.1.2), server-side role checks and CSRF protection. PostgreSQL validates organisation scope and dates, serializes intake decisions per receipt, and retains append-only observations and disposition evidence in hashed history (16.2.2 and 16.4.2).

Stores PR 1 (REQ-358) adds six write routes to the generated action and field inventory (8.1.2), each behind a server-side role check, CSRF protection and the maintenance approval check. Quantities are parsed as exact decimals and refused, never rounded, outside the unit scale and range (2.2.1). PostgreSQL enforces organisation scope and parent links, one posting per disposition, the lot lock and non-negative balances, and keeps every resolution, posting, count and movement append-only in hashed history (8.2.2, 16.2.2 and 16.4.2). Concurrent sessions are tested against committed PostgreSQL transactions (15.4.2).

### Tool register and control evidence

REQ-360 to REQ-363 add the register, control and delegation surfaces. The field inventory maps each POST to its allowed values and role (8.1.2). The service checks the linked person, action, approval, dated authority and site. The database checks tenant boundaries and consistency of the tool, basis and delegation (8.2, 8.3). Session-bound CSRF validation applies to every write. Hashed, attributable record history and the existing export verification cover retained decisions and retries (16.2.2 and 16.4.2). The tooling service, database, browser and export tests exercise the new surface.

The calibration service provider, order, movement, certificate, result, acceptance and reinstatement routes extend the fields-by-action inventory (8.1.2). Scoped delegations and business parent links are checked at the service and database layers. The existing session and CSRF controls protect browser writes. Evidence, acceptance and case records retain hashed history (16.2.2 and 16.4.2). The case insert is restricted to the result trigger, with an injected-failure test for transactional rollback.
