# TESTING.md

# Flowtina Testing Architecture

Version: 1.0

Framework:

pytest

Coverage Target:

> 80%

Goal:

Production-grade reliability

---

# Testing Philosophy

Test business logic first.

Avoid testing framework internals.

No flaky tests.

Tests must run locally.

Tests must be deterministic.

---

# Test Pyramid

```text
                E2E
             Integration
            Repository/API
             Unit Tests
```

Most tests should be unit tests.

---

# Folder Structure

```text
tests/

unit/

integration/

repository/

api/

providers/

services/

scheduler/

facebook/

telegram/

fixtures/

factories/

conftest.py
```

---

# Unit Tests

Services

Repositories

Utils

Prompt engine

Content pipeline

Provider factory

Scheduler logic

Notification logic

Report generation

---

# Repository Tests

UserRepository

ProjectRepository

PostRepository

JobRepository

PromptRepository

AIUsageRepository

SettingsRepository

LogsRepository

Use SQLite in-memory database.

---

# API Tests

Framework

pytest + httpx

Test

Authentication

CRUD

Validation

Error handling

Pagination

Filters

Rate limits

---

# Auth Tests

Register

Login

Refresh token

Invalid password

Expired token

Logout

Profile

Change password

---

# Project Tests

Create

Update

Delete

Soft delete

Search

Pagination

---

# Provider Tests

OpenAI

Gemini

Claude

DeepSeek

OpenRouter

Ollama

LM Studio

vLLM

Factory selection

Fallback chain

Timeout handling

---

# Prompt Engine Tests

Variable rendering

Prompt merge

Versioning

Missing variables

Long context

Language switching

---

# Content Pipeline Tests

Collect

Deduplicate

Summarize

Generate

Hashtags

Draft

Save

Schedule

Retry

---

# Scheduler Tests

Cron

Interval

Recovery

Restart

Missed jobs

Job history

Manual run

Disable

Enable

---

# Facebook Tests

Connect page

Publish post

Retry

Timeout

Error handling

History

Mock Graph API

---

# Telegram Tests

Send message

Daily report

Weekly report

Error alerts

Connection failures

---

# Dashboard Tests

Statistics

Charts

Aggregations

Recent posts

---

# Backup Tests

Create backup

Restore backup

Zip files

Corrupted backups

---

# Integration Tests

Flow:

```text
RSS
↓
Prompt Engine
↓
AI Provider
↓
Save Post
↓
Facebook Publish
↓
Telegram Report
```

End-to-end workflow validation.

---

# Mock Providers

Never call real API during tests.

Create

FakeOpenAIProvider

FakeClaudeProvider

FakeGeminiProvider

FakeFacebookClient

FakeTelegramClient

---

# Fixtures

UserFixture

ProjectFixture

ProviderFixture

PromptFixture

PostFixture

JobFixture

---

# Factories

UserFactory

ProjectFactory

PostFactory

PromptFactory

ProviderFactory

---

# Performance Tests

Memory usage

CPU usage

Scheduler load

Concurrent requests

Goal

1 CPU

1GB RAM

---

# Load Tests

Tool

Locust

Scenarios

Login

Dashboard

Generate content

Publish post

Reports

Target

100 requests/min

---

# Regression Tests

Every bug fixed must include a test.

Never reintroduce bugs.

---

# Security Tests

JWT

Encryption

Rate limits

SQL injection

XSS

Invalid payloads

Unauthorized access

---

# Coverage Rules

Minimum

80%

Critical modules

90%

Auth

AI Providers

Content Pipeline

Scheduler

Facebook

Telegram

---

# CI/CD

GitHub Actions

Steps

Lint

Black

Ruff

Mypy

Unit tests

Integration tests

Coverage

Build frontend

---

# Example Workflow

```yaml
name: CI

on:
 push:
 pull_request:

jobs:

 test:

  runs-on: ubuntu-latest
```

---

# Failure Policy

No merge if

Tests fail

Coverage <80%

Mypy fails

Ruff fails

---

# Snapshot Tests

Dashboard

Responses

Charts

Translations

---

# Frontend Tests

Framework

Vitest

Vue Testing Library

Test

Components

Stores

Pages

Forms

Routing

Theme switching

i18n

---

# E2E Tests

Playwright

Scenarios

Login

Create project

Generate content

Schedule job

Publish

Send telegram report

---

# Database Migration Tests

Alembic

Upgrade

Downgrade

Rollback

---

# Logging Tests

API logs

Scheduler logs

AI logs

Facebook logs

Telegram logs

---

# Error Recovery Tests

Provider timeout

Scheduler crash

Database reconnect

Facebook failure

Telegram failure

Retry chain

---

# Memory Leak Tests

Long-running scheduler

24h simulation

Target

No memory growth

---

# Absolute Rules

No skipped tests

No flaky tests

No real API calls

No hardcoded secrets

Coverage >80%

Production-grade only

