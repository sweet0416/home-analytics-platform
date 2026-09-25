#!/usr/bin/env sh
set -eu

if [ "${HAP_SQLITE_WRITES_STOPPED:-}" != "yes" ]; then
  echo "Refusing hot volume archive: stop all SQLite writers and set HAP_SQLITE_WRITES_STOPPED=yes; use HAP's online database backup while running." >&2
  exit 2
fi

BACKUP_VOLUME="${BACKUP_VOLUME:-hap_backups}"
SQLITE_VOLUME="${SQLITE_VOLUME:-hap_sqlite}"
BACKUP_NAME="hap_sqlite_$(date +%Y%m%d_%H%M%S).tar.gz"

docker run --rm \
  -v "${SQLITE_VOLUME}:/data/sqlite:ro" \
  -v "${BACKUP_VOLUME}:/backup" \
  alpine sh -c "tar czf /backup/${BACKUP_NAME} -C /data sqlite && ls -lh /backup/${BACKUP_NAME}"

echo "Backup created: ${BACKUP_NAME}"
