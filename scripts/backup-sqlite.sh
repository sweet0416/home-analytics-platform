#!/usr/bin/env sh
set -eu

BACKUP_VOLUME="${BACKUP_VOLUME:-hap_backups}"
SQLITE_VOLUME="${SQLITE_VOLUME:-hap_sqlite}"
BACKUP_NAME="hap_sqlite_$(date +%Y%m%d_%H%M%S).tar.gz"

docker run --rm \
  -v "${SQLITE_VOLUME}:/data/sqlite:ro" \
  -v "${BACKUP_VOLUME}:/backup" \
  alpine sh -c "tar czf /backup/${BACKUP_NAME} -C /data sqlite && ls -lh /backup/${BACKUP_NAME}"

echo "Backup created: ${BACKUP_NAME}"
