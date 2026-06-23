# INSTALL.md

# Flowtina — Installation & Operations Guide

Version: 1.1

Production deployment of the Flowtina AI Content Automation Platform on a single
Linux VM. No Docker, no Redis, no Celery.

---

# 1. What gets deployed

- **Backend**: FastAPI served by gunicorn (1 uvicorn worker, 4 threads) on
  `127.0.0.1:8000`. SQLite database (WAL mode).
- **Scheduler**: a separate process running APScheduler with a persistent SQLite
  job store (recovers missed jobs after a restart). Kept out of the web worker so
  the API stays stateless.
- **Frontend**: a static Vue 3 build (`frontend/dist`) served directly by nginx.
- **Reverse proxy**: nginx terminates HTTP/HTTPS and proxies `/api` to the
  backend.

Two systemd units keep everything running 24/7 with auto-restart:
`flowtina-api` and `flowtina-scheduler`.

---

# 2. Requirements

- Ubuntu 22.04 or 24.04 LTS (x86_64)
- 1 CPU / 1 GB RAM / ~20 GB disk (minimum)
- **Python 3.12** (preinstalled on 24.04; install via deadsnakes PPA on 22.04)
- Inbound network access on ports **22, 80, 443**
- A sudo-capable user (the app itself runs as a dedicated non-root `flowtina` user)

Node.js is **only** needed to build the frontend. If you build the frontend on
your own machine and ship the `dist/` folder, the server does not need Node.

---

# 3. Directory layout

```text
/opt/flowtina/
  backend/        FastAPI application + alembic
  frontend/dist/  Prebuilt static frontend served by nginx
  venv/           Python virtual environment
  database/       SQLite database (app.db)
  config/.env     Environment + secrets (chmod 600)
  config/config.yaml
  logs/           Rotating log files
  uploads/        User uploads
  backups/        Database backups
  scripts/        Operations scripts
```

The application runs as the system user `flowtina`. Never run it as root.

---

# 4. Environment file

Location: `/opt/flowtina/config/.env` (copied from `config/.env.example`).

```env
APP_NAME=Flowtina
APP_ENV=production
DATABASE_URL=sqlite:////opt/flowtina/database/app.db
JWT_SECRET=            # long random string
ENCRYPTION_KEY=        # Fernet key; if empty it is derived from JWT_SECRET
LOG_LEVEL=INFO
SCHEDULER_ENABLED=true
```

Generate strong secrets:

```bash
python3.12 -c 'import secrets; print(secrets.token_urlsafe(48))'                       # JWT_SECRET
python3.12 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'  # ENCRYPTION_KEY
```

`.env` is loaded automatically (it sits at `/opt/flowtina/config/.env`, the parent
of the backend working directory). Never commit `.env`. Keep it `chmod 600`.

---

# 5. Install — option A: one command on the server

Copy the repository to the server, then run the installer as root. It installs
packages, creates the `flowtina` user and directories, generates secrets, creates
the venv, runs migrations, builds the frontend (if `npm` is present), installs the
systemd units, configures nginx + firewall, starts the services, and checks
health.

```bash
sudo bash scripts/install.sh
```

# 5. Install — option B: remote deploy with a prebuilt frontend (recommended for 1 GB VMs)

Building the frontend needs more RAM than a 1 GB VM comfortably has, so build it
locally and ship the result. From your workstation:

```bash
# 1. Build the frontend locally
cd frontend && npm install && npm run build && cd ..

# 2. Copy the project to the server (rsync excludes venv, caches, db, .env)
rsync -az --delete \
  --exclude 'backend/venv/' --exclude '**/__pycache__/' \
  --exclude 'backend/database/*.db*' --exclude 'backend/logs/*' --exclude '.env' \
  backend config scripts deploy  user@your-server:/home/user/flowtina_src/
rsync -az --delete frontend/dist  user@your-server:/home/user/flowtina_src/frontend/

# 3. Run the remote deploy script on the server (uses the prebuilt dist; no Node needed)
ssh user@your-server 'sudo SRC=/home/user/flowtina_src bash /home/user/flowtina_src/scripts/remote_deploy.sh'
```

