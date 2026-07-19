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
