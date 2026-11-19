# Backup and Restore

Step 8 of private beta. Date: 19 November 2026. REQ-150 to REQ-154; hazard H-009; threats TH-040 to TH-042.

## Status

The scripts and the procedure exist and have passed a restore test in the build environment (`restore-tests/2026-11-19.md`). Backups are not yet running on the server, and where they are kept off the server is not decided: that is a paid service and Alex King's decision (Issue 27).

## What Is Backed Up

One thing: the PostgreSQL database. It holds every record, the whole history, the access log and the sessions. The application keeps no file of its own outside it; an uploaded import file is not stored, only its values.

Not in the backup, and kept by Alex King apart from it: the service's settings (the signing key and the database passwords) and the key that decrypts the backups.

## How

| Step | How | Why |
|---|---|---|
| Take the backup | `backup.sh <database> <recipient> <directory>`, run as the backup role, every 24 hours and before every migration | REQ-150. 145.A.45(e) expects backup within 24 hours of an entry |
| Encrypt it | To an `age` recipient, before it is written to disk. The matching identity is not on the server | TH-040. The server cannot read its own backups, and nor can whoever holds the storage |
| Check it | A SHA-256 file beside each backup | A damaged copy is found before it is needed |
| Copy it off the server | To storage in a different place, with credentials that can add and cannot delete or overwrite | REQ-151; CAO.A.090(e); TH-041 |
| Notice when it stops | `check_backup_age.sh <directory> 26`, run from somewhere other than the server, raising an alert when the newest backup is more than 26 hours old or missing | REQ-152; TH-042. A server that is down cannot report its own missing backup |
| Prove it restores | A restore test into a new database, recorded in `restore-tests/`, every 3 months and after any change to the database version or the scripts | REQ-153 |

The backup role can read every record and write nothing: `LOGIN`, `BYPASSRLS`, a member of `pg_read_all_data`, and no other right. It needs to bypass row-level security because a backup made under it would hold only the rows one organisation can see.

### Kept For How Long

Proposed, for Alex King to confirm: every daily backup for 35 days, and the first of each month for 12 months. Backups are for recovering the service; they are not the retention of the records, which the database itself keeps for the periods in REQ-133.

## Recovery Point Objective

**24 hours.** Proposed, for Alex King to confirm.

This is how much could be lost: everything entered since the last backup. The reasoning:

- 24 hours is what 145.A.45(e), adopted for Part-CAO, expects for backup of records, and what REQ-150 requires.
- The organisation's own source documents for the last day still exist: the work pack, the logbook entry, the certificate. A day's entries can be made again from them, and the import's verification report is how they are checked.
- A certificate issued in that day is not lost to the world: it is on paper and a copy goes to the Civil Aviation Authority. Its serial is protected by stating the highest serial after a restore (REQ-154).
- A shorter period is possible by keeping the database's write-ahead log off the server as it is written, which brings the loss down to minutes. It costs more storage and more to operate. Not proposed for private beta.

## Recovery Time Objective

**The next working day.** Proposed, for Alex King to confirm.

This is how quickly the service is back. The reasoning:

- The system records and calculates; it does not release an aircraft. While it is down the organisation works from its last export and its paper records, as it would in a parallel run.
- The restore itself is quick: seconds for the sample, and the measured time is recorded at each restore test as the database grows.
- What takes the time is a person and a server. There is one person. If the server is lost, a new one has to be obtained before anything can be restored. A shorter objective would be a promise that one person cannot keep.

## Restoring

Passwords and keys are entered by Alex King.

1. Decide which backup. The newest, unless the fault is in the records themselves.
2. On the database server, make sure the roles exist: the owner, the service login as a member of `airworthiness_application`, and the backup role. On a new server they are created first; the backup restores each table to its owner and its grants.
3. Create a new, empty database. Never restore over records: `restore.sh` refuses a database that is not empty.
4. `restore.sh <backup file> <identity file> <new database>`. The identity file is brought to the machine for this and removed afterwards.
5. `python -m django check_records`, as the backup role, against the new database. It must end The Records Agree with Their History.
6. For each organisation, ask what the highest certificate serial it has issued is, from its own copies, and state it: `python -m django set_serial_floor <organisation> <serial>`, as the owner.
7. Tell each organisation the time of the backup, so that it knows what to enter again.
8. Point the service at the new database. Keep the old one, if it still exists, until the cause is understood.
9. Record what happened in the incident log (`incident-response.md`), and in the organisation's Problem Log.

## Still to Do on the Server

| Item | Waiting On |
|---|---|
| Where backups are kept off the server, and its cost | Alex King, Issue 27. A recommendation is in `backup-storage-options.md` |
| The backup role and the daily job | First deployment |
| The alert when a backup is late | Choice of where the check runs |
| A delete attempt with the server's storage credentials, shown refused (TH-041) | The storage |
| The restore test on the server | First deployment |