`scripts/remote_deploy.sh` is Ubuntu 22.04/24.04-aware, installs only the runtime
packages (Python venv, nginx, sqlite3), creates the venv, runs migrations, installs
the systemd units, configures nginx + firewall, and verifies health.

---

# 6. What the install does, step by step

```text
Install packages (python3.12-venv, nginx, sqlite3, ufw, fail2ban)
  -> Create flowtina user + /opt/flowtina
  -> Sync backend code + prebuilt frontend dist
  -> Write .env and generate JWT_SECRET / ENCRYPTION_KEY
  -> python3.12 -m venv venv; pip install -r requirements.txt
  -> alembic upgrade head        (creates all tables)
  -> Install systemd units (flowtina-api, flowtina-scheduler)
  -> Configure nginx site + reload
  -> ufw allow 22/80/443; enable fail2ban
  -> chown -R flowtina:flowtina /opt/flowtina; chmod 600 config/.env
  -> systemctl restart services
  -> Health check: GET /api/v1/health
```

Manual equivalents if you prefer to run them yourself:

```bash
cd /opt/flowtina/backend
/opt/flowtina/venv/bin/alembic upgrade head        # migrate
sudo systemctl restart flowtina-api flowtina-scheduler
```

---

# 7. systemd services

```bash
sudo systemctl status   flowtina-api flowtina-scheduler
sudo systemctl restart  flowtina-api flowtina-scheduler
sudo journalctl -u flowtina-api -n 50
sudo journalctl -u flowtina-scheduler -n 50
```

- `flowtina-api`: gunicorn (`-w 1 --threads 4`), `SCHEDULER_ENABLED=false`,
  `MemoryMax=350M`, `Restart=always`.
- `flowtina-scheduler`: runs `python -m app.scheduler.runner`,
  `SCHEDULER_ENABLED=true`, `MemoryMax=200M`, `Restart=always`.

The web process intentionally does **not** run the scheduler; only the dedicated
scheduler service does. This avoids duplicate job execution.

---

# 8. Firewall (two layers)

Both layers must allow inbound 80/443:

1. **Host firewall (ufw)** — the installer runs `ufw allow 22/80/443`.
2. **Cloud / network firewall** — most cloud providers have a separate security
   group / network ACL. Add inbound rules for TCP **80** and **443** there too,
   or the ports stay blocked even though ufw allows them.

Note: some cloud Linux images (notably **Oracle Cloud / OCI**) ship a host
`iptables` ruleset — loaded at boot by `netfilter-persistent` from
`/etc/iptables/rules.v4` — that is evaluated **before** the ufw chains, with a
blanket `REJECT`/`DROP` after the SSH rule. While that ruleset is active, ufw's
allows for 80/443 never take effect. Verify with:

```bash
sudo iptables -S INPUT
```

**ufw is the single firewall manager on this deployment.** The `ufw` package
`Breaks` (conflicts with) `iptables-persistent` / `netfilter-persistent`, so
installing ufw — which the installer does — automatically removes them, and with
them the boot-time loader for that legacy `REJECT`. Do **not** reinstall
`iptables-persistent` alongside ufw; apt would uninstall ufw again.

Because the legacy loader is gone, after a reboot only ufw's rules apply, so
80/443 stay open (ufw is enabled on boot). Confirm and clean up:

```bash
sudo ufw status verbose      # Status: active, with 22/80/443 ALLOW
systemctl is-enabled ufw     # -> enabled (loads on boot)

# Drop the now-orphaned legacy ruleset so a future iptables-persistent
# reinstall can never reintroduce a pre-ufw REJECT:
sudo rm -f /etc/iptables/rules.v4 /etc/iptables/rules.v6
```

Only if ufw is **not** in use (you manage raw iptables yourself) should you insert
ACCEPT rules ahead of the first REJECT/DROP and persist them the classic way —
this removes ufw:

```bash
sudo iptables -I INPUT 5 -p tcp --dport 80  -j ACCEPT
sudo iptables -I INPUT 6 -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent   # NOTE: this removes ufw
sudo netfilter-persistent save
```

(Rule positions may differ — place them before the first REJECT/DROP.)

---

# 9. HTTPS / TLS

