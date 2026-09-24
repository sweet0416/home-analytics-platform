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

The production file is standalone and does not use Compose overlay merge behavior or `!reset`. Its backend,
frontend, and optional agent images are pinned to the verified source revision
`283bd97c84aee1a0f1cc9e5671ec4d351e3f2e37`. The later deployment-configuration commit is not the image
source revision. GitOps and automatic updates remain off; pushing a configuration commit does not redeploy HAP.

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

Generate an administrator password hash with `python scripts/hash_admin_password.py`
and configure `HAP_ADMIN_PASSWORD_HASH` in the private Portainer Stack variables.
The new backend will refuse to start without it. Keep the plaintext password
and the hash out of Git. Set `HAP_COOKIE_SECURE=true` when the browser reaches
HAP over HTTPS. This login prerequisite must be in place before switching to
an image built from the authentication change.

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
variables. For an image rollback, pin a new root Compose configuration to the verified pre-auth source revision
`4c5a17b3d6987fc6de66108fc5969be14e34b175` and these immutable GHCR digests:

- Backend: `ghcr.io/sweet0416/home-analytics-platform-backend@sha256:3ad050a8433b1c44e4442b6732d31221b00e0840982aa2a5491f0ae59fc5957f`
- Frontend: `ghcr.io/sweet0416/home-analytics-platform-frontend@sha256:bc86d14ea975d246ddf53eadfdaf402b7c97f261877eb1fcff5d84de2a70c7b9`

Set `HAP_DEPLOYMENT_REVISION` to that same pre-auth SHA, commit and push the rollback configuration, then perform
one controlled manual redeploy of the existing Stack. Verify health, login behavior, build info, and existing data.
This is a prepared rollback candidate, not proof that its older application will accept every future database
schema. Check database-migration compatibility and a usable backup before the initial cutover or rollback.

The current pre-cutover runtime uses local Docker image IDs, not registry digests: backend
`sha256:d0f83acf6bebae8efe9f6f8f2ee7d3f636336478fc6095f133a4226a98df6c55` and frontend
`sha256:22cead0f6d36baffe439e4107bc88fc0a5494556d1180c585701915af48c61ec`. Do not prune them before
cutover acceptance; they cannot be assumed pullable again. The original local-build Compose is preserved in the
pre-cutover Git commit, but merely restoring that file and rebuilding newer source does **not** recreate these
exact images. Image rollback is not database rollback; never delete or recreate the data volumes.

Do not use `docker compose down` as a production cutover or rollback step. Never use `down -v` on HAP data.

## Backup

For a quick volume backup:

```bash
docker run --rm \
  -v hap_sqlite:/data/sqlite \
  -v hap_backups:/backup \
  alpine sh -c "tar czf /backup/hap_sqlite_$(date +%Y%m%d_%H%M%S).tar.gz -C /data sqlite"
```

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
