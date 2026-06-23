# AI_PIPELINE.md

# Flowtina AI Content Pipeline Architecture

Version: 1.0

---

# Vision

Build a fully automated content pipeline capable of continuously:

* Collecting information.
* Filtering noise.
* Generating high-quality content.
* Publishing automatically.
* Reporting results.
* Running 24/7 with low resource usage.

---

# Pipeline Overview

```text
Sources
↓
Normalizer
↓
Deduplicator
↓
Summarizer
↓
Prompt Engine
↓
AI Generator
↓
Post Processor
↓
Quality Scorer
↓
Draft Storage
↓
Scheduler
↓
Publisher
↓
Telegram Report
↓
Analytics
```

---

# Step 1: Source Collection

Supported sources

RSS

Google News RSS

URL

Keyword

API

TXT

CSV

Manual topics

Services

RSSCollector

URLCollector

KeywordCollector

APICollector

---

# Step 2: Source Normalization

Convert everything into:

```python
class SourceDocument:
    id:str
    title:str
    content:str
    source:str
    language:str
    published_at:datetime
```

---

# Step 3: Deduplication

Goal

Avoid generating duplicate posts.

Method

SHA256(content)

Table

source_cache

If hash exists:

Skip

Otherwise:

Continue

---

# Step 4: Summarization

Large content

↓

Compact context

Use

Cheap model first

Example

DeepSeek

Gemini Flash

GPT-4o-mini

Target

1000~3000 chars

---

# Step 5: Prompt Engine

Layers

Global Prompt

↓

Project Prompt

↓

Content Type Prompt

↓

Variables

↓

Final Prompt

Variables

```text
{{date}}

{{topic}}

{{source_content}}

{{language}}

{{hashtags}}
```

---

# Step 6: AI Generation

Provider selected

↓

Fallback chain

↓

Generate

↓

Store raw output

Supported

OpenAI

Gemini

Claude

DeepSeek

OpenRouter

Ollama

vLLM

LM Studio

---

# Step 7: Post Processor

Responsibilities

Clean markdown

Remove duplicate hashtags

Normalize spacing

Fix encoding

Language detection

Add CTA

Generate title

Generate hashtags

---

# Step 8: Quality Scorer

Criteria

Length

Grammar

Duplicate ratio

Readability

Emoji count

Hashtag count

AI confidence

Score

0-100

Threshold

60

Below threshold

Regenerate

Maximum retries

2

---

# Step 9: Draft Storage

Table

posts

Status

draft

Version history enabled.

---

# Step 10: Scheduler

APScheduler

Types

cron

interval

daily

weekly

monthly

random

Persistent jobs

SQLite store

Recovery after restart

---

# Step 11: Publish Pipeline

```text
Draft

↓

Scheduled

↓

Publishing

↓

Published

↓

Reported
```

Status

draft

scheduled

publishing

published

failed

---

# Step 12: Telegram Report

Success

Failure

Duration

Token usage

AI cost

Publish statistics

---

# AI Provider Strategy

Primary

↓

Secondary

↓

Third

Example

Claude

↓

OpenAI

↓

Gemini

Timeout

60 seconds

Retries

3

---

# Cost Optimization

Cheap model

Summarization

↓

Premium model

Final article

↓

Cheap model

Hashtags

Target

Lowest token cost

---

# Language Flow

Input language

↓

Detect

↓

Prompt language

↓

Output language

Supported

English

Vietnamese

Future

Japanese

Korean

Chinese

---

# Content Types

Short Post

Long Post

News

Educational

SEO

Quote

Marketing

Motivation

Tech

Crypto

---

# Content Length

Short

100-300 words

Medium

300-800 words

Long

800-1500 words

---

# Retry Strategy

Generation fails

↓

Retry same provider

↓

Fallback provider

↓

Save error

↓

Telegram alert

---

# Logging

Store

duration_ms

tokens

provider

model

cost

status

---

# Analytics

Posts generated

Publish success

Average tokens

Average cost

Average duration

Failure rate

---

# Memory Goals

Target

<300MB

Rules

No queue system

No Redis

Sequential execution

Limited context

Lazy imports

---

# Sequence Diagram

```text
Scheduler
↓
Collector
↓
Normalizer
↓
Deduplicator
↓
Prompt Engine
↓
AI Provider
↓
Quality Check
↓
Post Repository
↓
Facebook Publisher
↓
Telegram Reporter
↓
Logs
```

---

# Failure Recovery

Provider timeout

Fallback provider

Facebook publish fail

Retry

Telegram fail

Ignore and log

Scheduler restart

Recover pending jobs

---

# Metrics

Generation duration

Average tokens

Cost

Success rate

Failure rate

Provider usage

---

# Future Pipeline

Trend Detection

↓

Research Agent

↓

Memory Retrieval

↓

Prompt Engine

↓

Generate

↓

Image Generation

↓

Multi-channel Publish

↓

Analytics

↓

Self Optimization

---

# Absolute Rules

No duplicated posts.

No infinite retries.

No provider lock-in.

No Redis.

No Celery.

Everything must survive restart.

Production-ready only.
