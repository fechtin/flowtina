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

---

## Cross-post Facebook + Instagram (1 Page -> nhiều nền tảng)

Mở rộng FacebookPage (IG gắn liền 1 FB Page, dùng chung page token).

### Backend — DONE ✅
- [x] Model: FacebookPage += instagram_user_id/username, publish_facebook(def true), publish_instagram(def false); FacebookPost += platform
- [x] Alembic migration e9b0c1d2f3a4 (down=d7a8b9c0e1f2), up/down/up clean
- [x] facebook_service: dò instagram_business_account khi import/connect
- [x] facebook_service: publish() fan-out FB + IG, skip nền tảng đã đăng thành công
- [x] facebook_service: _publish_instagram() 2 bước /media -> /media_publish (ảnh public URL bắt buộc)
- [x] Public media route GET /api/v1/public/posts/{id}/image cho Meta fetch ảnh upload
- [x] Schema FacebookPageOut += IG fields; PATCH /facebook/pages/{id}/platforms
- [x] 2 test mới (cross-post + toggle reject); full suite pass, ruff + mypy sạch

### Frontend — DONE ✅
- [x] types + facebookService.updatePlatforms + FacebookPlatformUpdate
- [x] FacebookPage.vue: card "Nền tảng đăng bài" + toggle FB/IG, trạng thái IG đã liên kết
- [x] i18n en + vi
- [x] vue-tsc type-check sạch

### Verify — DONE ✅
- [x] ruff + mypy backend sạch (chỉ còn lỗi mypy pre-existing ở base.py/logger/ai_service)
- [x] full backend suite pass (70 tests, +2 mới), migration up/down/up sạch
- [x] frontend vue-tsc sạch

### Còn lại (vận hành, không phải code)
- [ ] Meta App Review: instagram_basic + instagram_content_publish (Live mode)
- [ ] IG phải là Business/Creator account liên kết Page; token cần các scope trên
- [ ] Cân nhắc docs/instagram-setup.md (như docs/messenger-setup.md)
</new_string>
</invoke>
