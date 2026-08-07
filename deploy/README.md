# HAP Docker Deployment

This folder stores deployment notes for running HAP on the PVE host Docker environment.

The root `docker-compose.yml` starts:

- `hap-backend`: FastAPI backend, SQLite data, logs, exports, backups
- `hap-frontend`: Nginx static frontend and `/api` reverse proxy

The optional `ttskill-agent` service is behind the `ttskill` Compose profile.
It is only for bootstrapping the official Tiantian Fund Skills CLI and is not
started by the normal HAP deployment.
