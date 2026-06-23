# Flowtina — Technical Specification & Architecture

Codename: **AI Content Automation Platform** · Version 1.1

This document merges the original Technical Specification and the Software
Architecture Document (SAD) into a single reference.

---

# 1. Vision & Overview

A production-grade AI Content Automation SaaS that can:

- Run continuously 24/7.
- Generate content with AI and aggregate it from Internet sources (RSS, websites, APIs).
- Schedule and publish content to multiple Facebook Pages.
- Support commercial AI APIs and local LLMs.
- Send reports and notifications to Telegram.
- Support multi-user and multi-project.
- Provide a responsive UI (desktop + mobile) in English and Vietnamese.
- Let users customize AI behavior via System Prompt.
- Run on a low-resource VM (1 CPU / 1 GB RAM), no Docker required.

---

# 2. Goals

1. Generate and publish content automatically.
2. Manage multiple Facebook Pages.
3. Support multiple AI providers.
4. Consume very little resources.
5. Provide a professional UI.
6. Deploy easily on a single VM.
7. Be designed for future extension.

---

# 3. Architecture Principles

- Clean Architecture, SOLID
- Service Layer + Repository patterns, Dependency Injection
- Event-driven internal workflow; async I/O when useful
- Low memory footprint; SQLite-first design
- No Docker / Redis / Celery requirement

---

# 4. Tech Stack

**Backend:** Python 3.12, FastAPI, SQLAlchemy + Alembic, APScheduler, an internal
lightweight queue (no Redis). Database: SQLite (default) / PostgreSQL (optional).

**Frontend:** Vue 3, Vite, TypeScript, TailwindCSS, Shadcn-vue, Pinia, Axios, Vue-i18n.

**Cross-cutting:** JWT auth, i18n (English + Vietnamese).

---

# 5. System Architecture

```
                 Browser
                     |
             Vue3 + Tailwind
                     |
               FastAPI REST API
                     |
---------------------------------------------------
| Auth | Project | Scheduler | Content | AI Provider |
| Facebook | Telegram | Reports | Settings           |
---------------------------------------------------
                     |
                 Service Layer
                     |
              Repository Layer
                     |
                SQLAlchemy ORM
                     |
                  SQLite DB
```

---

# 6. Folder Structure

```
app/
    api/        auth, projects, dashboard, posts, pages,
                prompts, jobs, settings, reports, telegram
    core/       config, security, logger, database, exceptions
    models/  schemas/  repositories/  services/
    scheduler/  providers/  tasks/  prompts/  middlewares/  utils/
frontend/       components, pages, layouts, composables, i18n, public
tests/  logs/  migrations/  database/  uploads/  config/
main.py
```

---

# 7. Domain Model

```
User → Project → AI Provider → Prompt Template → Content Source
     → Scheduler Job → Generated Post → Facebook Publish → Telegram Report
```

---

# 8. Database Schema

Core tables: `users`, `projects`, `ai_providers`, `facebook_pages`, `topics`,
`sources` / `rss_feeds`, `prompts`, `jobs`, `posts`, `post_logs`,
`telegram_configs`, `settings`, `api_keys`, `system_logs`.

Selected columns:

```sql
users:          id, email, password_hash, name, language, timezone, created_at, updated_at
projects:       id, user_id, name, description, active, created_at
ai_providers:   id, project_id, provider, base_url, api_key, model,
                temperature, top_p, max_tokens, system_prompt, enabled
facebook_pages: id, project_id, page_name, page_id, page_token, enabled, created_at
topics:         id, project_id, topic, priority, active
rss_sources:    id, project_id, url, enabled, last_sync
posts:          id, project_id, title, content, hashtags, status, published_at, created_at
jobs:           id, project_id, job_name, cron_expression, enabled, last_run, next_run
telegram_configs: id, project_id, bot_token, chat_id, enabled
logs:           id, level, message, module, created_at
```

`posts.status`: `draft` · `scheduled` · `published` · `failed`

---

# 9. User Roles

