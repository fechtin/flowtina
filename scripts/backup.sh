#!/usr/bin/env bash
#
# Daily SQLite backup with rotation (keeps last 30). Run via cron.
#
set -euo pipefail

APP_DIR="${FLOWTINA_DIR:-/opt/flowtina}"
DB="${APP_DIR}/database/app.db"
BACKUP_DIR="${APP_DIR}/backups"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="${BACKUP_DIR}/backup_${STAMP}.zip"

mkdir -p "${BACKUP_DIR}"

if [[ ! -f "${DB}" ]]; then
  echo "Database not found at ${DB}" >&2
  exit 1
fi

# Use SQLite's online backup API for a consistent snapshot (safe with WAL).
TMP="$(mktemp -d)"
trap 'rm -rf "${TMP}"' EXIT
sqlite3 "${DB}" ".backup '${TMP}/app.db'"
( cd "${TMP}" && zip -q "${OUT}" app.db )

# Verify the archive and rotate.
unzip -tq "${OUT}" >/dev/null
ls -1t "${BACKUP_DIR}"/backup_*.zip 2>/dev/null | tail -n +31 | xargs -r rm -f

echo "Backup created: ${OUT}"
