#!/usr/bin/env sh
set -eu

if [ ! -f ".env" ]; then
  cp .env.example .env
fi

docker compose build
docker compose up -d
docker compose ps

echo "HAP should be available at: http://192.168.100.249:${HAP_WEB_PORT:-8088}"

