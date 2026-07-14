#!/usr/bin/env sh
set -eu

BASE_URL="${1:-http://127.0.0.1:8088}"
REQUESTS="${REQUESTS:-20}"

echo "Health endpoint latency sample:"
i=1
while [ "$i" -le "$REQUESTS" ]; do
  curl -fsS -o /dev/null \
    -w "request=%{num_connects} status=%{http_code} time_total=%{time_total}s\n" \
    "$BASE_URL/api/v1/system/health"
  i=$((i + 1))
done

echo
echo "Container resource snapshot:"
docker stats --no-stream hap-backend hap-frontend
