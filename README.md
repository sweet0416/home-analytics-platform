# Home Analytics Platform

HAP is a modular HomeLab analytics platform designed for long-term maintenance and Docker
deployment on a PVE host.

Current release: `1.0.0` (tag `v1.0.0`). Later UI and deployment updates have not been
assigned a new release version.

## Modules

- Dashboard
- Fund
- Lottery
- Reports
- Settings
- Docker Monitor
- PVE Monitor

Reserved routes (placeholders only):

- Stocks
- AI Lab
- Automation

## Administrator login

HAP requires one administrator password. Generate its PBKDF2 hash locally with
`python scripts/hash_admin_password.py`, then put the printed hash in
`HAP_ADMIN_PASSWORD_HASH` in private configuration. The current production backend
uses this raw hash variable. Current main also supports
`HAP_ADMIN_PASSWORD_HASH_B64` (Base64 of the complete UTF-8 hash), but the deployed
backend source does not include that support; production has not switched to it.
Base64 is transport encoding, not encryption, and must be protected like the
original hash. Do not set both inputs. The Base64 option avoids Compose interpreting
`$` within the hash. Do not assume local `.env` quoting behavior applies to Portainer
Stack variables. Set
`HAP_COOKIE_SECURE=true` when the browser uses HTTPS.
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

#### Current Production Provenance

The running backend and frontend have independent source revisions and immutable image digests:

| Service | Source SHA | Image digest |
| --- | --- | --- |
| Backend | `283bd97c84aee1a0f1cc9e5671ec4d351e3f2e37` | `sha256:5fe9a557e8c967877a859c1f84352514fd6143036a3df6b6e5b514081cf7cf5b` |
| Frontend | `ad4397d56ae580d579c311254a6c821228be3079` | `sha256:2bc71e461135d37167f9561b448dc19e80d110b0233c5a2c843a1ba396bc2559` |

The production frontend includes the Product UI System V1.2, login focus-state polish,
and host-wide Docker health scope clarification. These are product milestones, not
software release version numbers. Verify each service independently after deployment;
a configuration commit alone does not prove runtime acceptance.

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

## Docker Host Monitoring Scope

The Docker Monitor reports host-wide container status, including stopped containers.
This is separate from HAP's own API and database health indicators.

## Production Deployment Rules

The PVE TLS candidate supports `PVE_CA_BUNDLE` for a PEM CA bundle together with
`PVE_VERIFY_SSL=true`. Both CA trust and a URL matching the certificate SAN are required.
This candidate is not deployed; see [PVE TLS configuration](docs/deployment-pve-docker.md#pve-api-tls-candidate-not-deployed)
for configuration behavior and the separate production cutover prerequisites.

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

The production data volumes are data, not image artifacts:

```text
hap_sqlite
hap_exports
hap_backups
hap_logs
```

They must survive image updates and rollbacks. The optional `ttskill-agent` profile
uses a separate `ttskill_data` volume when enabled; the profile is not enabled in the
current production stack.

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
