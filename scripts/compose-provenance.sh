#!/usr/bin/env sh
set -eu

export HAP_GIT_SHA="${HAP_GIT_SHA:-$(git rev-parse HEAD)}"
export HAP_BUILD_TIME="${HAP_BUILD_TIME:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}"
export HAP_BACKEND_IMAGE="${HAP_BACKEND_IMAGE:-hap-backend:local}"
export HAP_FRONTEND_IMAGE="${HAP_FRONTEND_IMAGE:-hap-frontend:local}"
export HAP_TTSKILL_IMAGE="${HAP_TTSKILL_IMAGE:-hap-ttskill-agent:local}"

exec docker compose "$@"
