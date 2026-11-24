# ADR-0002: Organisation Scoping and History in the Database

Status: **Adopted 18 November 2026.** It carries out rules already fixed in `prompts/private-beta.md` (Step 4), ADR-0001 and `architecture/threat-model.md`; the mechanisms below are ours.

Date: 18 November 2026

## Context

Two rules must hold even if application code is wrong (ADR-0001, "How the Fixed Design Rules Are Met"):

- Each organisation has access to its own data only, and only its own personnel enter data (AMC1 CAO.A.100(f) point (d)(2); REQ-002, REQ-003, REQ-004; threat TH-020).
- Every record has a history that cannot be changed or removed, and nothing is deleted (CAP 562 C-90; REQ-130, REQ-131; threats TH-021, TH-022, TH-025).

## Decision

### Two Database Roles

| Role | Used For | What It Can Do |
|---|---|---|
| Owner of the tables | Migrations, and setting up a new organisation with its first user. Run separately, with `AIRWORTHINESS_DATABASE_OWNER_WORK=true` | Changes the structure of the database. Is still subject to row-level security and to the triggers that refuse deletion |
| `airworthiness_application` | Everything the running application does. Every connection switches to it | Reads, adds and changes rows of record tables. Cannot delete or truncate anything, cannot create an organisation, cannot write history directly, owns nothing, and can create no table, temporary table, function or trigger |

The account the running application signs in to the database with must be a member of `airworthiness_application` and nothing else. Its credentials are different from the owner's and the application never holds the owner's (threat TH-024).

### Organisation Scoping

- Every table carries its organisation. A record never moves to another organisation and never changes its identifier.
- Row-level security is enabled and forced on every table, so it applies to the owner as well.
- The policy compares the row's organisation with a setting on the database session, `airworthiness.organisation`. The application sets it for one transaction at a time (`airworthiness_plus.history.session.working_for`). With none set, no rows are returned and no row can be written.
- Identifiers are random, so one record's address says nothing about another's (threat TH-006).
- A record refers only to records of its own organisation. Every column that refers to another record has a trigger that refuses a row whose parent belongs elsewhere, for the application and the owner alike. Added 18 November 2026.

### History

- A trigger on every record table writes an entry to `history_event` whenever a row is created or changed. The application does not write history and cannot: a direct insert is refused.
- An entry holds the organisation, the record, a sequence number, the action, the columns that changed, the record before and after, the user, the user's name at the time, and the time from the database clock.
- The user comes from a second session setting, `airworthiness.user`, and must be an active user of the same organisation. A change with no user set is refused. Work done as the owner of the tables is recorded against the database role, not passed off as a user's.
- Values named as omitted for a table, such as a password, are kept out of the entry; that they changed is recorded.
- Update, delete and truncate on `history_event`, and delete and truncate on every record table, are refused by trigger whoever asks, and the application's role is not granted them.
- Each entry carries a SHA-256 hash over all its fields and the hash of the entry before it for the same record. The exact form is written in `airworthiness_plus/history/chain.py`. The database computes it; `chain.problems` computes it again separately in Python and reports an altered entry, a broken link or a missing entry.

### Sign-In and the Access Log

Added 18 November 2026.

- While a user name is being checked no organisation is known. For that moment a third session setting, `airworthiness.signing_in`, lets the application read the one user with that name and the access log entries for that name. It can change neither user nor organisation by it.
- The access log, `accounts_accessentry`, is not a record with a history: it is itself a log. It has row-level security, takes its time from the database clock, and refuses update, delete and truncate whoever asks.
- The log decides whether a user name is locked and whether a code has been used, so there is no counter to reset and signing in does not change the user record.
- The session table is Django's. Sessions are made, renewed and removed, so the application's role may delete from that one table. A session holds the user and the organisation it was made for; the user is then read under row-level security, so a session cannot resolve to a user of another organisation.

### Migrations That Change Existing Records

Added 24 November 2026.

- The owner of the tables is under row-level security too, so a migration cannot read or change every organisation's rows in one statement.
- A migration that must give existing records something new uses `history.sql.for_each_organisation`. It lifts the forcing of row-level security from the organisation table alone, reads the list of organisations, and puts the forcing back, all inside the migration's transaction and under the lock that changing a table takes.
- Each organisation's rows are then read and written with that organisation set, exactly as the application sets it. The history trigger records each change against the database role, as it does when an organisation is set up.
- `tests/test_approvals.py` runs such a statement and checks that the forcing is back and no organisation is left set.

### Keeping It That Way

`tests/test_data_layer.py` reads the database catalogue and fails the build if any table lacks row-level security, the history trigger or the refusal of deletion, or if the application's role holds a privilege it should not. A new record table is put under the rules by one call, `protect_record_table`, in its migration.

## Consequences

- The tests run as the application's role against a real PostgreSQL, and try each rule with raw SQL.
- A fault in a view or a query cannot show another organisation's rows or remove a record.
- Changing a record always costs one more row. Reading a record's history is one indexed query.
- Django's bulk operations work unchanged; `delete()` is refused on models and querysets as well as by the database.
- Transactional test cases that empty tables between tests cannot be used, because truncation is refused. Tests run inside a transaction that is rolled back.

## Limits, Stated Plainly

- The database trusts the application to set the organisation and the user. The rules protect against a missing filter or a faulty query, not against someone who controls the application process. That is what sign-in, the second factor and the penetration test are for (threats TH-001, TH-002; REQ-008).
- Someone with the owner's or a superuser's access can switch triggers off. The hash chain then shows an altered or missing entry, but entries removed from the end of a record's history can only be found by comparison with the off-server backup (threat TH-025; REQ-151).
- The hash of an entry depends on the stored text of the record before and after, as PostgreSQL wrote it. An export must carry that text unchanged for the chain to be checked outside the database (threat TH-081; REQ-134).