The bundled nginx site listens on port 80. Enable HTTPS with Let's Encrypt.

## 9.1 Direct DNS (the domain's A record points straight at the server)

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

certbot obtains the certificate, edits nginx to add a 443 server block, and sets
up automatic renewal (`certbot.timer`). Confirm renewal works:

```bash
sudo certbot renew --dry-run
```

## 9.2 Behind a CDN / proxy (e.g. Cloudflare)

When the domain is proxied, the CDN connects to your origin over 443, so the
origin must serve real TLS or you'll get a "web server is down" (HTTP 521) error.

1. In the nginx site, set `server_name your-domain.com;` (not `_`) — certbot's
   nginx installer needs a matching `server_name` to attach the certificate.
2. Issue and install the certificate as in 9.1. The HTTP-01 challenge works through
   the proxy as long as plain HTTP reaches the origin.
3. On the CDN, set the SSL/TLS mode to **Full (strict)** so traffic is encrypted
   end-to-end (the origin now has a publicly trusted certificate).

nginx version note: on nginx < 1.25 use `listen 443 ssl http2;` (the standalone
`http2 on;` directive requires nginx ≥ 1.25.1).

A ready-to-edit example site config lives in `deploy/nginx.conf`.

---

# 10. Operations scripts

```bash
sudo bash scripts/backup.sh     # consistent SQLite backup -> backups/, keeps last 30
sudo bash scripts/update.sh     # backup -> pull -> deps -> migrate -> build -> restart -> health
sudo bash scripts/rollback.sh   # restore the latest (or a given) backup, then restart
```

Schedule a daily backup with cron (run as the deploy user):

```cron
0 2 * * * /opt/flowtina/scripts/backup.sh >> /opt/flowtina/logs/backup.log 2>&1
```

---

# 11. Health & troubleshooting

```bash
# Health endpoint (database, scheduler-in-process flag, memory, cpu)
curl -s http://127.0.0.1:8000/api/v1/health

# Public health through nginx
curl -s https://your-domain.com/api/v1/health
```

`scheduler` in the API health response reflects only the API process (where the
scheduler is intentionally disabled); the scheduler runs in its own service —
check it with `systemctl status flowtina-scheduler`.

Common checks:

```text
API not responding   -> journalctl -u flowtina-api
Jobs not running      -> journalctl -u flowtina-scheduler
nginx config error    -> sudo nginx -t
Ports unreachable     -> check host iptables/ufw AND the cloud firewall (section 8)
HTTPS 521 behind CDN  -> origin must serve TLS on 443 (section 9.2)
```

---

# 12. Logs

Rotating per-module logs in `/opt/flowtina/logs/`: `system.log`, `api.log`,
`scheduler.log`, `facebook.log`, `telegram.log`, `ai.log`. Retention 30 days,
zip-compressed. A daily maintenance job trims old system-log rows from the DB.

---

# 13. Performance notes

Single gunicorn worker, lazy imports, SQLite (WAL), in-memory LRU caching — no
Redis or Celery. Typical resident memory for the API process is well under the
300 MB target on a 1 CPU / 1 GB VM.

---

# 14. Updating the frontend only

Rebuild locally and sync just the static build, then fix ownership. No restart
needed (nginx serves the new hashed assets immediately):

```bash
cd frontend && npm run build && cd ..
rsync -az --delete frontend/dist/  user@your-server:/home/user/flowtina_src/frontend/dist/
ssh user@your-server '
  sudo rsync -a --delete /home/user/flowtina_src/frontend/dist/ /opt/flowtina/frontend/dist/ &&
  sudo chown -R flowtina:flowtina /opt/flowtina/frontend/dist'
```

If a CDN sits in front, purge its cache (or rely on hashed asset filenames) so
clients pick up the new `index.html`.

---

# 15. Security checklist

- bcrypt password hashing, JWT access/refresh tokens
- API keys and channel tokens encrypted at rest (Fernet/AES)
- `.env` is `chmod 600`, never committed
- Application runs as the non-root `flowtina` user
- HTTPS enforced at the edge; host + cloud firewalls allow only 22/80/443
- fail2ban enabled for SSH
