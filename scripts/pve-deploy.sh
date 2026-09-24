#!/usr/bin/env sh
set -eu

# Legacy local-build helper; use only on an isolated development Docker engine.
if [ ! -f ".env" ]; then
  cp .env.example .env
fi

docker compose -f docker-compose.development.yml build
docker compose -f docker-compose.development.yml up -d
docker compose -f docker-compose.development.yml ps

echo "Development HAP should be available at: http://127.0.0.1:${HAP_WEB_PORT:-8088}"
