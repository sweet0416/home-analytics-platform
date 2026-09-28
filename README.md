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
uses this raw hash variable. The deployed backend also supports
`HAP_ADMIN_PASSWORD_HASH_B64` (Base64 of the complete UTF-8 hash), but production
has not switched to it.
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
| Backend | `7ee613bb62666f1c310f9806dd3bcd3a62efbb10` | `sha256:94feb58cbda49360035cb985899408f8c1593752443c43d597faa24d1d551e3a` |
| Frontend | `ad4397d56ae580d579c311254a6c821228be3079` | `sha256:2bc71e461135d37167f9561b448dc19e80d110b0233c5a2c843a1ba396bc2559` |

The backend reliability batch was released on 2026-09-28 using deployment-configuration
commit `09d2020b39b15a5b6772a141d8f1ca35677c4ea4`. The production database
Alembic revision is `20260927_1200`.

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

### Health database probe (candidate, not deployed)

The candidate keeps `GET /api/v1/system/health` unauthenticated and HTTP 200 for backend
liveness, while reporting database readiness in the existing response envelope:

| Condition | `data.status` | `data.database` | HTTP |
| --- | --- | --- | --- |
| Application engine executes `SELECT 1` | `ok` | `ok` | 200 |
| Database connection/query or file availability fails | `degraded` | `error` | 200 |
| Restore maintenance or fail-closed recovery gate is active | `degraded` | `maintenance` | 200 |

Build/source fields are unchanged. The probe closes its connection after success or failure,
does not issue SQL writes, migrations, table creation, `quick_check` or `integrity_check`, and
checks that a configured SQLite file exists before connecting so it does not recreate a missing
file under the existing coordinated single-worker restore boundary (not arbitrary external file
replacement). `SELECT 1` is **not** a schema, stored-data integrity or write-readiness check; an existing
empty database can pass. It inherits application pool/driver timeouts, not a separate deadline.

The database access holds the existing maintenance activity lease: restore drains in-flight
probes before disposal/replacement, and health requests admitted during maintenance do not open
the database. Successful restore/rollback allows the next request to reconnect; unusable rollback
keeps `maintenance`. After a process crash, the existing restore marker still prevents startup.
The existing container command runs migrations before HTTP serving (`&&`); migration failure
does not start the server. Neither startup order nor recovery protocol changes in this candidate.

The repository Docker probes use HTTP success only. Keeping 200 avoids introducing a new
database-failure HTTP 503/container-unhealthy policy; an actual HTTP timeout can still fail the
probe. No restart policy or Compose change is included, and external production automation was
not inspected. Local tests verify the HTTP-only contract, not a running container deployment.
The existing dashboard accepts these string values and shows non-`ok` health as unavailable.
Docker/PVE notification state does not consume this endpoint and remains unchanged.

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

### Restore safety candidate (not deployed)

The restore candidate adds single-worker maintenance isolation, a mandatory verified safety backup,
Alembic upgrade and database validation before resuming access, and rollback on post-replacement
failure. WAL/SHM or journal sidecars are rejected and preserved. An interrupted restore or failed
rollback requires operator recovery; it must not be retried blindly. See the
[restore safety runbook](docs/restore-safety.md) for the precise boundary and local test command.
This does not change the production image pins or claim that a production restore was tested.
For an isolated, read-only backup recovery exercise, see the
[backup recovery verification guide](docs/backup-recovery-verification.md). Passing a synthetic
test does not verify a production backup.

### SQLite concurrency candidate (not deployed)

The concurrency candidate keeps the current SQLite connection settings and moves fund-profile
provider reads before the update batch, avoiding a reproduced network-held write lock. It does not
enable WAL, foreign keys, or a global write coordinator. See the [isolated concurrency evidence](docs/sqlite-concurrency.md)
for DELETE/WAL experiments, the foreign-key gap, writer inventory and future read-only preflight.

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
- Candidate infrastructure-alert deduplication uses structured, per-channel delivery state with
  one nullable history column; upgrade/legacy behavior and limits are documented in the
  [notification guide](docs/notifications.md#infrastructure-health-deduplication-candidate-behavior).
  This does not indicate a production deployment.
- v1.0.0 checklist: [docs/release-v1.0.0.md](docs/release-v1.0.0.md)
