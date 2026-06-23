# AGENT_SYSTEM.md

# Flowtina Agent System Architecture

Version: 1.0

---

# Vision

Flowtina evolves from:

Content Automation Platform

↓

Workflow Platform

↓

AI Agent Platform

↓

AI Operating System

Agents are autonomous modules capable of:

Thinking

Planning

Generating

Executing

Reporting

Collaborating

---

# Design Principles

Low memory usage

Independent agents

Provider agnostic

Plugin-friendly

No Redis

No Celery

Recoverable

Deterministic

Production-ready

---

# Agent Architecture

```text
Trigger
↓
Planner
↓
Agent
↓
Memory
↓
Prompt Engine
↓
AI Provider
↓
Action
↓
Feedback
↓
Logs
```

---

# Base Agent Interface

```python
class BaseAgent:

    async def run(
        self,
        context: dict
    ):
        pass
```

---

# Agent Lifecycle

Initialize

↓

Receive Task

↓

Load Memory

↓

Generate Plan

↓

Execute

↓

Validate

↓

Save Feedback

↓

Complete

---

# Agent Registry

Table

agent_registry

Fields

id

name

type

enabled

version

status

created_at

---

# Agent Types

Content Agent

Research Agent

SEO Agent

Trend Agent

Memory Agent

Reporter Agent

Planner Agent

Quality Agent

Publisher Agent

Optimization Agent

---

# Content Agent

Responsibilities

Generate posts

Generate titles

Generate hashtags

Generate CTA

Summaries

Languages

English

Vietnamese

Future

Japanese

Korean

Chinese

---

Flow

```text
Topic

↓

Prompt Engine

↓

AI Provider

↓

Post

↓

Repository
```

---

# Research Agent

Responsibilities

Analyze sources

Summarize articles

Extract facts

Prepare context

---

Sources

RSS

URL

API

TXT

CSV

Future

Web search

PDF

Knowledge base

---

# SEO Agent

Responsibilities

SEO title

Keywords

Hashtags

Readability

Meta description

Content scoring

---

Metrics

Length

Readability

Keyword density

Duplicate ratio

---

# Trend Agent

Responsibilities

Detect trends

Hot topics

Emerging keywords

Future

Google Trends

Reddit

YouTube

Twitter

News APIs

---

# Memory Agent

Responsibilities

Store

Retrieve

Update

Forget

---

Memory Types

Short-term

Long-term

Project memory

Topic memory

User preferences

Writing styles

---

Future Tables

memory_entries

memory_tags

memory_relations

---

# Reporter Agent

Responsibilities

Daily report

Weekly report

Monthly report

Health summary

AI cost summary

Send Telegram notifications

---

# Planner Agent

Responsibilities

Break tasks into steps

Choose providers

Select prompts

Optimize costs

Fallback strategies

---

Example

```text
Generate article

↓

Summarize

↓

Generate

↓

Score

↓

Publish

↓

Report
```

---

# Quality Agent

Responsibilities

Review generated content

Score quality

Trigger regeneration

---

Metrics

Grammar

Length

Emoji ratio

Hashtags

Readability

AI confidence

Score

0-100

Threshold

60

---

# Publisher Agent

Responsibilities

Schedule

Publish

Retry

History

Future

Multi-channel

---

Channels

Facebook

Threads

WordPress

Telegram

LinkedIn

Twitter

---

# Optimization Agent

Responsibilities

Reduce cost

Choose model

Optimize prompts

Provider fallback

Measure latency

---

# Collaboration Model

```text
Planner Agent

↓

Research Agent

↓

Content Agent

↓

Quality Agent

↓

Publisher Agent

↓

Reporter Agent
```

---

# Agent Communication

Through

Events

Service layer

Shared context

Never direct DB access

---

# Context Object

```python
class AgentContext:

    project_id:str

    topic:str

    language:str

    metadata:dict
```

---

# Memory Architecture

```text
Task

↓

Short-term Memory

↓

Long-term Memory

↓

Prompt Engine

↓

AI Provider
```

Future

RAG support

---

# Event Types

agent.started

agent.finished

agent.failed

agent.timeout

memory.updated

publish.completed

report.sent

---

# Retry Strategy

Attempts

3

Backoff

1s

2s

5s

Timeout

60s

---

# Scheduler Integration

Cron

Interval

Daily

Weekly

Manual

---

# Metrics

Execution count

Success rate

Average duration

Token usage

Cost

Failure count

---

# Health States

healthy

warning

error

disabled

---

# Logs

agent.log

Track

Task ID

Duration

Provider

Model

Result

Error

---

# Future Multi-Agent System

```text
Planner Agent

↓

Research Agent

↓

Memory Agent

↓

Content Agent

↓

SEO Agent

↓

Quality Agent

↓

Publisher Agent

↓

Reporter Agent
```

---

# Future Autonomous Loop

```text
Observe

↓

Think

↓

Plan

↓

Act

↓

Evaluate

↓

Learn
```

---

# Learning

Phase 1

Static

Phase 2

Feedback memory

Phase 3

Optimization

Phase 4

Autonomous improvement

---

# Performance Goals

Memory

<50MB

CPU

Minimal

No background workers

Sequential execution

---

# Absolute Rules

Agents must be independent.

No direct database access.

No provider lock-in.

No Redis.

No Celery.

No infinite loops.

Everything recoverable.

Production-ready only.
