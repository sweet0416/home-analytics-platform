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

## Actual GitHub Actions and GHCR validation

Implementation commit: `ad83c74451128d4dfba90b8d3d6279f6c3790e53`

Workflow run: `32435803419` (push to `main`), conclusion `success`.

| Image | Immutable tag | Digest | Build | Push |
| --- | --- | --- | --- | --- |
| `ghcr.io/sweet0416/home-analytics-platform-backend` | `sha-ad83c74451128d4dfba90b8d3d6279f6c3790e53` | `sha256:50c442f17e3ff5866d564fb298f37f4ff4226aeb68ba7e0a1ab2ad480518c6c3` | PASS | PASS |
| `ghcr.io/sweet0416/home-analytics-platform-frontend` | `sha-ad83c74451128d4dfba90b8d3d6279f6c3790e53` | `sha256:a3ec4551432988e1f56b682ce87d4a0988371ad55007351aa50fb3c1c11e5224` | PASS | PASS |
| `ghcr.io/sweet0416/home-analytics-platform-ttskill-agent` | `sha-ad83c74451128d4dfba90b8d3d6279f6c3790e53` | `sha256:d9a76919df1bedd4f366e38d4aabe7e69e0de8dd831c134f94bdb2f614843e39` | PASS | PASS |

The GHCR API confirmed both `main` and the immutable SHA tag for each package. Pulled image metadata confirmed that all three OCI `org.opencontainers.image.revision` labels equal the full commit SHA, and all source labels point to this repository.

The pulled backend image contained matching `APP_BUILD_SHA`, `APP_BUILD_TIME`, and `APP_IMAGE_REFERENCE` values. The pulled frontend image contained matching `git_commit`, `build_time`, and version fields in `build-info.json`.

GitHub emitted a non-blocking warning that several actions currently target Node.js 20 while the hosted runner is forcing Node.js 24. The run completed successfully; action major-version migration can be handled separately when the official action compatibility guidance requires it.

`GITHUB_RUN_VALIDATION=PASS`
`PROVENANCE_VALIDATION=PASS`
`PHASE_2_FINAL_GATE=PASS`
