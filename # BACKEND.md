# BACKEND.md

# Flowtina Backend Architecture

Version: 1.0

Framework:

FastAPI

Language:

Python 3.12

Architecture:

Clean Architecture

---

# Design Goals

Production-ready

Low memory footprint

1 CPU

1GB RAM

No Docker

No Redis

No Celery

Async I/O when beneficial

Highly maintainable

Plugin friendly

---

# Architecture

```text
Presentation Layer
        ↓
API Layer
        ↓
Service Layer
        ↓
Repository Layer
        ↓
Database Layer
```

Dependencies flow only downward.

Never allow Repository → Service dependency.

---

# Folder Structure

```text
backend/

app/

api/

core/

config.py
database.py
logger.py
security.py
exceptions.py

models/

schemas/

repositories/

services/

providers/

scheduler/

tasks/

prompts/

middlewares/

utils/

tests/
```

---

# Core Module

core/config.py

Responsibilities

* load .env
* load yaml
* validation

Use:

Pydantic Settings

---

core/database.py

Responsibilities

* SQLAlchemy engine
* session management
* connection pooling

SQLite defaults

```python
pool_size=5
max_overflow=5
```

---

core/logger.py

Use:

Loguru

Files

system.log

api.log

scheduler.log

facebook.log

telegram.log

ai.log

Retention

30 days

Compression

zip

---

core/security.py

Responsibilities

JWT

bcrypt

AES encryption

Token utilities

---

# API Layer

Pattern

```python
Router
↓
Service
↓
Repository
```

Routers contain no business logic.

---

Example

auth.py

projects.py

posts.py

jobs.py

prompts.py

settings.py

dashboard.py

telegram.py

facebook.py

---

# Repository Layer

Repository must only communicate with database.

No external API calls.

Example

UserRepository

ProjectRepository

PostRepository

JobRepository

PromptRepository

AIUsageRepository

---

Example

```python
class UserRepository:

    get_by_email()

    create()

    update()

    soft_delete()
```

---

# Service Layer

Business logic only.

Services

AuthService

ProjectService

AIService

PromptService

ContentService

FacebookService

TelegramService

ReportService

SchedulerService

PostService

DashboardService

NotificationService

---

# AI Provider Module

providers/

base.py

openai_provider.py

gemini_provider.py

claude_provider.py

deepseek_provider.py

openrouter_provider.py

ollama_provider.py

lmstudio_provider.py

vllm_provider.py

factory.py

---

Interface

```python
class BaseAIProvider:

    async def generate(
        self,
        prompt:str
    )->str:
        pass
```

---

Factory

```python
provider = AIProviderFactory.create()
```

---

Fallback Chain

Primary

↓

Secondary

↓

Third

If timeout occurs.

---

# Prompt Engine

Layers

Global Prompt

↓

Project Prompt

↓

Content Prompt

↓

Variables

↓

Final Prompt

Variables

```text
{{date}}

{{topic}}

{{language}}

{{source_content}}

{{hashtags}}
```

---

Versioning supported.

---

# Source Engine

RSS

URL

Keyword

API

TXT

CSV

Services

RSSService

URLSourceService

KeywordService

APISourceService

---

Deduplicate Strategy

sha256(content)

stored in source_cache table

Ignore duplicates.

---

# Content Pipeline

Step 1

Collect source

↓

Step 2

Summarize

↓

Step 3

Generate article

↓

Step 4

Generate hashtags

↓

Step 5

Quality filters

↓

Step 6

Save draft

↓

Step 7

Schedule publish

---

ContentService coordinates pipeline.

---

# Scheduler

Use APScheduler only.

No Celery.

No Redis.

Components

SchedulerManager

JobExecutor

JobHistoryService

RecoveryService

---

Supported

cron

interval

daily

weekly

monthly

random interval

---

Jobs persist in database.

Survive restart.

---

# Task Layer

tasks/

generate_content.py

publish_post.py

telegram_report.py

cleanup_logs.py

backup_database.py

sync_rss.py

Each task independent.

---

# Facebook Module

Graph API only.

Services

FacebookPageService

FacebookPublishService

FacebookInsightService

Retry policy

3 attempts

Exponential backoff

Timeout

60 seconds

---

# Telegram Module

Services

TelegramBotService

TelegramReportService

TelegramAlertService

Supported

daily report

weekly report

error notification

system status

---

# Dashboard Module

Services

DashboardService

MetricsService

ChartService

Statistics

posts_today

success_rate

failed_posts

token_usage

cost

---

# Notification Module

Create notification

Mark read

Broadcast

Store history

---

# Backup Module

SQLite backup

JSON export

Restore

Compression

zip

Scheduled backup

---

# File Storage

uploads/

images/

csv/

txt/

backups/

logs/

Max upload

20MB

---

# Health Check

Endpoint

GET /health

Returns

database

scheduler

memory

cpu

disk

provider status

telegram status

---

# Error Handling

Global exception middleware

Custom exceptions

ValidationException

BusinessException

ProviderException

SchedulerException

FacebookException

TelegramException

---

HTTP codes

400

401

403

404

409

429

500

---

# Retry Strategy

AI

3 retries

Facebook

3 retries

Telegram

3 retries

Timeout

60 seconds

Exponential backoff

1s

2s

5s

---

# Logging

Every request logged.

Execution logs

API logs

AI logs

Facebook logs

Telegram logs

Scheduler logs

Request id tracking enabled.

---

# Cache Strategy

Avoid Redis.

Use in-memory LRU cache.

Cache

provider metadata

dashboard statistics

settings

TTL

300 seconds

---

# Performance Targets

Memory

<300MB

CPU idle

<5%

API latency

<100ms

Startup

<3 seconds

---

# Dependency Injection

Use FastAPI Depends.

Singleton

ConfigService

Logger

SchedulerManager

Factory pattern for providers.

---

# Sequence Diagram

Generate Content

```text
Scheduler
↓
SourceService
↓
PromptService
↓
AIService
↓
PostService
↓
FacebookService
↓
TelegramService
↓
LogService
```

---

# Absolute Rules

No business logic in routers.

No SQL in services.

No API calls in repositories.

No duplicated provider code.

No TODO.

No mock implementation.

Everything must be production-ready.
