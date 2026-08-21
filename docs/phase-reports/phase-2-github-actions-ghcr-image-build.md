# Phase 2: GitHub Actions + GHCR Image Build

## Goal

Build the three HAP images on GitHub Actions and publish them to GHCR without changing the production Portainer deployment model.

## Workflow architecture

`.github/workflows/build-ghcr.yml` runs on pushes to `main` and on manual dispatch. A readable matrix builds the real repository contexts:

- `./backend` -> `ghcr.io/sweet0416/home-analytics-platform-backend`
- `./frontend` -> `ghcr.io/sweet0416/home-analytics-platform-frontend`
- `./deploy/ttskill-agent` -> `ghcr.io/sweet0416/home-analytics-platform-ttskill-agent`

The workflow uses the official checkout, Buildx, login, metadata, and build-push actions. It only builds and pushes images; it does not deploy, call Portainer, or modify stateful volumes.

## Tags and provenance

Each image receives an immutable `sha-<full Git SHA>` tag. The `main` tag is a convenience tag only and must not be the sole production provenance reference. The workflow passes `github.sha`, a UTC build timestamp, the actual immutable image reference, and the application version into the Docker build.

OCI metadata includes:

- `org.opencontainers.image.revision`
- `org.opencontainers.image.created`
- `org.opencontainers.image.source`
- `org.opencontainers.image.version`

Backend runtime metadata continues to use the Phase 1 `/build-info` and health information. Frontend `build-info.json` now also carries the application version. The ttskill-agent has image-level provenance labels because it has no HAP HTTP runtime endpoint.

## Permissions and security

The workflow requests only `contents: read` and `packages: write`, and authenticates GHCR with the automatically provided `GITHUB_TOKEN`. It does not print credentials, pass tokens as build arguments, use `pull_request_target`, or deploy production.

## Cache

BuildKit's GitHub Actions cache is scoped per image so backend, frontend, and ttskill-agent layers do not collide. This reduces repeated PyPI, npm, apt, and ttskill package downloads on GitHub-hosted runners.

## GHCR behavior

The first successful package push may create the GHCR packages according to the repository/package visibility rules. This phase does not configure visibility or Portainer registry credentials. If the package is private, a future Portainer deployment will need read-only registry credentials stored in Portainer's credential store.

## Validation boundary

Local validation completed for this working tree:

- Backend full pytest: PASS
- Frontend `vue-tsc --noEmit`: PASS
- `docker compose config --quiet`: PASS
- `git diff --check`: PASS
- Backend, frontend, and ttskill-agent Dockerfile BuildKit `--check`: PASS
- Workflow trigger, permissions, matrix contexts, tags, build args, cache, and secret-safety assertions: PASS

No YAML parser or `actionlint` executable was available locally, so workflow syntax is recorded as static structural validation rather than a full actionlint result. A GitHub-hosted runner has not executed this workflow yet because this phase does not push the workflow changes.

`GITHUB_RUN_VALIDATION=NOT_RUN_PENDING_PUSH`

## Portainer boundary and rollback

The current Compose deployment remains unchanged and continues to use local `build:` configuration. A later deployment phase may introduce a separate production image Compose model after the GHCR images have been built and inspected. Stateful volumes (`hap_sqlite`, `hap_exports`, `hap_backups`, `hap_logs`, `ttskill_data`) must remain unchanged.

Future rollback should select an immutable SHA tag or recorded image digest, recreate only the application containers, run health and runtime-version checks, and verify persistent data before accepting the deployment.

## Known risks

- GitHub Runner validation is pending the user-approved commit and push.
- The `main` convenience tag is mutable by design; production must use the SHA tag and preferably record the digest.
- Private GHCR packages will require a future Portainer pull credential.
- This phase does not automatically deploy or verify a running production container.
