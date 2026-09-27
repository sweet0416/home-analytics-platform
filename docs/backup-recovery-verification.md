# HAP backup recovery verification

A backup's presence is not proof that it can be restored. The command below verifies a
**static, selected HAP `.db` backup** by copying it to a temporary directory. It opens the copy
read-only for SQLite checks, upgrades **only that copy** to the repository's Alembic head, reads
all mapped application tables, checks the database health probe, and verifies the final database.
The input's SHA-256 is checked before, during, and after the exercise. A source that changes while
being copied is rejected. The temporary copy is removed when the command exits.

Run from a trusted checkout with Python 3.12+ and `backend/requirements-dev.txt` installed.
On Windows PowerShell, substitute the path of an already-created, static backup:

```powershell
$previousPythonPath = $env:PYTHONPATH
$env:PYTHONPATH = (Resolve-Path backend).Path
Push-Location backend
try { py -m scripts.verify_backup 'C:\path\to\hap_selected_backup.db' }
finally { Pop-Location; $env:PYTHONPATH = $previousPythonPath }
```

The command prints only file size, hashes, schema revisions, integrity statuses and table counts;
it never prints records or secrets. Exit 0 means that this **one sample** passed the isolated
checks; exit 1 means recovery remains unverified; exit 2 means command usage is invalid. No
production database, backup, scheduler, Portainer Stack or volume is modified. Do not point it at
the live `hap.db`, a hot SQLite file, an encrypted remote asset, or an untrusted file. No `.env`
or caller application settings are used by the migration exercise.

## Evidence levels

- `UNVERIFIED_BACKUP`: file exists, but recovery has not been exercised.
- `STRUCTURALLY_VALID`: SQLite header, `quick_check`, `integrity_check`, foreign keys and HAP
  schema identity pass. Foreign-key violations are reported as failures; nothing is repaired.
- `MIGRATION_COMPATIBLE`: a disposable copy upgrades to the current Alembic head.
- `APPLICATION_READABLE`: a fresh engine can read mapped tables and the DB health probe returns
  `ok` on the copy.
- `RECOVERY_VERIFIED`: all above checks, source/copy hash equality and final check pass for this
  particular sample. It does not prove every backup, off-host availability, encrypted remote
  decryption, a full production restore, or future schema compatibility.

## If the live database fails

1. Stop and contain all writers before any filesystem-level recovery. Do not copy a hot SQLite
   file, delete WAL/journal sidecars or blindly retry a timed-out restore.
2. Preserve the broken database, sidecars, restore marker and audit journal for diagnosis.
3. Identify a candidate backup and verify an isolated copy with the command above. If none pass,
   stop; do not overwrite the only live database with an unverified file.
4. With explicit operator approval, use the supported authenticated restore path within its
   single-worker boundary. It takes its own safety backup, enters maintenance, validates the
   source, replaces atomically, migrates, validates and rolls back after a post-replacement failure.
5. Confirm mapped data reads, database health, restore status, expected counts and recent records
   before resuming normal operations. A failed rollback or interrupted marker requires supervised
   offline recovery; see [restore safety](restore-safety.md).

Manual backups are local. The scheduled job first creates a local Online Backup API copy and may
then upload an encrypted remote asset if configured. The optional remote asset requires separate
decryption and recovery verification; upload success alone is not recovery proof. Current local
retention keeps the newest `BACKUP_RETENTION_COUNT` matching `hap_*.db` files by modification
time after creating a backup. It does **not** distinguish verified from unverified files, so this
policy does not guarantee that a recoverable backup remains. Verification adds no scheduler and
does not change retention.
