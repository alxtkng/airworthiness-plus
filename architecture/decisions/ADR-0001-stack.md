# ADR-0001: Technology Stack

Status: **Accepted by Alex King, 18 November 2026** (Issue #26).

Date: 18 November 2026

## Context

Airworthiness+ private beta builds one slice: the Part-CAO core loop for Part-ML aircraft (`requirements/requirements.md`). The stack has to serve these facts:

- One founder maintains it, and he is new to software delivery. Fewer moving parts and fewer dependencies matter more than fashion.
- The records are safety records. The design rules are fixed (`prompts/private-beta.md`, Step 4): append-only history, nothing deleted, organisation scoping in the data layer, explicit date handling, server-allocated certificate serials, complete export in an open format.
- Calculations must be verifiable by a second party who has not seen the implementation, and by property-based tests (REQ-042 to REQ-048, REQ-100 to REQ-113).
- Hosting is the existing Coolify server at [address withheld], domain airworthiness.co. No DNS or email record changes.
- Every dependency is a supply-chain risk to be scanned, pinned and listed in a software bill of materials (NCSC Software Security Code of Practice 1.2; NIST SP 800-218).
- The interface is dense tables that expand on click, not a rich client application (`design-system/README.md`).
- The existing scripts in `scripts/` are Python.

## Options

### Option A. Python, Django, PostgreSQL, server-rendered pages

One application. Django renders HTML on the server; a small script (htmx) loads a row's detail when it is expanded. PostgreSQL holds the data and enforces the record rules itself.

- For: one language and one deployable thing. Django includes sign-in, sessions, permissions, database migrations and protection against the common web attacks, so few third-party packages are needed. A long record of security releases on a published schedule. PostgreSQL row-level security enforces organisation scoping below the application (REQ-003), and database permissions and triggers make history tables append-only whatever the application does (REQ-130, REQ-131). Hypothesis is the established property-based testing library. Exact decimal and date types are in the standard library (REQ-028, REQ-137).
- Against: Python type checking is optional and has to be enforced in continuous integration. Server-rendered pages are less fluid than a client application, which the design does not ask for. Geist components are published for React, so the components in `design-system/Components.md` are rebuilt as templates and CSS from `tokens.json`.

### Option B. TypeScript, Next.js, PostgreSQL

A React application with server routes.

- For: Geist's own components and font come from this ecosystem. Types across client and server.
- Against: several hundred transitive packages even for a small application, which is the largest supply-chain surface of the options. Frequent breaking releases. Sign-in, permissions and migrations each come from a separate package to choose, pin and track. Two runtimes to reason about (browser and server). More to maintain for one founder, for an interface that is mostly tables.

### Option C. A hosted backend (Supabase) with a thin front end

- For: quick start; sign-in and row-level security provided.
- Against: the records would live on a third party's platform outside the Coolify server, which adds a processor to the data protection record and a dependency to the availability claim. Business rules end up split between database policies and client code, which is hard to test as one system. Leaving later is a migration, which is hazard H-008.

### Option D. Go or Rust, PostgreSQL

- For: one static binary, strong types, few dependencies.
- Against: sign-in, permissions, migrations, forms and an administration interface are all hand-built or assembled. Slower to build and more original security-relevant code to verify, for one founder.

## Decision

Option A.

| Layer | Choice | Reason |
|---|---|---|
| Language | Python, a version in security support, pinned | Standard library decimal and date types; the existing scripts |
| Framework | Django 5.2 LTS, moving to 6.2 LTS after its release in April 2027 | 5.2 has security support to April 2028 (djangoproject.com/download) |
| Database | PostgreSQL, a version in support, pinned | Row-level security, sequences, constraints and triggers enforce the record rules in the data layer |
| Pages | Django templates, CSS built from `design-system/tokens.json`, Geist font files served from the application, htmx for expand on click | No build chain for the interface; no third-party requests from the browser |
| Calculations | A separate pure Python package, `airworthiness_rules`, with no Django or database imports: dates, intervals, next due, review validity, recency | Can be tested, property-tested and independently recomputed on its own |
| Tests | pytest, Hypothesis | Golden cases and property-based tests |
| Checks | mypy in strict mode, ruff, pip-audit, detect-secrets, CycloneDX software bill of materials exported by uv | Step 5 pipeline. Amended 18 November 2026: detect-secrets replaces gitleaks so that every tool is installed from the lock file with verified hashes |
| Dependencies | uv, with a lock file that pins versions and hashes | Pinned dependencies (Step 5) |
| Continuous integration | GitHub Actions | Runs on every pull request; free for this scale |
| Deployment | One Docker image, deployed by Coolify from `main` to the existing server | Uses the server as it is; nothing else on it is touched |
| Backup | PostgreSQL base backups with continuous archiving, encrypted, to storage off the server | REQ-150, REQ-151. The storage is a paid service: Alex's decision, Issue #27 |
| Export | JSON with a published schema, plus CSV for tables | Open format (REQ-134); seeds the open data standard |

### How the Fixed Design Rules Are Met

| Rule | Mechanism |
|---|---|
| Append-only history | Every change is written as an event row: who, when, what, before, after. The application's database user has INSERT and SELECT only on event tables. A trigger refuses UPDATE and DELETE even for a more privileged user |
| Nothing deleted | Records have no delete operation. Supersession is an event |
| Organisation scoping in the data layer | Every table carries the organisation. PostgreSQL row-level security policies compare it with the organisation set on the database session for the signed-in user. A query with no organisation set returns nothing |
| Dates | Timestamps stored in Coordinated Universal Time. Regulatory dates stored as dates with no time. "Today" is the current date in Europe/London. Rules written once in `airworthiness_rules` |
| Certificate serials | A PostgreSQL sequence for each organisation and certificate type, with a uniqueness constraint. Allocated in the same transaction as the certificate. Voided serials stay allocated |
| Export | Generated from the event history. A test fails the build if a record type exists that the export does not cover (REQ-136) |

## Consequences

- One application, one database, one container to run, back up and restore.
- The interface components are written once as templates from the design system. There is no React.
- Organisation scoping and append-only history hold even if application code is wrong, and can be tested directly against the database.
- The rules package can be handed to an independent verifier with the fixtures and nothing else.
- Type checking and linting are enforced by the pipeline, not by the language.
- Django's administration interface is not exposed for customer organisations, because of REQ-004.
- If a rich offline or mobile client is ever needed, it is built against an interface added to this application, by a later decision record.

## Costs

| Item | Cost |
|---|---|
| Python, Django, PostgreSQL, htmx, the test and scanning tools | Free, open source |
| GitHub Actions | Within the free allowance for a private repository at this scale; to be confirmed from the first month's usage |
| Coolify server | Existing |
| Off-server backup storage | Paid, small. Provider and cost are Alex's decision (Issue #27) |

## Open Before First Deployment

1. The current state of the Coolify server (free memory and disk, other services running) has not been inspected. It is checked, without changing anything, before the first deployment.
