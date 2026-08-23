# HAP Docker Deployment

This folder stores deployment notes for running HAP on the PVE host Docker environment.

The root `docker-compose.yml` is the development/local-build Compose model. It starts:

- `hap-backend`: FastAPI backend, SQLite data, logs, exports, backups
- `hap-frontend`: Nginx static frontend and `/api` reverse proxy

The optional `ttskill-agent` service is behind the `ttskill` Compose profile.
It is only for bootstrapping the official Tiantian Fund Skills CLI and is not
started by the normal HAP deployment.

For production, use the standalone `docker-compose.production.yml` with GHCR
images pinned by immutable digest. Do not use the development `build:` flow,
`latest`, `docker compose down -v`, or a different Portainer Stack/project
identity. See [the production deployment guide](../docs/deployment-pve-docker.md).
