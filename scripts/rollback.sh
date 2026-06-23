#!/usr/bin/env bash
#
# Roll back the database to the most recent (or specified) backup.
# Usage: rollback.sh [backup_file.zip]
#
set -euo pipefail

APP_DIR="${FLOWTINA_DIR:-/opt/flowtina}"
DB="${APP_DIR}/database/app.db"
BACKUP_DIR="${APP_DIR}/backups"
log() { echo -e "\033[1;33m[rollback]\033[0m $*"; }

BACKUP="${1:-$(ls -1t "${BACKUP_DIR}"/backup_*.zip 2>/dev/null | head -n1 || true)}"
if [[ -z "${BACKUP}" || ! -f "${BACKUP}" ]]; then
  echo "No backup file found to restore." >&2
  exit 1
fi

log "Stopping services..."
systemctl stop flowtina-api flowtina-scheduler || true

log "Restoring ${BACKUP}..."
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
unzip -o "${BACKUP}" -d "${TMP}" >/dev/null
cp "${DB}" "${DB}.pre-rollback" 2>/dev/null || true
cp "${TMP}/app.db" "${DB}"
rm -f "${DB}-wal" "${DB}-shm"

log "Starting services..."
systemctl start flowtina-api flowtina-scheduler

log "Health check..."
for _ in $(seq 1 15); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    log "Rollback complete and healthy."
    exit 0
  fi
  sleep 2
done
echo "Health check failed after rollback." >&2
exit 1
