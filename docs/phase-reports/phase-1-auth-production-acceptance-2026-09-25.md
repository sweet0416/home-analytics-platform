# Phase 1 authentication: production acceptance and hash transport follow-up

On 2026-09-25, the `hap` Portainer Git Stack passed Phase 1 functional and data acceptance. This record distinguishes the earlier acceptance report from new candidate work; no production redeploy was done for this document.

| Identity | Accepted production value |
| --- | --- |
| Application source | `283bd97c84aee1a0f1cc9e5671ec4d351e3f2e37` |
| Deployment configuration | `ef800d5f4a7a0656112923ec63d6153a9c6c4e21` |
| Backend image | `ghcr.io/sweet0416/home-analytics-platform-backend@sha256:5fe9a557e8c967877a859c1f84352514fd6143036a3df6b6e5b514081cf7cf5b` |
| Frontend image | `ghcr.io/sweet0416/home-analytics-platform-frontend@sha256:77e36e9c5ab1c19a736fad2ee8fa0d8cdeef81db3e74d53ef4c030825420bb0b` |

The acceptance report recorded healthy backend/frontend, zero restarts, correct login 200, wrong login 401, protected anonymous API 401, authenticated API 200, session persistence and logout invalidation, a complete four-segment hash inside the running backend, SQLite `quick_check=ok`, and preserved business data. Its counts (16 funds, 4 holdings, 70 transactions, 2354 NAV records, 42 report snapshots, 0 account snapshots) are a dated baseline, not fixed future expectations. The pre-cutover SQLite backup was `/app/data/backups/hap_pre_phase1_20260925_052533_5n2px3cj.db`; it passed `quick_check` and `integrity_check` at creation. Do not restore or remove it as part of hash-transport work.

## Incident boundaries

1. First production attempt: the hash was saved in four segments by Portainer but reached the container damaged after Compose interpolation. The backend correctly rejected it and did not start; the deployment was rolled back. An isolated Portainer test reproduced the four-to-three-segment failure class. This is direct observation plus separate reproduction, not proof of every internal parsing step.
2. Second production attempt: redeploy failed before any new application container was created. The underlying cause remains **unknown**; an isolated `manifest unknown` observation must not be promoted to the production root cause.
3. Final attempt: deployment and functional acceptance succeeded with a valid hash whose salt and digest start with digits. A parallel HTTP response capture timed out; the exact successful HTTP status was **not captured**. This instrumentation gap does not undo functional acceptance.

The digit-leading property is a temporary property of the deployed hash, **not** a long-term generation rule. The candidate Base64 transport in `deploy/hash-transport-test/` is separate from production and requires a new backend image. Base64 is not encryption. Its value must stay in private Portainer configuration. The production root Compose file and accepted image pins remain unchanged until a separately reviewed release.

For future releases, prefer the accepted Phase 1 digest as a rollback baseline after database-compatibility review. The older pre-auth images are emergency references only: they lack unified API authentication and reverting to them degrades security.

## Transport evidence and references

Data path: local PBKDF2 generation → private Portainer Stack variable → Compose interpolation → container environment → `Settings.admin_password_hash()` → existing PBKDF2 validation and login. The candidate encodes the *entire* UTF-8 hash as strict Base64 before the interpolation boundary and compares the decoded value to the generated value in tests. It rejects ambiguous dual inputs. Shell quoting, a local `.env` file, service `env_file`, and the Portainer Stack variable editor are different parsing layers; a rule from one does not establish behavior in another. On this Portainer Git Stack UI, `stack.env` must already be in the repository, so a private `env_file: format: raw` cannot be assumed to exist. The candidate keeps the secret out of Git.

References: [Compose interpolation](https://docs.docker.com/reference/compose-file/interpolation/), [Compose `.env` rules](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/), [service `env_file` and version requirement](https://docs.docker.com/reference/compose-file/services/), [SQLite Online Backup API](https://sqlite.org/backup.html), [SQLite corruption guidance](https://www.sqlite.org/howtocorrupt.html).

On 2026-09-25 the candidate was tested against Portainer CE 2.27.9 in the isolated Git Stack `hap-hash-transport-test-20260925` (ID 32), using a separately built local backend image from candidate code commit `52899c327cf5b77ce09ef1498dcbcbbd56da20b2`. Stack creation and a later manual Git pull/redeploy both succeeded. A synthetic letter-leading hash matched the generated value exactly in the container; the backend was healthy, anonymous access returned 401, bad login 401, correct login 200, and the authenticated route 200. The test Stack, container, network, volume, and local candidate image were removed afterwards. Production `hap` was not redeployed. This confirms the tested Portainer route, not a production release of the candidate.

## HTTP capture rule for any future *test-stack-only* redeploy

Arm response capture **before** the UI click. Filter by method, API path, endpoint ID, and the freshly resolved isolated Stack ID; associate the observed request with its own response rather than presuming a request was issued. Record status and a redacted response category only. If the request is not observed, report `REQUEST_NOT_OBSERVED`. If it is observed but no response arrives before the deadline, report `CAPTURE_TIMEOUT` with no invented status or deployment conclusion. A network disconnect is `CONNECTION_INTERRUPTED`, also without a fabricated status. Never automatically retry a redeploy POST after a timeout. Scope any server-log and Docker-event windows to the isolated Stack and redact values before display or persistence. This procedure was not retroactively applied to the final successful production attempt.
