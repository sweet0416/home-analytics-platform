# Phase 3: Portainer Prebuilt Image Deployment Preparation

## Scope and status

This phase prepares, but does not perform, the migration from Portainer-side local builds to verified GHCR images. Production was not modified, no production image was pulled, and no container, volume, database, environment variable, or Portainer Stack was changed.

## Current and target deployment models

Current model:

```text
Git Repository -> Portainer Git Stack -> Compose build: -> local Docker build -> containers
```

Target model:

```text
Git Commit -> GitHub Actions -> GHCR immutable image -> Portainer pull/recreate -> runtime verification
```

The existing `docker-compose.yml` remains the local development/build model. `docker-compose.production.yml` is now a
standalone production file and should be loaded directly by the Portainer Stack named `hap`.

## Production image model

The standalone production file removes all HAP build paths and requires explicit image references:

- `HAP_BACKEND_IMAGE`
- `HAP_FRONTEND_IMAGE`
- `HAP_TTSKILL_AGENT_IMAGE` when the `ttskill` profile is enabled

The references should use GHCR digest syntax in production, for example `image@sha256:...`. The deployment manifest also records the human-readable Git SHA tag and digest. Digest references provide immutable rollback and eliminate mutable-tag drift; SHA tags remain easier to read and audit in logs. The digest is the production authority. The optional `ttskill-agent` profile has no tag fallback; if the profile is enabled, a verified digest reference is required explicitly.

The external `docker-socket-proxy` keeps its existing security configuration and is pinned to a verified multi-platform
GHCR index digest in the production file. The development Compose file may continue using its existing convenience
tag; production does not.

The Phase 2 source record used for this preparation is revision `ad83c74451128d4dfba90b8d3d6279f6c3790e53`, from successful GitHub Actions run `32435803419`:

- Backend digest: `sha256:50c442f17e3ff5866d564fb298f37f4ff4226aeb68ba7e0a1ab2ad480518c6c3`
- Frontend digest: `sha256:a3ec4551432988e1f56b682ce87d4a0988371ad55007351aa50fb3c1c11e5224`
- ttskill-agent digest: `sha256:d9a76919df1bedd4f366e38d4aabe7e69e0de8dd831c134f94bdb2f614843e39`

These are verified build artifacts for the manifest template, not evidence that production has been deployed.

## Revision and provenance compatibility

`HAP_IMAGE_REVISION` must be the same full Git SHA for the backend, frontend, and enabled agent. The standalone
production file does not declare `APP_BUILD_SHA`, `APP_BUILD_TIME`, or `APP_IMAGE_REFERENCE`, so the container uses the
values baked into the verified GHCR image. Frontend provenance remains baked into the image `build-info.json`; it is
not replaced by an untrusted runtime value. The image OCI revision and deployment SHA must match.

The checked-in example manifest is intentionally marked `NOT_DEPLOYED` and contains placeholders. It is a template, not a claim about the current production deployment.

## Stateful volume firewall

The standalone file explicitly preserves the existing Docker volume names:

- `hap_sqlite`
- `hap_exports`
- `hap_backups`
- `hap_logs`
- `ttskill_data`

The stack must continue to use project name `hap`. Do not rename these volumes, change their driver, use a new project name, or run `docker compose down -v`. The standalone file does not migrate or recreate volumes.

Static validation of the standalone production Compose configuration passed with both the normal service set and the
`ttskill` profile. The configuration contains no `build:` keys for HAP services and retains all five explicit volume
names. Runtime Portainer volume identity remains pending because this phase did not access production.

## GHCR credential requirement

If the packages are private, Portainer needs a registry credential for `ghcr.io` with package read-only access. A dedicated service identity is preferable. Do not put a PAT in Compose, `.env`, this repository, or an image layer. This phase does not create or configure credentials.

## Pre-deployment safety gates

Before any real deployment, record or verify:

1. Target Git SHA and successful Actions run.
2. Backend, frontend, and optional agent digest references.
3. OCI revision equals the target full SHA.
4. Production Compose config contains no `build:` for HAP services.
5. Existing Portainer Stack configuration and project name are recorded.
6. Existing volume identities are recorded.
7. A usable HAP database backup is confirmed.
8. Current container/image state and a previous known-good revision are recorded.

This preparation cannot inspect the live Portainer Stack or verify the real backup state: `NOT_RUN_PENDING_PRODUCTION_ACCESS`.

## Manual Portainer procedure for a later phase

The first deployment should remain manual:

```text
GitHub Actions PASS
-> record SHA/digests
-> backup gate PASS
-> update production image revision/manifest
-> Portainer pull/recreate
-> health checks
-> smoke test
-> runtime provenance verification
-> record deployment manifest
```

No webhook or automatic production deployment is required for the first version.

## Smoke test design

After a future deployment, verify backend/frontend health, login, core pages, backend `/build-info`, backend and frontend Git SHA equality, image reference and digest, no restart loop, no migration error, and preservation of SQLite, backup, export, log, and optional ttskill data. Verify current holdings, trades, and NAV data remain visible.

## Rollback design

Rollback changes only application image references from revision B to the previous known-good revision A tag/digest, then pulls/recreates application containers and repeats the health/provenance checks. It does not touch volumes or restore the database. Code-image rollback is not database rollback.

## Known risks and pending runtime checks

- Live Portainer Stack configuration and current volume identity require production access.
- GHCR private-package credentials are not configured.
- The development Compose file still uses the convenience tag for `docker-socket-proxy`; production is digest-pinned.
- `frontend/pnpm-workspace.yaml` and frontend lockfile concerns remain outside this phase.
- GitHub Actions Node.js 20 deprecation warnings remain a future CI maintenance item.
- Production Compose pull/recreate, health, smoke test, and runtime provenance verification are pending and were not run.

## Static validation record

- `git diff --check`: PASS
- `docker compose -f docker-compose.production.yml config --quiet`: PASS
- Same standalone Compose validation with `--profile ttskill`: PASS
- Production config image/build check: PASS; HAP services have GHCR `image:` references and no `build:` keys
- Runtime provenance override check: PASS; the standalone production file does not replace image-baked build SHA, build time, or image reference
- Immutable image reference check: PASS for the recorded SHA/digest examples
- Manifest template check: PASS; `DEPLOYMENT_TIME=NOT_DEPLOYED`
- Secret-like content scan of new Phase 3 files: PASS
- Production runtime validation: NOT RUN, intentionally prohibited in this phase

The production file no longer uses Compose's `!reset` tag. This removes the previous Portainer parser compatibility
risk. Portainer runtime validation is still required before deployment.

`PORTAINER_CHANGED=NO`
`PRODUCTION_CONTAINER_CHANGED=NO`
`PRODUCTION_IMAGE_PULLED=NO`
`PRODUCTION_VOLUME_CHANGED=NO`
`PRODUCTION_DATABASE_CHANGED=NO`
`PRODUCTION_DATA_CHANGED=NO`
`PRODUCTION_ENV_CHANGED=NO`
`DEPLOYED=NO`
