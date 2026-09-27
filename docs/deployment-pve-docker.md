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
authentication was accepted in production on 2026-09-25 with historical deployment-configuration commit
`ef800d5f4a7a0656112923ec63d6153a9c6c4e21` (not an image source revision). The current production Compose
pins the backend at source `283bd97c84aee1a0f1cc9e5671ec4d351e3f2e37` and digest
`sha256:5fe9a557e8c967877a859c1f84352514fd6143036a3df6b6e5b514081cf7cf5b`, and the frontend at source
`ad4397d56ae580d579c311254a6c821228be3079` and digest
`sha256:2bc71e461135d37167f9561b448dc19e80d110b0233c5a2c843a1ba396bc2559`.
Backend and frontend are pinned independently; different source SHAs are valid. The current frontend includes
Product UI System V1.2, login focus polish, and host-wide Docker health scope clarification.
For a frontend-only rollback, retain the backend and restore the previous verified frontend Compose pin
`sha256:d3cde0afd9b929fff691643e1d052ef422233594cfead66085d80c2062d5ab96` after compatibility checks.
The older authenticated Phase 1 frontend digest
`sha256:77e36e9c5ab1c19a736fad2ee8fa0d8cdeef81db3e74d53ef4c030825420bb0b` is a historical reference,
not the default rollback target.
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

The current production backend uses a private `HAP_ADMIN_PASSWORD_HASH`.
Do not rotate or alter it for a documentation update.
For a future approved release, generate a hash locally with
`python scripts/hash_admin_password.py`; keep the plaintext password and hash
out of Git. Current main supports `HAP_ADMIN_PASSWORD_HASH_B64`, but the deployed
backend source does not; production still uses raw `HAP_ADMIN_PASSWORD_HASH`.
Switching transport requires a verified backend image and a controlled release.
Base64 is not encryption and its value is equally sensitive. Never set both hash inputs.
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

Verify each service independently: its runtime source SHA and image OCI revision must match that service's expected
source SHA, while the running image digest must match that service's selected digest. Check the backend and frontend
separately; different source SHAs are valid during independent releases. A healthy container alone is not sufficient evidence.

Also confirm the login page, core pages, holdings, transactions, NAV data, and scheduled services remain usable.

## PVE API TLS (candidate, not deployed)

The TLS candidate adds `PVE_CA_BUNDLE` without changing the production configuration.
Production verification remains disabled until a separately approved backend release and cutover.

| Configuration | Request behavior |
| --- | --- |
| `PVE_VERIFY_SSL=false` | Existing compatibility mode (`verify=False`); `PVE_CA_BUNDLE` is ignored and urllib3 warnings remain. |
| `PVE_VERIFY_SSL=true`, bundle unset | Requests default CA trust and normal hostname/IP verification. |
| `PVE_VERIFY_SSL=true`, bundle set | Verify using the supplied readable PEM CA bundle and normal hostname/IP verification. |

When verification is enabled, the URL must use HTTPS. A configured CA file is checked before each request;
missing, unreadable, empty, or malformed files fail closed with a configuration error. The client never retries
with verification disabled. API redirects are not followed. TLS failures report a fixed error without tokens,
certificate contents, or local paths. A CA file alone cannot fix a hostname/IP mismatch.

Example for a future approved configuration (the hostname is a placeholder, not a verified DNS entry):

```dotenv
PVE_URL=https://pve.example.internal:8006
PVE_VERIFY_SSL=true
PVE_CA_BUNDLE=/run/secrets/pve-ca.pem
```

Obtain the **public** cluster CA certificate through an authenticated administrative channel and confirm its
fingerprint independently before trusting it. Proxmox documents the public CA at `/etc/pve/pve-root-ca.pem`;
never copy the CA private key. A certificate collected through an unverified TLS connection is not by itself
an authenticated trust anchor. Do not commit live certificate material or credentials.

A future deployment may mount the approved CA file read-only into the backend and pass `PVE_CA_BUNDLE` to that
container. The file must be readable by the image's non-root `hap` user. An image containing this candidate is
required first; later CA file rotations do not require baking the CA into an image. The current root production
Compose does not pass this new variable or mount a CA file; changing only a host `.env` is insufficient.

Before cutover, verify DNS/routing **from the backend network**, URL-to-SAN identity, CA chain, expiry, and the
container's access to the mounted file. Candidate development did not establish a usable production hostname
or obtain an independently authenticated production CA; no secure production path is claimed yet. Reissuing
a certificate, changing DNS, installing trust, or changing the live URL requires a separate approved task.
Keep the prior image and configuration available for a controlled rollback. This task performs no cutover.

References: [Requests TLS verification](https://requests.readthedocs.io/en/stable/user/advanced/#ssl-cert-verification),
[Proxmox certificate management](https://pve.proxmox.com/pve-docs/chapter-sysadmin.html#sysadmin_certs_api_gui).

## Rollback

Rollback stays within the same `hap` Stack and preserves the same named volumes, network, port, and environment
variables. By default, restore only the affected service to its immediately previous verified image pin, keeping
the other service unchanged. A frontend-only failure uses the previous frontend pin above; a backend-only failure
uses its previous verified backend pin, subject to compatibility, database/schema checks, and a usable backup.
Do not automatically roll both services back to Phase 1. The pre-auth source revision
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
