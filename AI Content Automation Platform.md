# AI Content Automation Platform

## Software Architecture Document (SAD)

Version 1.0

---

# 1. Vision

Build a production-grade AI Content Automation SaaS capable of:

* Running continuously 24/7.
* Automatically generating content from AI or Internet sources.
* Publishing to Facebook Pages.
* Supporting commercial AI APIs and local LLMs.
* Sending reports to Telegram.
* Working on a low-resource VPS (1 CPU / 1GB RAM).
* Supporting multi-user and multi-project.
* Providing beautiful responsive UI.
* Supporting English and Vietnamese.
* Designed with clean architecture and extensibility.

---

# 2. Architecture Principles

Must follow:

* Clean Architecture
* SOLID principles
* Service Layer pattern
* Repository pattern
* Dependency Injection
* Event-driven internal workflow
* Async I/O when useful
* Low memory footprint
* SQLite-first design
* No Docker requirement
* No Redis required
* No Celery required

---

# 3. System Architecture

```
                 Browser
                     |
             Vue3 + Tailwind
                     |
               FastAPI REST API
                     |
---------------------------------------------------
| Auth Module                                        |
| Project Module                                     |
| Scheduler Module                                   |
| Content Module                                     |
| AI Provider Module                                 |
| Facebook Module                                    |
| Telegram Module                                    |
| Reports Module                                     |
| Settings Module                                    |
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

# 4. Folder Structure

```
app/

    api/
        auth.py
        projects.py
        dashboard.py
        posts.py
        pages.py
        prompts.py
        jobs.py
        settings.py
        reports.py
        telegram.py

    core/
        config.py
        security.py
        logger.py
        database.py
        exceptions.py

    models/
    schemas/
    repositories/
    services/

    scheduler/
    providers/
    tasks/
    prompts/
    middlewares/
    utils/

frontend/

tests/

logs/

migrations/

database/

main.py
```

---

# 5. Domain Model

User

↓

Project

↓

AI Provider

↓

Prompt Template

↓

Content Source

↓

Scheduler Job

↓

Generated Post

↓

Facebook Publish

↓

Telegram Report

---

# 6. Database Schema

## users

```sql
id
email
password_hash
name
language
timezone
created_at
updated_at
```

---

## projects

```sql
id
user_id
name
description
active
created_at
```

---

## ai_providers

```sql
id
project_id
provider
base_url
api_key
model
temperature
top_p
max_tokens
system_prompt
enabled
```

---

## facebook_pages

```sql
id
project_id
page_name
page_id
page_token
enabled
created_at
```

---

## topics

```sql
id
project_id
topic
priority
active
```

---

## rss_sources

```sql
id
project_id
url
enabled
last_sync
```

---

## posts

```sql
id
project_id
title
content
hashtags
status
published_at
created_at
```

status:

draft

scheduled

published

failed

---

## jobs

```sql
id
project_id
job_name
cron_expression
enabled
last_run
next_run
```

---

## telegram_configs

```sql
id
project_id
bot_token
chat_id
enabled
```

---

## logs

```sql
id
level
message
module
created_at
```

---

# 7. AI Providers

Interface:

```python
class BaseAIProvider:

    async def generate(
        self,
        prompt:str
    ) -> str:
        pass
```

Implementations:

```
OpenAIProvider
GeminiProvider
ClaudeProvider
OpenRouterProvider
DeepSeekProvider
OllamaProvider
LMStudioProvider
VLLMProvider
OpenAICompatibleProvider
```

Factory:

```python
AIProviderFactory
```

---

# 8. Prompt System

Global System Prompt

↓

Project Prompt

↓

Content Type Prompt

↓

Topic

↓

Dynamic Context

↓

Final Prompt

Variables:

```text
{{date}}
{{time}}
{{language}}
{{topic}}
{{source_content}}
{{hashtags}}
{{tone}}
```

---

# 9. Content Source Module

Sources:

### RSS

feedparser

### Manual topic

keyword list

### API source

json

### Website scraping

BeautifulSoup

### CSV

### TXT

---

# 10. Content Pipeline

```
Fetch source

↓

Deduplicate

↓

Summarize

↓

Generate article

↓

Generate hashtags

↓

Quality check

↓

Schedule

↓

Publish

↓

Logging

↓

Telegram report
```

---

# 11. Scheduler

Use APScheduler.

Supported:

```python
interval
cron
daily
weekly
monthly
randomized interval
```

Recovery:

Missed jobs should execute after restart.

Persistence:

SQLite job store.

---

# 12. Facebook Module

Use Graph API only.

Services:

```python
FacebookService

connect_page()

publish_post()

publish_image()

schedule_post()

delete_post()

