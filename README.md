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

## Architecture Overview

HAP has two intentionally different Compose models:

### Development Model

Use `docker-compose.yml` for local development, testing, and local image builds.

- Services use `build:` and build from the checked-out source tree.
- Build-time provenance can use local fallback values.
- This model is convenient for iteration, but is not the production release source.

### Production Model

Use the standalone `docker-compose.production.yml` for production deployment.

- Services use GHCR prebuilt images pinned by `image@sha256:<digest>`.
- Production does not build HAP images on the PVE host.
- Production must not use `latest`, an unverified tag, or a mutable convenience tag as its authority.
- The production file is independent and does not depend on Compose overlay reset tags such as `!reset`.

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
docker compose build
docker compose up -d
docker compose ps
```

Do not use this development flow for the production image migration. Production deployment follows
[the PVE production deployment guide](docs/deployment-pve-docker.md).

Default web URL:

```text
http://192.168.100.249:8088
```

Smoke test:

```bash
curl http://127.0.0.1:8088/api/v1/system/health
curl http://127.0.0.1:8088/api/v1/lottery/dlt/rules/current
```

## Production Deployment Rules

Production deployment must:

- keep the Portainer Stack and Compose project identity as `hap`;
- use the standalone `docker-compose.production.yml`;
- pin Backend, Frontend, and enabled `ttskill-agent` images by verified digest;
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