- **Admin:** manage all users, view logs, disable accounts.
- **User:** create projects; manage pages, prompts, sources; configure AI;
  schedule posts; view reports.

---

# 10. Authentication

JWT access + refresh tokens, bcrypt password hashing. Features: login, register,
forgot password, email verification, change password, profile, language & timezone.

---

# 11. AI Providers

Supported: OpenAI, Gemini, Claude, OpenRouter, DeepSeek, Ollama, LM Studio, vLLM,
and any OpenAI-compatible endpoint. The user chooses the provider per project.

```python
class BaseAIProvider:
    async def generate(self, prompt: str) -> str: ...

# Implementations: OpenAIProvider, GeminiProvider, ClaudeProvider,
# OpenRouterProvider, DeepSeekProvider, OllamaProvider, LMStudioProvider,
# VLLMProvider, OpenAICompatibleProvider
# Built via AIProviderFactory
```

**Per-project AI config:** provider, API key, model, temperature, top_p,
max_tokens, system prompt, context window, enable memory, language, writing style.

---

# 12. Prompt System

```
Global System Prompt → Project Prompt → Content Type Prompt
   → Topic → Dynamic Context → Final Prompt
```

Templates: news writer, SEO article, short/funny/sales post, tech news, crypto
news, motivational (user-editable).

Variables: `{{date}}`, `{{time}}`, `{{language}}`, `{{topic}}`,
`{{source_content}}` / `{{sources}}`, `{{hashtags}}`, `{{tone}}`.

---

# 13. Content Sources

RSS (feedparser), Google News RSS, custom URLs, website scraping (BeautifulSoup),
manual topics / keyword lists, web APIs (JSON), CSV, TXT, imported feeds.

---

# 14. Content Pipeline

```
Collect source → Deduplicate → Summarize → Generate content
  → Generate image prompt → Generate hashtags → Quality / review filters
  → Schedule → Publish → Record logs → Telegram report
```

---

# 15. Content Types

Short post, long post, article, question, quote, news summary, carousel text,
hashtags, image caption, CTA.

---

# 16. Image Generation Prompt

Generate prompts for DALL·E, Flux, SDXL, ComfyUI, Automatic1111. Prompts are
stored only; actual image generation is optional.

---

# 17. Scheduler

APScheduler with a persistent SQLite job store. Modes: interval (every X minutes),
hourly, daily, weekly, monthly, cron expression, randomized intervals. Timezone
aware. Missed jobs are recovered and executed after a restart.

---

# 18. Facebook Module

Official Graph API only — no browser automation.

```python
FacebookService:
    connect_page() · publish_post() · publish_image()
    schedule_post() · delete_post() · fetch_insights()
```

Capabilities: connect multiple pages, publish text/image/links, schedule and
draft posts, page access token management, status tracking, logging.
Retry: 3 attempts with exponential backoff; all errors logged.

---

# 19. Telegram Module

```python
send_message() · send_daily_report() · send_error_report() · send_system_status()
```

Config: bot token, chat ID. Notifications: post success/failure, daily/weekly/
monthly reports, errors, server health, token usage.

---

# 20. Reports

Daily / weekly / monthly, sent via Telegram. Metrics: posts created, posts
published, failures, AI cost, Facebook pages, success ratio, execution time,
top prompts.

---

# 21. Dashboard

Cards: today's posts, successful/failed posts, Facebook pages, AI usage, token
consumption, jobs, success rate. Charts: post statistics, token usage. Plus the
latest logs.

---

# 22. REST API

```
/auth (login, register, refresh, logout)   /projects (CRUD)
/pages        /posts (CRUD, publish/{id})    /prompts (CRUD)
/sources      /jobs (CRUD)                    /settings
/reports      /telegram (test, config)        /logs       /dashboard
```

---

# 23. UI Architecture & Pages

Vue 3 + Pinia + Axios + Tailwind + Shadcn-vue + Vue-i18n.

Pages: Login, Dashboard, Projects, AI Settings, Prompt Templates (visual editor,
variable preview, live test), Sources (RSS/topics/URLs/CSV import), Jobs (cron
builder, execution logs, next run), Posts (drafts/published/failed/retry),
Telegram (bot setup, test message), Logs (search/filter/download), Settings.

