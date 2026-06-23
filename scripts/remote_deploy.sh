#!/usr/bin/env bash
#
# Remote deploy for Flowtina (Ubuntu 22.04/24.04). Run ON the server with sudo
# after the source has been rsynced to ${SRC} (default /home/ubuntu/flowtina_src).
# Uses a PREBUILT frontend (frontend/dist) so Node is not required on the VM.
#
set -euo pipefail

SRC="${SRC:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
APP_DIR="/opt/flowtina"
APP_USER="flowtina"

log() { echo -e "\033[1;32m[deploy]\033[0m $*"; }

[[ "${EUID}" -eq 0 ]] || { echo "Run with sudo." >&2; exit 1; }

log "Installing system packages..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3.12-venv python3-pip nginx sqlite3 git curl rsync ufw fail2ban

log "Creating ${APP_USER} user..."
id "${APP_USER}" &>/dev/null || useradd -m -s /bin/bash "${APP_USER}"

log "Preparing ${APP_DIR}..."
mkdir -p "${APP_DIR}"/{backend,frontend/dist,database,uploads,logs,backups,config,scripts,ssl}

log "Syncing application code..."
rsync -a --delete \
  --exclude 'venv/' --exclude '__pycache__/' --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' --exclude '.mypy_cache/' --exclude 'database/*.db*' \
  --exclude 'logs/*' --exclude '.env' \
  "${SRC}/backend/" "${APP_DIR}/backend/"
rsync -a --delete "${SRC}/frontend/dist/" "${APP_DIR}/frontend/dist/"
cp -r "${SRC}/scripts/." "${APP_DIR}/scripts/"
cp "${SRC}/config/config.yaml" "${APP_DIR}/config/config.yaml"

log "Configuring environment (.env)..."
ENV_FILE="${APP_DIR}/config/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${SRC}/config/.env.example" "${ENV_FILE}"
  JWT="$(python3.12 -c 'import secrets;print(secrets.token_urlsafe(48))')"
  ENC="$(python3.12 -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())' 2>/dev/null || true)"
  sed -i "s#^JWT_SECRET=.*#JWT_SECRET=${JWT}#" "${ENV_FILE}"
  [[ -n "${ENC}" ]] && sed -i "s#^ENCRYPTION_KEY=.*#ENCRYPTION_KEY=${ENC}#" "${ENV_FILE}"
  sed -i "s#^DATABASE_URL=.*#DATABASE_URL=sqlite:////opt/flowtina/database/app.db#" "${ENV_FILE}"
fi

log "Creating venv and installing backend dependencies..."
[[ -d "${APP_DIR}/venv" ]] || python3.12 -m venv "${APP_DIR}/venv"
"${APP_DIR}/venv/bin/pip" install --upgrade pip -q
"${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt" -q

log "Running database migrations..."
( cd "${APP_DIR}/backend" && "${APP_DIR}/venv/bin/alembic" upgrade head )

log "Installing systemd services..."
cp "${SRC}/deploy/flowtina-api.service" /etc/systemd/system/
cp "${SRC}/deploy/flowtina-scheduler.service" /etc/systemd/system/
systemctl daemon-reload
systemctl enable flowtina-api flowtina-scheduler

log "Configuring nginx..."
# Only install the bootstrap (HTTP-only) site on first deploy. On later runs keep
# the existing config so certbot's TLS server block + redirect are not clobbered
# (overwriting it drops the :443 listener and breaks HTTPS / causes a CDN 521).
NGINX_SITE="/etc/nginx/sites-available/flowtina"
if [[ -f "${NGINX_SITE}" ]]; then
  log "  Keeping existing nginx site (preserving any TLS config)."
else
  cp "${SRC}/deploy/nginx.conf" "${NGINX_SITE}"
fi
ln -sf "${NGINX_SITE}" /etc/nginx/sites-enabled/flowtina
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl restart nginx

log "Setting permissions..."
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
chmod 600 "${ENV_FILE}"

log "Configuring firewall..."
ufw allow 22/tcp || true
ufw allow 80/tcp || true
ufw allow 443/tcp || true
ufw --force enable || true
systemctl enable --now fail2ban || true

log "Starting services..."
systemctl restart flowtina-api flowtina-scheduler

log "Health check..."
for _ in $(seq 1 20); do
  if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
    log "Backend healthy."
    curl -fsS http://127.0.0.1:8000/api/v1/health
    echo
    log "Deployment complete."
    exit 0
  fi
  sleep 2
done
echo "Backend did not become healthy. Check: journalctl -u flowtina-api -n 50" >&2
exit 1
