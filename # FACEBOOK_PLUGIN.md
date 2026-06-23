# FACEBOOK_PLUGIN.md

# Flowtina Facebook Plugin

Version: 1.0

Plugin Name

facebook

Type

social

API

Meta Graph API

---

# Goals

Reliable publishing

Multi-page support

Retry support

History tracking

Insights

24/7 operation

Low resource usage

---

# Capabilities

Connect Facebook Pages

Publish text posts

Publish image posts

Scheduled publishing

Publish history

Page insights

Error notifications

Multi-project support

---

# Architecture

```text
Scheduler
↓
PostService
↓
FacebookPlugin
↓
FacebookClient
↓
Meta Graph API
↓
Response
↓
History + Logs
```

---

# Folder Structure

```text
plugins/facebook/

plugin.py

client.py

services/

models/

schemas/

utils/

config.yaml
```

---

# Services

FacebookPlugin

FacebookClient

FacebookPageService

FacebookPublishService

FacebookHistoryService

FacebookInsightService

---

# Database Tables

facebook_pages

facebook_publish_history

facebook_insights

---

# facebook_pages

Fields

id

project_id

page_id

page_name

access_token_encrypted

status

created_at

updated_at

deleted_at

---

# facebook_publish_history

Fields

id

post_id

page_id

facebook_post_id

status

duration_ms

error_message

published_at

---

# Page Connection

Flow

User

↓

OAuth

↓

Long-lived Token

↓

Store encrypted token

↓

Ready

---

# Token Storage

AES encrypted

Never store plain text

Never log token

---

# Multi-page Support

One project

↓

Many pages

Each page has:

Independent token

Independent status

Independent history

---

# Publish Pipeline

```text
Draft

↓

Scheduler

↓

FacebookPublishService

↓

Graph API

↓

Success

↓

History

↓

Telegram Report
```

---

# Publish Status

pending

publishing

published

failed

retrying

---

# Publish Types

Text post

Text + image

Future

Carousel

Video

Reels

---

# Retry Policy

Attempts

3

Backoff

1 second

2 seconds

5 seconds

---

# Timeout

60 seconds

---

# Error Handling

Token expired

Page unavailable

Permission denied

Network timeout

Rate limit

Unknown API error

---

# Error Strategy

Recoverable

Retry

Non-recoverable

Fail

Notify Telegram

Save logs

---

# History

Store

post_id

facebook_post_id

duration

status

error message

response body

---

# Scheduler Integration

Job

↓

PostService

↓

FacebookPlugin

↓

History

↓

Notification

---

# Insights

Supported

Post reach

Impressions

Engagement

Clicks

Reactions summary (aggregated metrics only)

---

# Analytics Tables

facebook_insights

Fields

page_id

post_id

reach

impressions

engagement

clicks

created_at

---

# Logging

facebook.log

Track

Request ID

Duration

Status

Errors

Retries

---

# Health Check

Check

Token validity

Page access

API response latency

Status

healthy

warning

error

---

# Metrics

Publish count

Success rate

Average duration

Failure count

Retry count

---

# Rate Limiting

Avoid burst traffic

Random delay support

Batch size configurable

---

# Multi-language

English

Vietnamese

Future

Japanese

Korean

Chinese

---

# Sequence Diagram

```text
Scheduler

↓

PostService

↓

FacebookPlugin

↓

FacebookClient

↓

Meta Graph API

↓

Success

↓

History Repository

↓

Telegram Reporter
```

---

# Future Features

Instagram Business

Threads

Cross-posting

Media library

Image generation

AI captions

Analytics dashboard

---

# Security

Encrypted tokens

No plain text secrets

Audit logs

Token masking

Timeout protection

---

# Performance Goals

Publish latency

<5 seconds

Memory

<20MB

No background worker

Low CPU usage

---

# Absolute Rules

Use Meta Graph API only.

Never automate user interactions.

Never use browser automation.

Never store plain tokens.

Retry only recoverable failures.

Production-ready only.
