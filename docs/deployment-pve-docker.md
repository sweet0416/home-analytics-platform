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

`docker-compose.development.yml` is the local development and testing model. It uses `build:` and builds HAP
images from the checkout. It retains the old container and explicit volume names, so run it only on an isolated
development Docker engine, never beside the production Stack on the same host.

### Production

The root `docker-compose.yml` is the production model used by the existing Portainer Git Stack named `hap`.
It uses prebuilt GHCR images pinned by immutable digest:

```text
GitHub Commit
  -> GitHub Actions
  -> GHCR Image
  -> Digest Pin
  -> Portainer Stack
  -> Runtime Provenance Verification
```

The production file is standalone and does not use Compose overlay merge behavior or `!reset`. Phase 1
authentication was accepted in production on 2026-09-25 with deployment-configuration commit
`ef800d5f4a7a0656112923ec63d6153a9c6c4e21` (not an image source revision). The frontend-only login release
keeps the backend at source `283bd97c84aee1a0f1cc9e5671ec4d351e3f2e37` and digest
`sha256:5fe9a557e8c967877a859c1f84352514fd6143036a3df6b6e5b514081cf7cf5b`.
The new frontend target is source `fa9adeea2b9bea3d39316c5a1ac2a574b686506f`, digest
`sha256:a8e08cc64e168dc847c875e3b6583cf2e046e0787faafa68f1718a21f3516884`.
Each service must be verified against its own source SHA after manual deployment; do not change the backend
deployment revision to the frontend SHA. These pins describe the release target, not completed runtime acceptance.
For a frontend-only rollback, retain the backend and restore the previous authenticated frontend digest
`sha256:77e36e9c5ab1c19a736fad2ee8fa0d8cdeef81db3e74d53ef4c030825420bb0b`.
The optional agent remains disabled. GitOps and automatic updates remain off; pushing a configuration commit does not redeploy HAP.

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

The current accepted production release already has a working private
`HAP_ADMIN_PASSWORD_HASH`. Do not rotate or alter it merely for this candidate.
For a future approved release, generate a hash locally with
`python scripts/hash_admin_password.py`; keep the plaintext password and hash
out of Git. The candidate `HAP_ADMIN_PASSWORD_HASH_B64` transport is not
deployed and requires a newly built, verified backend image. Base64 is not
encryption and its value is equally sensitive. Never set both hash inputs.
Set `HAP_COOKIE_SECURE=true` for HTTPS access.

1. Confirm the GitHub Actions build succeeded.
2. Record the target full Git SHA and each GHCR digest.
3. Confirm the database backup gate is PASS.
4. Keep the Portainer Stack name and Compose project identity as `hap`.
5. Confirm the root production Compose file retains the existing volumes, network, port, and services.
6. In the existing `hap` Stack, perform one approved manual Pull and redeploy; do not create a second Stack.
7. Run the health, login, protected-route, data-preservation, and provenance checks below.

Release order: source commit -> successful CI/GHCR build -> verified digest -> deployment-config commit ->
manual Portainer redeploy -> runtime and data acceptance. Before the manual step, record the previous running
image IDs and confirm a usable database backup. This repository preparation does not perform that step.

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
docker compose -f docker-compose.development.yml build
docker compose -f docker-compose.development.yml up -d
docker compose -f docker-compose.development.yml ps
```

For production, do not run `docker compose build`; the existing Portainer Stack reads the root
`docker-compose.yml`, which already pins all HAP images by digest.

## Verify

```bash
curl http://127.0.0.1:8088/api/v1/system/health
```

The health endpoint is public; protected API calls should return 401 before login. Verify login and protected
pages through the browser without exposing credentials in command history.

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

Rollback stays within the same `hap` Stack and preserves the same named volumes, network, port, and environment
variables. The preferred baseline for a future release rollback is the accepted Phase 1 source and digests above,
subject to database/schema compatibility and a verified backup. The pre-auth source revision
`4c5a17b3d6987fc6de66108fc5969be14e34b175` and these older immutable GHCR digests are historical
emergency references only; returning to them removes unified API authentication and is a security downgrade:

- Backend: `ghcr.io/sweet0416/home-analytics-platform-backend@sha256:3ad050a8433b1c44e4442b6732d31221b00e0840982aa2a5491f0ae59fc5957f`
- Frontend: `ghcr.io/sweet0416/home-analytics-platform-frontend@sha256:bc86d14ea975d246ddf53eadfdaf402b7c97f261877eb1fcff5d84de2a70c7b9`

Any exceptional pre-auth rollback requires an explicit security decision, restricted network exposure, a
database-compatibility check, a usable backup, and a controlled manual redeploy with fresh acceptance checks.
It is not an automatic/default rollback target.

The former pre-cutover runtime used local Docker image IDs, not registry digests: backend
`sha256:d0f83acf6bebae8efe9f6f8f2ee7d3f636336478fc6095f133a4226a98df6c55` and frontend
`sha256:22cead0f6d36baffe439e4107bc88fc0a5494556d1180c585701915af48c61ec`. They cannot be assumed
pullable again. The original local-build Compose is preserved in the
pre-cutover Git commit, but merely restoring that file and rebuilding newer source does **not** recreate these
exact images. Image rollback is not database rollback; never delete or recreate the data volumes.

Do not use `docker compose down` as a production cutover or rollback step. Never use `down -v` on HAP data.

## Backup

For an online backup while HAP is running, use its authenticated database-backup operation. It uses
SQLite's Online Backup API (`sqlite3.Connection.backup`) to produce a consistent database copy;
verify the resulting backup and keep it separate from the live volume. Directly archiving the
active `hap_sqlite` directory with `tar` is **not** a guaranteed consistent backup: SQLite may
be writing the main file or WAL at the same time. The `scripts/backup-sqlite.sh` volume archive
is only a cold-backup option after all database writers are stopped and the database is closed.
Never restore or replace production data as part of a configuration-only change.

## Upgrade

For local development only, use `docker compose -f docker-compose.development.yml build --pull` and the same
`-f` file for `up`/`ps`. For production, first back up `hap_sqlite`, verify new source SHA and image digests, then
follow the manual Portainer procedure above. Record image digests, source SHA, deployment-config commit, and backup
gate result before recreating containers.

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
