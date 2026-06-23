# SPEC.md

# AI Content Automation Platform

Version: 1.0

---

# Vision

Build a production-grade AI content automation platform that runs continuously and automatically:

* Generate content with AI.
* Aggregate information from Internet sources.
* Publish to Facebook Pages.
* Support multiple AI providers.
* Send reports to Telegram.
* Multi-user.
* Multi-project.
* Multi-language.
* Responsive UI.
* Work on low-end VPS.

---

# Design Principles

* Clean Architecture
* SOLID
* Repository Pattern
* Service Layer
* Dependency Injection
* Event-driven workflow
* Low memory footprint
* SQLite-first
* No Docker required
* No Redis required
* No Celery required

---

# Tech Stack

Backend

* Python 3.12
* FastAPI
* SQLAlchemy
* Alembic
* APScheduler
* Loguru

Frontend

* Vue3
* TypeScript
* Vite
* TailwindCSS
* shadcn-vue
* Pinia
* Vue-i18n

Database

Default:

SQLite

Optional:

PostgreSQL

---

# Modules

## Authentication

Features

* Register
* Login
* Refresh token
* Forgot password
* Change password
* Profile

---

## Projects

Each user can have multiple projects.

Project contains:

* AI provider
* Prompts
* Sources
* Schedules
* Facebook Pages
* Telegram settings

---

## AI Providers

Supported:

### OpenAI

### Gemini

### Claude

### OpenRouter

### DeepSeek

### Ollama

### LM Studio

### vLLM

### OpenAI-compatible endpoints

User chooses provider.

---

## Prompt System

Layers

Global Prompt

↓

Project Prompt

↓

Content Type Prompt

↓

Runtime Variables

↓

Final Prompt

Variables:

```text
{{date}}
{{time}}
{{topic}}
{{language}}
{{hashtags}}
{{source_content}}
```

---

## Content Sources

RSS

URL

CSV

TXT

Keyword list

API

Manual topic

Google News RSS

---

## Content Types

Short Post

Long Post

News Summary

Question

Quote

Marketing

Educational

Tech

Crypto

Motivational

---

## Content Pipeline

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

Quality filters

↓

Save draft

↓

Schedule

↓

Publish

↓

Telegram report

↓

Logging

---

## Scheduler

Based on APScheduler.

Supported:

* interval
* cron
* daily
* weekly
* monthly
* random interval

Recovery after restart supported.

---

## Facebook Module

Official Graph API only.

Capabilities:

* Publish post
* Publish image
* Schedule post
* Delete post
* Insights

No browser automation.

---

## Telegram Module

Daily report

Weekly report

Monthly report

Error report

System status

Manual test

---

## Dashboard

Cards

Posts today

Success rate

Failed posts

Token usage

AI cost

Jobs

Facebook pages

Charts

Execution history

---

## Settings

Theme

Timezone

Language

Budget

Retry

Default prompt

Default model

---

## Languages

English

Vietnamese

Switch without reload.

---

# Performance Targets

VPS:

1 CPU

1GB RAM

Memory target:

<300MB

CPU idle:

<5%

Single process

No Redis

No Celery

---

# Logging

system.log

api.log

scheduler.log

facebook.log

telegram.log

ai.log

Rotation:

30 days

---

# Security

bcrypt

JWT

rate limit

API key encryption

Audit logs

Input validation

XSS prevention

SQL injection prevention

---

# Deployment

Ubuntu 22.04

systemd

Nginx

SQLite

No Docker

Auto restart

Backup

---

# Future Plugins

Instagram

Threads

Twitter X

LinkedIn

WordPress

TikTok

YouTube

Telegram Channel

Discord

Email

---

# Development Roadmap

Phase 1

Auth

Users

Projects

Settings

Phase 2

AI providers

Prompt system

Phase 3

Sources

RSS

Topics

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

# Non Functional Requirements

Production-grade only.

No TODO.

No mock code.

Typed code.

Unit tests.

Coverage >80%.

Ready for deployment.