fetch_insights()
```

Retry:

3 attempts

Exponential backoff

Logs all errors.

---

# 13. Telegram Module

Services:

```python
send_message()

send_daily_report()

send_error_report()

send_system_status()
```

Reports:

Daily

Weekly

Monthly

---

# 14. Logging

Files:

```
system.log

api.log

facebook.log

scheduler.log

telegram.log

ai.log
```

Rotation:

30 days

loguru

---

# 15. Authentication

JWT

bcrypt

refresh token

access token

forgot password

email verification

---

# 16. REST API

## Auth

```
POST /login

POST /register

POST /refresh

POST /logout
```

---

## Projects

```
GET /projects

POST /projects

PUT /projects/{id}

DELETE /projects/{id}
```

---

## Posts

```
GET /posts

POST /posts

DELETE /posts/{id}

POST /publish/{id}
```

---

## Prompt

```
GET /prompts

POST /prompts

PUT /prompts/{id}
```

---

## Jobs

```
GET /jobs

POST /jobs

PUT /jobs/{id}
```

---

## Telegram

```
POST /telegram/test

GET /telegram/config
```

---

# 17. UI Architecture

Vue3

Pinia

Axios

Tailwind

Shadcn-vue

Vue-i18n

---

# 18. Pages

### Login

### Dashboard

Cards:

* Posts today
* Success rate
* AI tokens
* Facebook pages
* Jobs

Charts:

* Post statistics
* Token usage

---

### Projects

CRUD

---

### AI Settings

Provider

API key

Model

Temperature

System Prompt

---

### Prompt Templates

Visual editor

Variables preview

Live test

---

### Sources

RSS

Topics

URLs

Import CSV

---

### Jobs

Cron builder

Execution logs

Next run

---

### Posts

Drafts

Published

Failed

Retry

---

### Telegram

Bot setup

Test message

---

### Logs

Search

Filter

Download

---

### Settings

Theme

Language

Timezone

Budget

Retry

---

# 19. Mobile UI

Responsive

Drawer sidebar

Cards

Dark mode

Touch optimized

---

# 20. i18n

Languages:

en

vi

Structure:

```json
{
 "dashboard":"Dashboard"
}
```

Language switch without reload.

---

# 21. Security

bcrypt

JWT

rate limiting

API key encryption

input validation

XSS protection

SQL injection protection

audit log

---

# 22. Config File

config.yaml

```yaml
app:

host: 0.0.0.0

port: 8000

database:

sqlite_path: database/app.db

scheduler:

max_threads: 2

logging:

retention_days: 30
```

---

# 23. Systemd

Backend:

```
ai-content-api.service
```

Frontend:

```
ai-content-web.service
```

Auto restart:

always

---

# 24. Performance Targets

Server:

1CPU

1GB RAM

Memory:

<300MB

CPU:

idle <5%

No Redis

No Celery

SQLite

Single process

Async HTTP requests

Connection pooling

Lazy loading

---

# 25. Sequence Diagram

Generate Content

```
Scheduler

↓

Fetch Sources

↓

AI Provider

↓

Post Repository

↓

Facebook Service

↓

Telegram Service

↓

Logs
```

---

# 26. Error Handling

Retry:

3

Timeout:

60s

Circuit breaker:

AI provider unavailable

Fallback:

next provider

Store failed tasks

Manual retry

---

# 27. Plugin Architecture

Future plugins:

Instagram

Threads

Twitter X

LinkedIn

WordPress

Telegram Channel

Discord

YouTube

TikTok

Pinterest

Email

---

# 28. Deployment

Ubuntu 22.04

Python 3.12

Nginx

systemd

SQLite

No Docker

No Redis

No Kubernetes

---

# 29. Testing

pytest

coverage >80%

Unit test

Service test

Repository test

API test

Integration test

---

# 30. Code Standards

Python:

PEP8

type hints

mypy

ruff

black

Frontend:

eslint

prettier

typescript strict

---

# 31. Development Roadmap

Phase 1

Foundation

* Auth
* Project
* Settings

Phase 2

AI module

* Providers
* Prompt system

Phase 3

Content sources

* RSS
* URL

Phase 4

Scheduler

Phase 5

Facebook

Phase 6

Telegram

Phase 7

Dashboard

Phase 8

Optimization

Phase 9

Plugin architecture

---

# 32. Claude Code Instructions

IMPORTANT:

Never create placeholder code.

Never write TODO.

Generate complete implementation.

Use service layer.

Use repository pattern.

Generate Alembic migrations.

Create unit tests.

Optimize for 1CPU + 1GB RAM.

Avoid unnecessary dependencies.

Keep memory low.

Write production-ready code only.

Build incrementally.

Commit after every module.

Ensure everything can run on Ubuntu 22.04 without Docker.

The final result must be a complete production-grade SaaS platform.
