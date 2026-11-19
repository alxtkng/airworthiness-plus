# Operations

Step 8 of private beta. How the service is built, run, backed up, watched and repaired, and what the company does with the data it holds.

Nothing here names the server, its address or any credential. Those are held by Alex King and are never committed.

| Document | What It Covers | Requirements |
|---|---|---|
| `deployment.md` | Building and running the service; settings; the reverse proxy; what is checked on the server | REQ-132 |
| `backup-and-restore.md` | What is backed up, how, for how long; the recovery point and recovery time objectives; how to restore | REQ-150 to REQ-154 |
| `restore-tests/` | The record of each restore test | REQ-153 |
| `backup.sh`, `restore.sh`, `check_backup_age.sh` | The scripts the procedure uses | REQ-150, REQ-152, REQ-153 |
