# Home Analytics Platform

HAP is a modular HomeLab analytics platform designed for long-term maintenance and Docker
deployment on a PVE host.

Current release: `1.0.0`

## Modules

- Dashboard
- Lottery
- Reports
- Settings

Reserved plugin areas:

- Fund
- Stocks
- Docker Monitor
- PVE Monitor
- AI Lab
- Automation

## Administrator login

HAP requires one administrator password. Generate its PBKDF2 hash locally with
`python scripts/hash_admin_password.py`, then put the printed hash in
`HAP_ADMIN_PASSWORD_HASH` in your private `.env` or Portainer Stack variables.
In a Compose `.env` file, wrap the hash in single quotes so its `$` separators
are not expanded. Set `HAP_COOKIE_SECURE=true` when the browser uses HTTPS.
Never commit the hash or plaintext password. The backend refuses to start when
the hash is absent or invalid. Use HTTPS when accessing HAP outside a trusted
local network.

All API routes require the admin session except the health check, login, and
six Tiantian Skills integration routes that retain their dedicated sync token.
Sessions expire after eight hours, logout revokes the session, and service
restarts log everyone out. HAP currently runs with one backend worker so these
short-lived sessions can be held in memory.

## Architecture Overview

HAP has two intentionally different Compose models:

### Development Model

Use `docker-compose.development.yml` for local development, testing, and local image builds.

- Services use `build:` and build from the checked-out source tree.
- Build-time provenance can use local fallback values.
- This model is convenient for iteration, but is not the production release source.

### Production Model

The existing Portainer `hap` Git Stack uses the root `docker-compose.yml` for production.

- Services use GHCR prebuilt images pinned directly by `image@sha256:<digest>`.
- Production does not build HAP images on the PVE host.
- Production must not use `latest`, an unverified tag, or a mutable convenience tag as its authority.
- GitOps/automatic updates remain off; deployment is a controlled manual Portainer operation.
- Emergency rollback: the currently pinned images report pre-auth source revision `4c5a17b3d6987fc6de66108fc5969be14e34b175`; the Phase 1 cutover failed backend health acceptance and is not complete.

The production image source of truth is:

```text
GitHub Commit
  -> GitHub Actions
  -> GHCR Image
  -> Immutable Digest
  -> Portainer Stack
  -> Runtime Provenance Verification
```

## PVE Docker Development Quick Start

```bash
cp .env.example .env
docker compose -f docker-compose.development.yml build
docker compose -f docker-compose.development.yml up -d
docker compose -f docker-compose.development.yml ps
```

Use an isolated development Docker engine: the development file retains the historical HAP container and volume
names and must not run alongside the production Stack on the same host. Production deployment follows
[the PVE production deployment guide](docs/deployment-pve-docker.md).

Default web URL:

```text
http://192.168.100.249:8088
```

Smoke test:

```bash
curl http://127.0.0.1:8088/api/v1/system/health
```

The health endpoint is public; protected API calls should return 401 until login.

## Production Deployment Rules

Production deployment must:

- keep the Portainer Stack and Compose project identity as `hap`;
- use the root `docker-compose.yml` in the existing `hap` Stack;
- pin Backend, Frontend, and enabled `ttskill-agent` images by verified digest;
- keep GitOps off and deploy manually only after a database backup and final review;
- verify runtime provenance after recreation.

Production deployment must not:

- run `docker compose down -v`;
- delete or rename `hap_*` volumes;
- deploy `latest` or an unverified image tag;
- assume a healthy container proves that the expected Git revision is running.

Fixed volumes are data, not image artifacts:

```text
hap_sqlite
hap_exports
hap_backups
hap_logs
ttskill_data
```

They must survive image updates and rollbacks.

## DLT Data Sync

DLT synchronization always tries the China Sports Lottery source first. When that source is
unavailable or returns an invalid response, HAP can automatically use the 500 Lottery public
history page as a third-party fallback. Every sync run records the source that actually supplied
the data.

The fallback and both source URLs are configurable through `.env`:

```text
LOTTERY_DLT_FALLBACK_ENABLED=true
LOTTERY_DLT_SPORTTERY_URL="https://webapi.sporttery.cn/gateway/lottery/getHistoryPageListV1.qry"
LOTTERY_DLT_500_HISTORY_URL="https://datachart.500.com/dlt/history/newinc/history.php"
```

## Release

- Changelog: [CHANGELOG.md](CHANGELOG.md)
- Notifications: [docs/notifications.md](docs/notifications.md)
- v1.0.0 checklist: [docs/release-v1.0.0.md](docs/release-v1.0.0.md)
