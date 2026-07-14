# HAP Release v1.0.0

Release date: 2026-07-14

## Scope

Home Analytics Platform v1.0.0 delivers the first stable home-server baseline:

- Docker Compose deployment for the PVE Docker VM.
- FastAPI backend with plugin registry, health check, unified responses, and SQLite storage.
- Vue 3 frontend with dashboard navigation, dark theme, and lottery plugin views.
- DLT analysis module foundation with official rule seed, statistics API surface, and required disclaimer.
- Operational scripts for smoke testing, backup, deployment, and performance checks.

## Pre-Release Checklist

- Confirm repository is clean before tagging.
- Confirm Docker stack has only one active HAP stack.
- Run backend compile check.
- Run frontend build when Node dependencies are available.
- Build Docker images.
- Start stack with `docker compose up -d`.
- Confirm backend health endpoint returns `status: ok` and `version: 1.0.0`.
- Confirm frontend returns HTTP 200 on the published port.
- Create SQLite volume backup before replacing any running deployment.

## Upgrade

```bash
git pull
cp .env.example .env
docker compose build --pull
docker compose up -d
docker compose ps
./scripts/pve-smoke-test.sh http://127.0.0.1:8088
```

If an existing `.env` file is already present, update `APP_VERSION=1.0.0` manually and keep local host-specific values such as `HAP_WEB_PORT` and `CORS_ORIGINS`.

## Rollback

```bash
git checkout <previous_commit_or_tag>
docker compose build
docker compose up -d
docker compose ps
```

Restore the latest `hap_sqlite` backup only when a data migration or data corruption requires it.

## Known Limits

- Historical DLT draw ingestion is not automated yet.
- Fund, PVE Monitor, Docker Monitor, Automation, and Reports are reserved modules.
- Frontend build depends on local Node package installation.
