# Home Analytics Platform

HAP is a modular HomeLab analytics platform designed for long-term maintenance and Docker
deployment on a PVE host.

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

