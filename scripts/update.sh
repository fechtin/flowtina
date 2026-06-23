#!/usr/bin/env bash
#
# Update Flowtina: backup -> pull -> deps -> migrate -> build -> restart -> health.
#
set -euo pipefail

APP_DIR="${FLOWTINA_DIR:-/opt/flowtina}"
log() { echo -e "\033[1;34m[update]\033[0m $*"; }

log "Backing up database..."
bash "${APP_DIR}/scripts/backup.sh"

log "Pulling latest code..."
if [[ -d "${APP_DIR}/backend/.git" ]]; then
  ( cd "${APP_DIR}/backend" && git pull --ff-only )
fi

log "Installing backend dependencies..."
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"

log "Running migrations..."
( cd "${APP_DIR}/backend" && "${APP_DIR}/venv/bin/alembic" upgrade head )

if command -v npm &>/dev/null; then
  log "Building frontend..."
  ( cd "${APP_DIR}/frontend" && npm install && npm run build )
fi

log "Restarting services..."
systemctl restart flowtina-api flowtina-scheduler

log "Health check..."
for _ in $(seq 1 15); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    log "Update complete and healthy."
    exit 0
  fi
  sleep 2
done
echo "Health check failed after update. Consider scripts/rollback.sh" >&2
exit 1
