# CLAUDE.md

# Flowtina

Autonomous AI Content Operating System

---

# Purpose

Claude Code is responsible for building the entire application incrementally.

Generate production-quality code only.

Never generate placeholder code.

Never generate TODO comments.

Never generate mock implementations.

Everything must be executable.

---

# Core Principles

Follow:

* Clean Architecture
* SOLID
* Repository Pattern
* Service Layer Pattern
* Dependency Injection
* Async-first where beneficial
* Typed code
* Small modules
* Low memory footprint

Target environment:

Ubuntu 22.04

1 CPU

1GB RAM

No Docker

No Redis

No Celery

SQLite default

---

# Backend Stack

Python 3.12

FastAPI

SQLAlchemy 2.x

Alembic

Pydantic v2

Loguru

APScheduler

httpx

bcrypt

PyJWT

feedparser

BeautifulSoup4

cryptography

---

# Frontend Stack

Vue3

TypeScript

Vite

TailwindCSS

shadcn-vue

Pinia

Axios

Vue-i18n

Vue Router

ECharts

---

# Database Rules

Use UUID primary keys.

Every table contains:

created_at

updated_at

deleted_at

No hard delete.

Soft delete only.

Use indexes.

Avoid cascade delete.

One migration per table.

---

# Code Quality

Use:

ruff

black

mypy

pytest

coverage

Strict typing enabled.

No Any type unless unavoidable.

---

# Folder Structure

backend/

api/

core/

models/

schemas/

repositories/

services/

providers/

scheduler/

tasks/

middlewares/

utils/

frontend/

components/

pages/

layouts/

stores/

i18n/

tests/

---

# Commit Rules

Commit after every module.

Example:

```text id="vujgmy"
feat(auth): add jwt authentication

feat(projects): project CRUD

feat(ai): openai provider

feat(rss): rss collector

feat(posts): publish pipeline

feat(facebook): graph api integration
```

---

# Build Order

PHASE 1

Foundation

Tasks:

* project structure
* config
* logger
* database
* exception middleware

Commit

```text id="6xk5ku"
feat(core): foundation
```

---

PHASE 2

Authentication

Tasks

register

login

refresh token

profile

change password

tests

Commit

```text id="c8m7f3"
feat(auth): complete auth module
```

---

PHASE 3

Projects

CRUD

Commit

```text id="n8d1sx"
feat(projects): project module
```

---

PHASE 4

AI Providers

Implement:

OpenAI

Gemini

Claude

OpenRouter

DeepSeek

Ollama

LM Studio

vLLM

Factory pattern required.

Commit

```text id="v0vgzi"
feat(ai): providers
```

---

PHASE 5

Prompt System

System prompt

Template prompt

Variables

Versioning

Commit

```text id="zjlwmk"
feat(prompt): prompt engine
```

---

PHASE 6

Sources

RSS

URL

Keyword

API source

Deduplicate

Commit

```text id="mt09fk"
feat(source): content sources
```

---

PHASE 7

Scheduler

APScheduler

SQLite job store

Recovery after restart

Commit

```text id="ghuqx7"
feat(scheduler)
```

---

PHASE 8

Content Pipeline

collect

summarize

generate

hashtags

quality filters

save draft

Commit

```text id="gvtng4"
feat(content): pipeline
```

---

PHASE 9

Posts

CRUD

Versioning

Retry

Commit

```text id="i4e3dl"
feat(posts)
```

---

PHASE 10

Facebook

Graph API only.

No browser automation.

Features

connect page

publish

schedule

history

Commit

```text id="z6n2oi"
feat(facebook)
```

---

PHASE 11

Telegram

Reports

Alerts

Daily summary

Commit

```text id="vtr2gw"
feat(telegram)
```

---

PHASE 12

Dashboard

Charts

Statistics

Recent posts

Commit

```text id="0h2jz7"
feat(dashboard)
```

---

PHASE 13

Frontend

Responsive UI

Dark mode

i18n

Commit

```text id="t9l9na"
feat(frontend)
```

---

PHASE 14

Optimization

Memory optimization

Connection pooling

Caching

Commit

```text id="9xj4j6"
perf(system)
```

---

# AI Provider Interface

```python id="shh5bf"
class BaseAIProvider:

    async def generate(
        self,
        prompt:str
    )->str:
        pass
```

Use factory pattern.

Never duplicate code.

---

# Error Handling

Global exception middleware.

Retry:

3 times.

Timeout:

60 seconds.

Circuit breaker:

AI provider unavailable.

Fallback provider supported.

---

# Scheduler Rules

APScheduler only.

No Celery.

No Redis.

Jobs must survive restart.

---

# Logging

loguru

Files

system.log

api.log

scheduler.log

facebook.log

telegram.log

ai.log

Rotation:

30 days

Compression enabled.

---

# Security

bcrypt

JWT

AES encryption

Rate limiting

Input validation

Audit logs

---

# Frontend Rules

Composition API only.

Pinia stores.

Reusable components.

No duplicated pages.

Responsive first.

Dark mode.

English + Vietnamese.

---

# Testing

pytest

Unit tests

API tests

Repository tests

Integration tests

Coverage >80%

---

# Performance Goals

Memory

<300MB

CPU idle

<5%

Cold startup

<3 seconds

---

# Deployment

Ubuntu 22.04

systemd

Nginx

No Docker

SQLite default

---

# Absolute Rules

NEVER:

create TODO code

create mock code

skip tests

skip migrations

skip typing

duplicate logic

hardcode secrets

break clean architecture

use Redis

use Celery

use Docker

Everything generated must be production-ready.
