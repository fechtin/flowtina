# TELEGRAM_PLUGIN.md

# Flowtina Telegram Plugin

Version: 1.0

Plugin Name

telegram

Type

messaging

API

Telegram Bot API

---

# Vision

Telegram acts as the control center and notification system of Flowtina.

Users should be able to monitor the system entirely from their phones.

The plugin must support:

* Reports
* Alerts
* Health notifications
* Backup notifications
* Error notifications
* Multi-project support

---

# Architecture

```text
Scheduler
↓
ReportService
↓
TelegramPlugin
↓
TelegramBotClient
↓
Telegram Bot API
↓
Response
↓
Logs
```

---

# Folder Structure

```text
plugins/telegram/

plugin.py

client.py

services/

schemas/

models/

utils/

config.yaml
```

---

# Services

TelegramPlugin

TelegramBotClient

TelegramReportService

TelegramAlertService

TelegramHistoryService

TelegramHealthService

TelegramBackupService

---

# Database Tables

telegram_configs

telegram_history

---

# telegram_configs

Fields

id

project_id

bot_token_encrypted

chat_id

enabled

created_at

updated_at

deleted_at

---

# telegram_history

Fields

id

type

message

status

duration_ms

error_message

created_at

---

# Configuration

Fields

Bot Token

Chat ID

Enabled

Timezone

Language

---

# Message Types

Daily Report

Weekly Report

Monthly Report

System Alerts

Health Alerts

Backup Notifications

Publish Results

Failure Notifications

Manual Messages

---

# Daily Report

Contents

Posts generated

Posts published

Success rate

Failure count

AI token usage

Estimated AI cost

Execution duration

Provider usage

---

Example

```text
📊 Daily Report

Generated Posts: 12

Published Posts: 11

Failed Posts: 1

Success Rate: 91%

Token Usage: 55k

AI Cost: $0.48

Duration: 4m32s
```

---

# Weekly Report

Statistics

Posts

Cost

Providers

Success ratio

Top projects

---

# Monthly Report

Aggregated metrics

Trends

Costs

Success rates

---

# Error Alerts

Types

Provider timeout

Facebook publish failed

Scheduler stopped

Database unavailable

Backup failed

Disk space low

Unexpected exceptions

---

Example

```text
🚨 Facebook Publish Failed

Project:

AI News

Reason:

Token expired

Time:

2026-06-23 18:00
```

---

# Health Notifications

Status

healthy

warning

critical

---

Components

Database

Scheduler

AI Provider

Telegram

Facebook

Disk

Memory

CPU

---

# Backup Notifications

Messages

Backup created

Backup failed

Restore completed

---

Example

```text
✅ Backup Completed

Filename:

backup_20260623.zip

Size:

23MB
```

---

# Manual Messages

API endpoint

```text
POST /telegram/send
```

Supports

Markdown

Plain text

---

# Retry Policy

Attempts

3

Backoff

1s

2s

5s

Timeout

30 seconds

---

# Multi-project Support

One bot

↓

Many projects

or

Many bots

↓

Many projects

---

# Multi-chat Support

Private chat

Groups

Channels

---

# Markdown Formatting

Supported

Bold

Italic

Code

Lists

Links

Tables as text

---

# Message Queue

Simple in-memory queue

No Redis

No Celery

Sequential execution

---

# Logging

telegram.log

Track

Request ID

Duration

Status

Retries

Errors

---

# Scheduler Integration

Daily

Weekly

Monthly

Custom intervals

---

# Health Check

Bot token validity

Chat access

Response latency

---

# Metrics

Messages sent

Failures

Retries

Average duration

Success rate

---

# Security

Encrypt bot token

Mask token in logs

Never expose secrets

---

# Sequence Diagram

```text
Scheduler

↓

ReportService

↓

TelegramPlugin

↓

TelegramBotClient

↓

Telegram API

↓

Success

↓

History

↓

Logs
```

---

# Future Features

Interactive commands

/buttons

Inline keyboards

Report PDFs

Images

Charts

Voice summaries

AI assistant via Telegram

---

# Telegram Commands

/plans

/status

/reports

/health

/last-post

/retry

/help

Future

---

# Performance Goals

Memory

<10MB

Latency

<2 seconds

CPU usage

Minimal

---

# Absolute Rules

Use Telegram Bot API only.

No polling loops with high CPU usage.

Encrypt bot tokens.

Retry recoverable errors only.

No Redis.

No Celery.

Production-ready only.
