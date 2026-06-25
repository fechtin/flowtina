# Flowtina Build Plan

Goal: build a complete, runnable, production-grade core of the Flowtina AI Content
Automation Platform per the spec `.md` files. Clean Architecture, SOLID, repo + service
layers, SQLite-first, low memory, no Docker/Redis/Celery.

## Backend (FastAPI) — DONE ✅ (28 tests pass, 80% coverage, ruff clean)
- [x] PHASE 1 — Foundation: structure, requirements, config, database, logger, security, exceptions, base model, app factory
- [x] PHASE 2 — Models + Schemas
- [x] PHASE 3 — Repositories (generic base + per-entity)
- [x] PHASE 4 — AI Providers (base + OpenAI-compatible family + Gemini + Claude + factory + fallback)
- [x] PHASE 5 — Prompt Engine (Jinja2 layered rendering + safe variables)
- [x] PHASE 6 — Services (auth, project, provider, ai, prompt, source, content, post, facebook, telegram, dashboard, report, scheduler)
- [x] PHASE 7 — Sources (RSS/topic/keyword) + SHA-256 dedup
- [x] PHASE 8 — Scheduler (APScheduler + SQLAlchemy jobstore) + tasks + standalone runner
- [x] PHASE 9 — API routers (auth, projects, providers, prompts, sources, jobs, posts, facebook, telegram, dashboard, settings, logs, health)
- [x] PHASE 10 — Alembic migration (27 tables) + DB bootstrap
- [x] PHASE 11 — Tests (unit/api) — 80% coverage

## Frontend (Vue 3 + TS) — DONE ✅ (npm run build green, 14 pages, 18 components, 4 stores)
- [x] Scaffold + layouts + stores + services (axios JWT refresh) + i18n (en/vi) + dark mode + all pages
- [x] Independently re-verified: `npm run build` ✓ built in 3.7s, lazy route chunks

## Ops / Deployment — DONE ✅
- [x] config.yaml, .env.example
- [x] install.sh, update.sh, rollback.sh, backup.sh (syntax-checked)
- [x] systemd units (flowtina-api, flowtina-scheduler), nginx conf, gunicorn_conf
- [x] README

## Review (after completion)
- [x] Smoke test backend boot + key endpoints + live scheduler
- [x] Verify frontend build green (independently re-ran npm run build)
- [x] Final summary to user — COMPLETE, ready for review
</content>
</invoke>

---

## Messenger continuous auto-reply — hardening + Meta setup (2026-06-25)
Webhook only enqueues; a scheduler job processes with debounce+coalesce+dedup+retry.
- [x] 1. Model `MessengerEvent` (models/integration.py)
- [x] 2. Migration: table `messenger_events`
- [x] 3. `MessengerEventRepository` (exists_by_mid, list_pending)
- [x] 4. Config flags (inbox tick / debounce / coalesce / max_attempts)
- [x] 5. MessengerService: enqueue_event() + process_inbox() + _send_action (mark_seen/typing)
- [x] 6. Webhook -> enqueue_event (return 200 fast)
- [x] 7. Scheduler job process_messenger_inbox + jobs.py task
- [x] 8. Update + run tests
- [x] 9. docs/messenger-setup.md (App Review pages_messaging, webhook+page subscribe, scopes, 24h window)

### Review (Messenger continuous auto-reply)
- Webhook is now fire-and-forget: enqueue + 200, no AI/network in request path.
- Poller process_messenger_inbox (every 5s, single-instance) debounces 6s, coalesces
  rapid-fire DMs into one reply, dedupes by Meta mid, retries up to 3x, shows seen/typing.
- Tests: 8 messenger + full suite 63 pass; ruff clean; migration d7a8b9c0e1f2 applies.
- Real-world blocker is config not code: App Review for pages_messaging + Live mode +
  page subscribed_apps -> docs/messenger-setup.md.
