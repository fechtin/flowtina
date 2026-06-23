# Flowtina

**Autonomous AI Content Operating System** — a production-grade AI content
automation platform that generates content with AI, aggregates Internet sources,
schedules and publishes to Facebook Pages, and reports to Telegram. Designed to
run 24/7 on a 1 CPU / 1 GB VPS with **no Docker, no Redis, no Celery**.

> Built per the specification documents in this repository (`# *.md`). Clean
> Architecture · SOLID · Repository + Service layers · SQLite-first · async I/O.

---

## Architecture

```
Browser (Vue 3 + Tailwind + Pinia)
        │  REST /api/v1
FastAPI  ── Middlewares (request-id, rate limit)
        │
   API Routers      (no business logic)
        │
   Service Layer    (business logic, orchestration)
        │
  Repository Layer  (DB-only access, soft delete)
        │
  SQLAlchemy 2.x ── SQLite (WAL)   ·   APScheduler (SQLite jobstore)
        │
  Providers (OpenAI/Gemini/Claude/DeepSeek/OpenRouter/Ollama/LM Studio/vLLM)
```

### Backend layout (`backend/app`)
| Folder | Responsibility |
|---|---|
| `core/` | config, database, logger, security (JWT/bcrypt/AES), exceptions |
| `models/` | SQLAlchemy models (UUID PKs, timestamps, soft delete) |
| `schemas/` | Pydantic v2 request/response models |
| `repositories/` | generic + per-entity data access |
| `services/` | auth, project, AI, content pipeline, post, facebook, telegram, dashboard, scheduler |
| `providers/` | AI provider interface + factory + fallback chain |
| `prompts/` | layered Jinja2 prompt engine + defaults |
| `scheduler/` | APScheduler manager + standalone runner |
| `tasks/` | background jobs (generate content, reports, cleanup) |
| `api/` | FastAPI routers |
| `middlewares/` | request logging + rate limiting |

---

## Content pipeline

`collect sources → deduplicate (SHA-256) → summarize (cheap model) → render
layered prompt → generate (provider + fallback) → quality score (regenerate if
< 60) → save draft → schedule → publish (Facebook) → Telegram report → log`.

---

## Local development

Requires **Python 3.12** and **Node 20+**.

```bash
# Backend
cd backend
python3.12 -m venv venv
./venv/bin/pip install -r requirements-dev.txt
cp ../config/.env.example .env          # then set DATABASE_URL=sqlite:///./database/app.db
./venv/bin/alembic upgrade head
./venv/bin/uvicorn app.main:app --reload     # http://localhost:8000/docs

# Tests (80%+ coverage)
./venv/bin/pytest --cov=app

# Frontend
cd ../frontend
npm install
npm run dev                              # http://localhost:5173 (proxies /api -> :8000)
```

The first registered user automatically becomes the admin.

---

## API

- Base URL: `/api/v1`, JWT Bearer auth.
- Interactive docs: `/docs` (Swagger) and `/redoc`.
- Success envelope: `{ "success": true, "message": "", "data": {...} }`.
- Error envelope: `{ "success": false, "error": { "code", "message" } }`.

Key groups: `/auth`, `/projects`, `/providers`, `/prompts`, `/topics` `/rss`
`/keywords`, `/posts`, `/jobs`, `/facebook`, `/telegram`, `/dashboard`,
`/settings`, `/logs`, `/health`.

---

## Production deployment (Ubuntu 22.04)

```bash
sudo bash scripts/install.sh
```

The installer creates the `flowtina` user, `/opt/flowtina`, a venv, runs
migrations, builds the frontend, installs two systemd services
(`flowtina-api`, `flowtina-scheduler`), configures nginx + UFW + fail2ban, and
verifies `/api/v1/health`. Run `certbot --nginx` to enable HTTPS.

Operations scripts: `scripts/backup.sh` (daily, rotates 30), `scripts/update.sh`,
`scripts/rollback.sh`.

### Services
- **flowtina-api** — gunicorn + 1 uvicorn worker, 4 threads (scheduler disabled).
- **flowtina-scheduler** — dedicated APScheduler process (persistent SQLite jobstore, recovers missed jobs on restart).

---

## Performance targets
Memory < 300 MB · idle CPU < 5 % · cold start < 3 s · single process · SQLite WAL.

---

## Security
bcrypt password hashing · JWT access/refresh · AES (Fernet) encryption for API
keys & tokens at rest · per-IP rate limiting · input validation (Pydantic) ·
audit-ready logging · token masking in responses/logs · no root execution.
