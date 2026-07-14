# Phase 11: Performance And Operations

## Goals

Phase 11 hardens the first Docker deployment for a home server environment. The priority is stable
operation before aggressive scaling.

## Current Decisions

- Keep `BACKEND_WORKERS=1` while SQLite is the primary database.
- Use Nginx gzip for text assets and API responses.
- Cache immutable frontend assets under `/assets/` for 30 days.
- Keep `index.html` uncached so Portainer stack updates are visible after refresh.
- Store SQLite, exports, backups, and logs in named Docker volumes.

## Why One Backend Worker

SQLite is reliable for this phase, but concurrent writes can create lock contention. A single backend
worker also prevents future in-process schedulers from running the same job multiple times.

When HAP moves to PostgreSQL and a distributed scheduler lock is added, `BACKEND_WORKERS` can be
raised gradually.

## Validation

Run a smoke test from the Docker host:

```bash
sh scripts/pve-smoke-test.sh http://127.0.0.1:8088
```

Run a lightweight latency/resource check:

```bash
REQUESTS=20 sh scripts/pve-performance-check.sh http://127.0.0.1:8088
```

## Backup

Create a SQLite volume backup:

```bash
sh scripts/backup-sqlite.sh
```

Backups are written to the `hap_backups` Docker volume.

## Phase 11 Acceptance Criteria

- Frontend root returns HTTP 200.
- Backend health endpoint returns `status=ok`.
- Lottery rule endpoint returns the current DLT rule version.
- Containers stay healthy after restart.
- SQLite volume backup can be created and listed.
- Basic latency samples complete without HTTP errors.