**Mobile UI:** responsive, drawer sidebar, cards, dark mode, touch optimized.

**i18n:** `en` / `vi`, language switch without reload.

```json
{ "dashboard": "Dashboard" }
```

---

# 24. Logging

Per-module rotating logs (`system.log`, `api.log`, `facebook.log`,
`scheduler.log`, `telegram.log`, `ai.log`) via loguru. Levels: DEBUG, INFO,
WARNING, ERROR. Retention: 30 days.

---

# 25. Settings & Config

User settings: theme, language, timezone, retry count, random delay, default
prompt/model, token limit, daily budget.

```yaml
# config.yaml
app:        { host: 0.0.0.0, port: 8000 }
database:   { sqlite_path: database/app.db }
scheduler:  { max_threads: 2 }
logging:    { retention_days: 30 }
```

---

# 26. Security

bcrypt hashing, JWT, rate limiting, API key / channel token encryption at rest,
input validation, XSS protection, SQL injection prevention, CSRF protection,
audit logs.

---

# 27. Performance

Target: 1 CPU / 1 GB RAM, resident memory < 300 MB, idle CPU < 5%. Single
process, async HTTP, connection pooling, lazy loading, in-memory caching,
background scheduler. SQLite (WAL). No Redis / Celery.

---

# 28. Error Handling

Retry 3× with 60 s timeout. Circuit breaker when an AI provider is unavailable,
falling back to the next provider. Failed tasks are stored for manual retry.

---

# 29. Backup

Database backup (scheduled + manual), JSON export/import, restore.

---

# 30. Monitoring

CPU, RAM, disk, jobs, queue size, API latency, scheduler health, Facebook status,
AI provider status.

---

# 31. Testing

pytest, coverage > 80%. Unit, service, repository, API and integration tests.

---

# 32. Code Standards

**Python:** PEP 8, type hints, mypy, ruff, black; async where needed; service
layer, repository pattern, dependency injection.

**Frontend:** Composition API, Pinia, Axios, eslint, prettier, TypeScript strict,
reusable components.

---

# 33. Deployment

Ubuntu 22.04 / 24.04, Python 3.12, SQLite, nginx reverse proxy, systemd services
with auto-restart, log rotation. No Docker / Redis / Kubernetes. See `INSTALL.md`
for the full operations guide.

---

# 34. Sequence — Generate & Publish

```
Scheduler → Fetch Sources → AI Provider → Post Repository
          → Facebook Service → Telegram Service → Logs
```

---

# 35. Plugin Architecture & Future Extensions

Future channels via a plugin interface: Instagram, Threads, Twitter/X, LinkedIn,
WordPress, TikTok, YouTube, Pinterest, Email, Slack, Discord.

---

# 36. Development Roadmap

1. Foundation — auth, project, settings
2. AI module — providers, prompt system
3. Content sources — RSS, URL
4. Scheduler
5. Facebook
6. Telegram
7. Dashboard
8. Optimization
9. Plugin architecture

---

# 37. Deliverables

Backend & frontend source, database migrations, sample config, installation
script, systemd service files, README, API docs, example prompts, example
scheduler configs, sample Telegram bot setup.

---

# 38. Non-functional Requirements

Production quality, clean and modular architecture, easy maintenance, low memory,
scalable, fully typed, well-commented. No mock implementations, no TODO
placeholders — complete and production-ready.

---

# 39. Claude Code Instructions

1. Build incrementally; commit after every module.
2. Generate complete code — never placeholders or TODOs.
3. Create Alembic migrations automatically.
4. Maintain clean architecture (service layer, repository pattern).
5. Create unit tests.
6. Optimize for 1 CPU / 1 GB RAM; keep memory footprint minimal.
7. Use async execution when useful; prefer SQLite + APScheduler.
8. Avoid unnecessary dependencies.
9. Ensure everything runs on Ubuntu without Docker.
10. Produce a complete, production-grade SaaS platform.
