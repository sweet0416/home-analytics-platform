# PVE Docker Deployment

## Target

HAP is deployed on the Docker environment running on the PVE host.

Default access URL after deployment:

```text
http://192.168.100.249:8088
```

The Docker management UI on port `9000` is not used by application code and credentials must not be
stored in this repository.

## Architecture: Development vs Production

HAP has separate deployment models.

### Development

`docker-compose.yml` is the development and testing model. It uses `build:` and builds HAP images from the local
checkout. Use it when iterating on source code or validating local changes.

### Production

`docker-compose.production.yml` is the production model. It uses prebuilt GHCR images pinned by immutable digest:

```text
GitHub Commit
  -> GitHub Actions
  -> GHCR Image
  -> Digest Pin
  -> Portainer Stack
  -> Runtime Provenance Verification
```

The production Compose file is standalone. It does not depend on Compose overlay merge behavior or the `!reset` tag,
because Portainer deployments may use a different Compose parser than local Docker Compose.

The PVE host must not build the production HAP images.

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

## Production Deployment Rules

Before a real production deployment:

1. Confirm the GitHub Actions build succeeded.
2. Record the target full Git SHA and each GHCR digest.
3. Confirm the database backup gate is PASS.
4. Keep the Portainer Stack name and Compose project identity as `hap`.
5. Use the standalone production Compose file with digest-pinned images.
6. Pull/recreate only the application containers through the approved Portainer procedure.
7. Run the health, data-preservation, and provenance checks below.

Never use a mutable `latest` tag, an unverified tag, or a different Stack/project name for production.

Never run:

```bash
docker compose down -v
```

Do not delete, rename, migrate, or replace the existing HAP volumes during an image deployment.

## Development Deploy

For local development only:

Copy the project folder to the PVE Docker host, then run:

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose ps
```

For production, do not run `docker compose build`. Use `docker-compose.production.yml` directly and provide verified
GHCR digest references for all enabled HAP images.

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

## Runtime Verification

After production recreation, verify:

Backend:

```text
/api/v1/system/build-info
```

Frontend:

```text
/build-info.json
```

Confirm that Backend and Frontend report the same Git SHA, and that the reported image reference and OCI revision
match the deployment manifest and selected image digest. A healthy container alone is not sufficient evidence.

Also confirm the login page, core pages, holdings, transactions, NAV data, and scheduled services remain usable.

## Rollback

Rollback is an image operation:

1. Select the previous known-good GHCR digest.
2. Update the production image references.
3. Pull/recreate the application containers.
4. Repeat health and provenance verification.

Rollback must not use `main` as the authority and must not delete the database volume. Code-image rollback is not a
database rollback.

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

For the production model, replace the local build/upgrade commands with the manual Portainer procedure described
above. Record the image digest, Git SHA, Compose revision, and backup gate result before recreating containers.

## Troubleshooting

### Why does development Compose have `build:` but production does not?

Development builds from the checkout for fast iteration. Production consumes prebuilt immutable GHCR images so the
running image can be traced to a Git commit and digest.

### Why is `!reset` not used in production?

The standalone production file avoids Portainer Compose parser differences. It declares production images directly
instead of inheriting local `build:` settings and then resetting them.

### Why not use `latest`?

`latest` is mutable and cannot prove which source revision is running. Production uses a verified digest and records
the matching Git SHA.

### Why must the Stack name remain `hap`?

Named volume and network identity must remain attached to the existing HAP resources. Changing the project identity
can create a parallel deployment with empty data resources.
