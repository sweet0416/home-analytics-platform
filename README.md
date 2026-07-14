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

## PVE Docker Quick Start

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

Default web URL:

```text
http://192.168.100.249:8088
```

Smoke test:

```bash
curl http://127.0.0.1:8088/api/v1/system/health
curl http://127.0.0.1:8088/api/v1/lottery/dlt/rules/current
```

## Release

- Changelog: [CHANGELOG.md](CHANGELOG.md)
- v1.0.0 checklist: [docs/release-v1.0.0.md](docs/release-v1.0.0.md)
