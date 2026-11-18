# Threat Model

Method: STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege) applied to each data flow of the private beta slice, on the stack accepted in `architecture/decisions/ADR-0001-stack.md`.

Every threat is linked to the requirement that answers it and to a planned test. Test identifiers beginning T-SEC are created in Step 7 and entered in `requirements/traceability.csv`; until a test exists the threat is Open.

Reviewed: 18 November 2026, before any product code. Reviewed again at each step that adds a data flow, and in full at the readiness review.

## What Is Protected

| Asset | Why It Matters |
|---|---|
| Continuing airworthiness records and their history | A lost or altered record means an aircraft's status cannot be shown (ML.A.305, CAO.A.090) |
| Calculated due dates and validity dates | A wrong figure can lead to an overrun (hazards H-001, H-010) |
| Certificates and their serials | A certificate must be traceable and unique (CAP 562 C-90) |
| Separation between organisations | AMC CAO.A.090, AMC CAMO.A.220 |
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
| TH-080 | Information Disclosure | Export of another organisation's aircraft | High | Export runs through the same data-layer scoping; export is a logged event | REQ-003, REQ-134, REQ-009 | T-SEC-010 includes export endpoints |
| TH-081 | Tampering | Exported file altered after export and presented as the record | Medium | Export carries the event hash chain and a checksum, so it can be verified against the system | REQ-134 | T-SEC-019 altered export fails verification |
| TH-082 | Information Disclosure | Formula injection when a CSV export is opened in a spreadsheet | Low | Cells beginning with =, +, - or @ are neutralised in CSV | REQ-134 | T-SEC-020 |

## Design Additions From This Model

These go beyond ADR-0001 and are adopted here:

1. Each event carries a hash chained to the previous event of the same record (TH-021, TH-025, TH-081).
2. The application's storage credentials can add backups but not delete them (TH-041).
3. Database migrations run under a separate database user from the application (TH-024).

## Not Yet Covered

- Email (password reset, notifications): no email flow is designed yet. It is modelled when it is added.
- File attachments (scanned certificates, supporting documents for REQ-112): upload handling and malware scanning are modelled when attachments are designed.
- The server's other services: the Coolify server runs other projects that are not to be touched. Isolation between them and this application is checked in Step 8.
