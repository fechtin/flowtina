#!/usr/bin/env bash
#
# Flowtina one-command installer for Ubuntu 22.04 LTS (no Docker/Redis/Celery).
# Run as root: sudo bash scripts/install.sh
#
set -euo pipefail

APP_DIR="/opt/flowtina"
APP_USER="flowtina"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

log() { echo -e "\033[1;32m[install]\033[0m $*"; }

require_root() {
  if [[ "${EUID}" -ne 0 ]]; then
    echo "Please run as root (sudo)." >&2
    exit 1
  fi
}

install_packages() {
  log "Installing system packages..."
  export DEBIAN_FRONTEND=noninteractive
  apt-get update -y
  apt-get install -y python3.12 python3.12-venv python3-pip nginx git sqlite3 \
    curl build-essential ufw fail2ban
}

create_user() {
  if ! id "${APP_USER}" &>/dev/null; then
    log "Creating system user ${APP_USER}..."
    useradd -m -s /bin/bash "${APP_USER}"
  fi
}

setup_directories() {
  log "Setting up ${APP_DIR}..."
  mkdir -p "${APP_DIR}"/{backend,frontend,database,uploads,logs,backups,config,scripts,ssl}
  # Copy application code (backend + frontend + config + scripts).
  cp -r "${REPO_DIR}/backend/." "${APP_DIR}/backend/"
  cp -r "${REPO_DIR}/frontend/." "${APP_DIR}/frontend/"
  cp -r "${REPO_DIR}/scripts/." "${APP_DIR}/scripts/"
  [[ -f "${APP_DIR}/config/.env" ]] || cp "${REPO_DIR}/config/.env.example" "${APP_DIR}/config/.env"
  cp "${REPO_DIR}/config/config.yaml" "${APP_DIR}/config/config.yaml"
}

generate_secrets() {
  log "Generating secrets in config/.env (if placeholders present)..."
  local env_file="${APP_DIR}/config/.env"
  if grep -q "change-me" "${env_file}"; then
    local jwt enc
    jwt="$(python3.12 -c 'import secrets;print(secrets.token_urlsafe(48))')"
    enc="$(python3.12 -c 'from cryptography.fernet import Fernet;print(Fernet.generate_key().decode())' 2>/dev/null || true)"
    sed -i "s#^JWT_SECRET=.*#JWT_SECRET=${jwt}#" "${env_file}"
    [[ -n "${enc}" ]] && sed -i "s#^ENCRYPTION_KEY=.*#ENCRYPTION_KEY=${enc}#" "${env_file}"
  fi
}

setup_venv() {
  log "Creating virtual environment..."
  python3.12 -m venv "${APP_DIR}/venv"
  "${APP_DIR}/venv/bin/pip" install --upgrade pip
  "${APP_DIR}/venv/bin/pip" install -r "${APP_DIR}/backend/requirements.txt"
}

run_migrations() {
  log "Running database migrations..."
  ( cd "${APP_DIR}/backend" && "${APP_DIR}/venv/bin/alembic" upgrade head )
}

build_frontend() {
  if command -v npm &>/dev/null; then
    log "Building frontend..."
    ( cd "${APP_DIR}/frontend" && npm install && npm run build )
  else
    log "npm not found; skipping frontend build (install Node 20+ and run npm run build)."
  fi
}

install_services() {
  log "Installing systemd services..."
  cp "${REPO_DIR}/deploy/flowtina-api.service" /etc/systemd/system/
  cp "${REPO_DIR}/deploy/flowtina-scheduler.service" /etc/systemd/system/
  systemctl daemon-reload
  systemctl enable flowtina-api flowtina-scheduler
}

configure_nginx() {
  log "Configuring nginx..."
  cp "${REPO_DIR}/deploy/nginx.conf" /etc/nginx/sites-available/flowtina
  ln -sf /etc/nginx/sites-available/flowtina /etc/nginx/sites-enabled/flowtina
  rm -f /etc/nginx/sites-enabled/default
  nginx -t && systemctl restart nginx
}

configure_firewall() {
  log "Configuring firewall..."
  ufw allow 22 || true
  ufw allow 80 || true
  ufw allow 443 || true
  ufw --force enable || true
  systemctl enable --now fail2ban || true
}

set_permissions() {
  chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
  chmod 600 "${APP_DIR}/config/.env"
}

start_services() {
  log "Starting services..."
  systemctl restart flowtina-api flowtina-scheduler
}

health_check() {
  log "Waiting for API health..."
  for _ in $(seq 1 15); do
    if curl -fsS http://127.0.0.1:8000/api/v1/health >/dev/null 2>&1; then
      log "API is healthy. Installation complete!"
      return 0
    fi
    sleep 2
  done
  echo "API did not become healthy. Check: journalctl -u flowtina-api" >&2
  exit 1
}

main() {
  require_root
  install_packages
  create_user
  setup_directories
  generate_secrets
  setup_venv
  run_migrations
  build_frontend
  install_services
  configure_nginx
  configure_firewall
  set_permissions
  start_services
  health_check
}

main "$@"
