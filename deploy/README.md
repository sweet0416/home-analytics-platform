# HAP Docker Deployment

This folder stores deployment notes for running HAP on the PVE host Docker environment.

The root `docker-compose.yml` is the digest-pinned production model used by the existing Portainer `hap` Git
Stack. Local builds use `docker-compose.development.yml`. Both describe:

- `hap-backend`: FastAPI backend, SQLite data, logs, exports, backups
- `hap-frontend`: Nginx static frontend and `/api` reverse proxy

The optional `ttskill-agent` service is behind the `ttskill` Compose profile.
It is only for bootstrapping the official Tiantian Fund Skills CLI and is not
started by the normal HAP deployment.

Production uses the root file with immutable GHCR digests; GitOps stays off and deployment is manual. Do not use
the development `build:` flow, `latest`, `docker compose down -v`, or a different Portainer Stack/project identity.
Run the development file only on an isolated Docker engine because its historical container/volume names overlap
production. See [the production deployment guide](../docs/deployment-pve-docker.md).
