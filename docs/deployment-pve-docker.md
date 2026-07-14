# Phase 10: PVE Docker Deployment

## Target

HAP is deployed on the Docker environment running on the PVE host.

Default access URL after deployment:

```text
http://192.168.100.249:8088
```

The Docker management UI on port `9000` is not used by application code and credentials must not be
stored in this repository.

## Services

```text
hap-frontend
  - Nginx
  - Serves Vue static files
  - Reverse proxies /api to hap-backend

hap-backend
  - FastAPI
  - SQLite
  - Loguru logs
  - Plugin runtime
```

## Persistent Volumes

```text
hap_sqlite   -> /app/data/sqlite
hap_exports  -> /app/data/exports
hap_backups  -> /app/data/backups
hap_logs     -> /app/logs
```

## Deploy

Copy the project folder to the PVE Docker host, then run:

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

## Verify

```bash
curl http://127.0.0.1:8088/api/v1/system/health
curl http://127.0.0.1:8088/api/v1/lottery/dlt/rules/current
```

Browser:

```text
http://192.168.100.249:8088
```

## Logs

```bash
docker compose logs -f hap-backend
docker compose logs -f hap-frontend
```

## Stop

```bash
docker compose down
```

Do not use `docker compose down -v` unless you intentionally want to delete SQLite data, exports,
backups, and logs.

## Backup

For a quick volume backup:

```bash
docker run --rm \
  -v hap_sqlite:/data/sqlite \
  -v hap_backups:/backup \
  alpine sh -c "tar czf /backup/hap_sqlite_$(date +%Y%m%d_%H%M%S).tar.gz -C /data sqlite"
```

## Upgrade

```bash
docker compose build --pull
docker compose up -d
docker compose ps
```

Before upgrading, create a backup of `hap_sqlite`.

