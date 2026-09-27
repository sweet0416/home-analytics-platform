# SQLite restore safety candidate

This is a candidate implementation, not a production restore/deployment acceptance record.
The production Compose pins and configuration remain unchanged.

## Supported boundary

One HAP backend worker owns the database. The process-local maintenance gate covers HTTP requests
(including machine-token routes, streaming responses, dependency cleanup and FastAPI background
tasks) and all four schedulers: backup, infrastructure notification, fund NAV and lottery sync.
Infrastructure notifications also write delivery history and therefore participate in the gate.
Already admitted work can finish; new database requests receive HTTP 503 and new jobs skip with
`reason=restore_maintenance` in logs. A competing restore receives HTTP 409. If active work does not
drain within 10 seconds, restore aborts before replacement; it never force-closes an active session.

All database-backed reads are also blocked. Health, build info, in-memory login/logout/session checks,
and authenticated `GET /api/v1/system/restore-status` remain available. The status includes the
operation ID, phase, maintenance flag and number of active operations. Authentication and CSRF
requirements remain in force. The public health endpoint is liveness, not proof of restore success.

The guard does not coordinate other processes, SQLite shells, volume editors or multiple workers.
Those writers are unsupported and must be excluded by the operator. No distributed lock is added.

## Execution and failure contract

1. Validate confirmation, backup location and live engine/session binding; claim the sole restore slot.
2. Enter maintenance and drain admitted work; reject an earlier interrupted-restore marker.
3. Validate the source and current database: regular nonempty file, SQLite `quick_check`, recognizable
   HAP core tables and a known Alembic revision when present. Reject unrelated or unsupported inputs.
4. Verify there are no checked-out engine connections, then dispose the pool. Create an Online Backup
   API safety copy and validate it. Safety backup failure prevents replacement. Restore does not run
   retention pruning, so neither the source nor safety copy is removed during the operation.
5. Copy the source to a unique file beside the target, flush it and validate it. Persist the operation
   marker, then use `os.replace` on the same filesystem. The original file remains until this step.
6. Run the existing Alembic upgrade mechanism against an explicit connection to the restored database.
   Legacy unversioned HAP databases use the existing bootstrap/stamp path. `create_all` alone is not
   considered success. Validate `quick_check`, exact Alembic head, all mapped tables/columns, and reads
   through a new application session.
7. Record success, remove the operation marker, and resume access. Existing engine/sessionmaker objects
   remain bound to the same path; disposed pools establish fresh connections to the replacement file.

Post-replacement migration, validation, or required history failure triggers a controlled rollback:
dispose connections, validate and replace from the safety backup, migrate and validate again. A
successful rollback still reports `RESTORE_FAILED / ROLLBACK_SUCCEEDED`; normal access then resumes.
If rollback cannot be validated, the response reports `ROLLBACK_FAILED`, maintenance remains active,
and the marker prevents normal startup/migration after a process restart.

The Settings action has a longer request timeout and distinguishes rollback success, maintenance and
an unknown response outcome. A timeout/disconnect is not proof that restore failed. No restore POST
is automatically retried; inspect status and audit evidence before deciding on another operation.

## WAL, SHM and interrupted operations

This candidate deliberately rejects WAL mode, or any `-wal`, `-shm` or `-journal` sidecar at the source
or live target, before replacing data. It does not delete sidecars or perform implicit checkpoint-based
cleanup. This is not WAL support; a future WAL rollout must first extend this protocol and its tests.
Do not delete a sidecar merely to pass this gate.

An atomic per-operation `hap_restore_<operation_id>.json` journal in the backup directory preserves
start time, source/safety filenames, phases, migration/rollback outcomes and fixed error classes even
when the database itself is replaced. Terminal results are also recorded in the existing
`database_restore_runs` table when the resulting database is usable; no schema migration is added.
Pre-replacement rejections are recorded in the external journal without writing to the live database.
The journal does not contain database rows, credentials or raw exception payloads. It is not subject
to `.db` backup retention and should be retained with recovery evidence.

If `<database>.restore-in-progress` remains, preserve the database, safety copy, journal and sidecars.
Do not blindly restart, retry, or delete the marker. With explicit operator approval, recover offline
after stopping every writer, determine the last durable stage from the journal, select/validate a
known-good copy, run migrations and verify reads. Remove the marker only after recovery is verified.
This document does not authorize or execute those production operations. Process interruption fails
closed; the multi-file protocol is not a power-loss-proof database transaction.

## Candidate validation

Python 3.12+, `backend/requirements-dev.txt`, and the repository's existing pytest/Ruff tooling are
required. Run from a disposable checkout with no real `.env` or real provider credentials. On Windows:

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
py -m pytest -c backend/pyproject.toml backend/tests/test_restore_safety.py backend/tests/test_database_migrations.py backend/tests/test_backup_service.py backend/tests/test_backup_remote.py
py -m pytest -c backend/pyproject.toml backend/tests
py -m ruff check backend/app backend/scripts backend/tests
py -m compileall -q backend/app backend/scripts backend/tests
git diff --check
```

Restore tests create temporary databases and use init-only Settings. They exercise real migrations,
concurrent requests and background cleanup, all scheduler guards, invalid sources, safety-copy failures,
rollback failures, fresh sessions, and sidecar rejection. They never use production database files.
