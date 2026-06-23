# AI Auto Content Platform - Technical Specification

# 1. Overview

Build a production-ready SaaS platform that can:

* Automatically generate content using AI.
* Aggregate content from Internet sources (RSS, websites, APIs).
* Schedule and publish content to multiple Facebook Pages.
* Run continuously 24/7.
* Support commercial AI APIs and local LLMs.
* Provide Telegram reports and notifications.
* Support English and Vietnamese.
* Responsive UI for desktop and mobile.
* Allow users to customize AI behavior through System Prompt.
* Work on very small servers (1 CPU, 1GB RAM).
* No Docker required.

Project codename:

AI Content Automation Platform

---

# 2. Goals

The system should:

1. Generate content automatically.
2. Publish automatically.
3. Manage multiple Facebook Pages.
4. Support multiple AI providers.
5. Consume very little resources.
6. Have a professional UI.
7. Be easy to deploy on a single VM.
8. Allow future extension.

---

# 3. Tech Stack

Backend:

Python 3.12

Framework:

FastAPI

ORM:

SQLAlchemy + Alembic

Database:

SQLite (default)
PostgreSQL (optional)

Task Scheduler:

APScheduler

Queue:

Internal lightweight queue (no Redis required)

Frontend:

Vue 3
Vite
TypeScript
TailwindCSS
Shadcn-vue

Authentication:

JWT

Internationalization:

i18n

Languages:

English
Vietnamese

---

# 4. Folder Structure

project/

backend/

api/

models/

services/

scheduler/

providers/

tasks/

repositories/

middlewares/

utils/

prompts/

frontend/

components/

pages/

layouts/

composables/

i18n/

public/

database/

logs/

uploads/

config/

tests/

main.py

---

# 5. User Roles

Admin

Normal User

Admin can:

* manage all users
* view logs
* disable accounts

User can:

* create projects
* manage pages
* manage prompts
* configure AI
* schedule posts
* view reports

---

# 6. Authentication

JWT access token

Features:

Login

Register

Forgot password

Refresh token

Change password

Profile

Language setting

Timezone setting

---

# 7. Dashboard

Show:

Today's posts

Successful posts

Failed posts

Facebook pages

AI usage

Token consumption

Latest logs

Charts

---

# 8. AI Providers

Support:

OpenAI

Gemini

Claude

OpenRouter

DeepSeek

Ollama

LM Studio

vLLM

OpenAI-compatible endpoints

User chooses provider.

---

# 9. AI Configuration

Per project:

Provider

API Key

Model

Temperature

Top P

Max Tokens

System Prompt

Context Window

Enable memory

Language

Writing style

---

# 10. Prompt Templates

Examples:

News writer

SEO article

Short post

Funny post

Sales post

Tech news

Crypto news

Motivational

Users can edit.

Variables:

{{date}}

{{topic}}

{{language}}

{{sources}}

{{hashtags}}

---

# 11. Content Sources

RSS

Google News RSS

Custom URLs

Manual topics

Keyword lists

Web APIs

CSV

TXT

Imported feeds

---

# 12. Content Pipeline

Step 1

Collect source

↓

Step 2

Deduplicate

↓

Step 3

Summarize

↓

Step 4

Generate content

↓

Step 5

Generate image prompt

↓

Step 6

Review filters

↓

Step 7

Schedule

↓

Step 8

Publish

↓

Step 9

Record logs

↓

Step 10

Telegram report

---

# 13. Scheduler

Support:

Every X minutes

Hourly

Daily

Weekly

Cron expression

Random intervals

Timezone support

Missed job recovery

---

# 14. Facebook Integration

Use official Graph API.

Capabilities:

Connect multiple pages

Publish text

Publish image

Publish links

Schedule posts

Draft posts

Page access token management

Auto retry

Status tracking

Logging

Avoid browser automation.

---

# 15. Content Types

Short post

Long post

Article

Question

Quote

News summary

Carousel text

Hashtags

Image caption

CTA

---

# 16. Image Generation Prompt

Generate prompts for:

DALL-E

Flux

SDXL

ComfyUI

Automatic1111

Store prompts only.

Image generation is optional.

---

# 17. Telegram Integration

Bot Token

Chat ID

Notifications:

Post success

Post failed

Daily report

Weekly report

Monthly report

Errors

Server health

Token usage

---

# 18. Reports

Daily

Weekly

Monthly

Metrics:

Posts created

Posts published

Failures

AI cost

Facebook pages

Success ratio

Execution time

Top prompts

Send via Telegram.

---

# 19. Logging

Log levels:

INFO

WARNING

ERROR

DEBUG

Logs:

scheduler.log

api.log

facebook.log

ai.log

telegram.log

system.log

Rotation:

30 days

---

# 20. Database Tables

users

projects

facebook_pages

ai_providers

prompts

topics

sources

rss_feeds

jobs

posts

post_logs

telegram_configs

settings

api_keys

system_logs

---

# 21. Settings

Theme

Language

Timezone

Retry count

Random delay

Default prompt

Default model

Token limit

Daily budget

---

# 22. Multi-language

English

Vietnamese

Use i18n.

Language switch without reload.

---

# 23. UI

Modern SaaS style

Dark mode

Light mode

Responsive

Mobile first

Sidebar

Dashboard cards

Charts

Tables

Search

Pagination

Notifications

Skeleton loading

Professional design

---

# 24. Performance Requirements

Server:

1 CPU

1GB RAM

No Docker

Target memory:

<300MB

SQLite by default

Lazy loading

Background scheduler

No Redis

No Celery

Single process

Low CPU usage

---

# 25. API Endpoints

/auth

/projects

/pages

/posts

/prompts

/sources

/jobs

/settings

/reports

/telegram

/logs

/dashboard

---

# 26. Security

Encrypt API keys

Rate limiting

JWT

Password hashing

Audit logs

CSRF protection

Input validation

SQL injection prevention

XSS protection

---

# 27. Backup

Database backup

Export JSON

Import JSON

Restore

Manual backup

Scheduled backup

---

# 28. Monitoring

CPU

RAM

Disk

Jobs

Queue size

API latency

Scheduler health

Facebook status

AI provider status

---

# 29. Future Extensions

Instagram

Threads

Twitter/X

LinkedIn

WordPress

TikTok

YouTube

Pinterest

Email

Slack

Discord

---

# 30. Coding Standards

Python:

PEP8

Type hints

Async where needed

Service layer pattern

Repository pattern

Dependency injection

Frontend:

Composition API

Pinia

Axios

Reusable components

---

# 31. Deployment

Ubuntu 22.04

Python 3.12

SQLite

systemd service

Nginx reverse proxy

PM2 for frontend

No container

Auto restart

Log rotation

---

# 32. Deliverables

Backend source code

Frontend source code

Database migrations

Sample config

Installation script

systemd service files

README

API docs

Example prompts

Example scheduler configs

Sample Telegram bot setup

---

# 33. Non-functional Requirements

Production quality

Clean architecture

Modular

Easy maintenance

Low memory

Scalable

Typed code

Extensive comments

No mock implementations

No TODO placeholders

Complete implementation

Ready for production

---

# IMPORTANT

Claude Code should:

1. Build incrementally.
2. Create migrations automatically.
3. Generate complete code.
4. Avoid placeholders.
5. Maintain clean architecture.
6. Optimize for 1CPU and 1GB RAM.
7. Use asynchronous execution when useful.
8. Prefer SQLite and APScheduler.
9. Keep memory footprint minimal.
10. Produce production-grade code.
