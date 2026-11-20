# Operations

Step 8 of private beta. How the service is built, run, backed up, watched and repaired, and what the company does with the data it holds.

Nothing here names the server, its address or any credential. Those are held by Alex King and are never committed.

| Document | What It Covers | Requirements |
|---|---|---|
| `deployment.md` | Building and running the service; settings; the reverse proxy; what is checked on the server | REQ-132 |
| `test-site.md` | The test site on a free host, holding the sample organisation only: how it is made, started, used and removed. It is not the server | ADR-0003; Issue 96 |
| `backup-and-restore.md` | What is backed up, how, for how long; the recovery point and recovery time objectives; how to restore | REQ-150 to REQ-154 |
| `restore-tests/` | The record of each restore test | REQ-153 |
| `backup-storage-options.md` | Where to keep backups away from the server: what it must do, what was found, and a recommendation for Alex King | REQ-151; Issue 27 |
| `backup.sh`, `restore.sh`, `check_backup_age.sh` | The scripts the procedure uses | REQ-150, REQ-152, REQ-153 |
| `monitoring.md` | What is watched, what raises an alert, and every log: what is in it, where, for how long | REQ-152 |
| `incident-response.md` | What to do when something goes wrong, who is told, and what is recorded | REQ-132, REQ-172 |
| `vulnerability-management.md` | How vulnerabilities are heard of, rated, fixed and disclosed, and how fast | REQ-132 |
| `keys-and-secrets.md` | Every key and secret: what it is for, where it lives, who can read it, when it is replaced | REQ-132 |
| `user-administration.md` | Adding and removing users; a forgotten password; a lost authenticator | REQ-005 to REQ-010 |
| `system-description.md` | The description of the system for an organisation's exposition | REQ-175 |
| `data-protection/record-of-processing.md` | What personal data is processed, why, how it is protected and for how long. A draft, not legal advice | REQ-132 |
| `contracts/` | Drafts for a solicitor: data processing agreement, service level, data export on exit | |

## What Only Alex King Can Do

| Item | Document |
|---|---|
| Rent a server, when there is a budget. There is no existing server (found 20 November 2026) and none is planned for now; the test site is the only hosting | `deployment.md`, `test-site.md` |
| Choose and pay for backup storage and any monitoring service (Issue 27) | `backup-and-restore.md`, `monitoring.md` |
| Confirm the recovery objectives and how long backups and logs are kept | `backup-and-restore.md` |
| Hold the backup decryption key and the owner's database password | `keys-and-secrets.md` |
| Say who acts when he is away | `incident-response.md`, `monitoring.md` |
| Have the data protection documents and the contract drafts reviewed by someone qualified | `data-protection/`, `contracts/` |
| Fill in the company's details: registered address, company number, registration with the Information Commissioner's Office | `data-protection/`, `contracts/` |
