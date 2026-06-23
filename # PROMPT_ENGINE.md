# PROMPT_ENGINE.md

# Flowtina Prompt Engine Architecture

Version: 1.0

---

# Vision

The Prompt Engine is the brain of Flowtina.

It is responsible for transforming:

Raw information

↓

Context

↓

Instructions

↓

Variables

↓

AI Prompt

↓

High-quality content

The system must support:

* Multiple prompt layers
* Versioning
* Multi-language
* User customization
* Provider independence
* Prompt profiles
* Future memory support
* Cost optimization

---

# Prompt Flow

```text
Source Content
↓
Language Context
↓
Global Prompt
↓
Project Prompt
↓
Content Type Prompt
↓
Style Profile
↓
Persona
↓
Variables
↓
Final Prompt
↓
AI Provider
```

---

# Layer Architecture

Priority order:

```text
Global Prompt

↓

Project Prompt

↓

Content Type Prompt

↓

Style Profile

↓

Persona

↓

Runtime Variables

↓

Final Prompt
```

Lower layers override upper layers.

---

# Global Prompt

Purpose

System-wide behavior.

Examples

Tone

Formatting

Safety

Language rules

SEO rules

Brand rules

Table

system_prompts

---

# Project Prompt

Per project customization.

Examples

Technology news

Crypto

Motivation

Education

Marketing

Brand voice

---

# Content Type Prompt

Types

short_post

long_post

news

seo

marketing

quote

question

tutorial

story

comparison

---

# Prompt Profiles

Purpose

Reusable writing styles.

Examples

Professional

Friendly

Humorous

Educational

Technical

Formal

Minimalist

Sales

Inspirational

---

Table

prompt_profiles

Fields

name

description

language

active

---

# Personas

Purpose

Make AI behave consistently.

Examples

Tech journalist

Teacher

Copywriter

SEO expert

News editor

Motivational coach

Software architect

Marketing expert

---

Table

personas

---

# Runtime Variables

Supported

```text
{{date}}

{{time}}

{{language}}

{{topic}}

{{source_content}}

{{hashtags}}

{{style}}

{{persona}}

{{tone}}

{{cta}}

{{brand_name}}

{{audience}}

{{max_words}}

{{emoji_level}}
```

---

# Variable Engine

Missing variable

↓

Default value

↓

Render final prompt

Never fail.

---

# Multi-language

Supported

English

Vietnamese

Future

Japanese

Korean

Chinese

Spanish

---

# Language Strategy

Input

↓

Language detection

↓

Prompt language

↓

Output language

---

# Prompt Versioning

Purpose

Rollback

History

A/B testing

Table

prompt_versions

Fields

id

prompt_id

version

content

created_at

---

# Prompt Templates

Examples

Tech News

Crypto News

SEO Article

Motivational

Educational

Marketing

Quote

Facebook Post

Telegram Summary

Daily Report

Weekly Report

---

# Prompt Rendering

Engine

Jinja2

Example

Template

```text
Write a {{tone}} article about {{topic}}.

Source:

{{source_content}}

Language:

{{language}}
```

Rendered

```text
Write a professional article about AI.

Source:

...

Language:

English
```

---

# Prompt Pipeline

```text
Prompt Layers

↓

Merge

↓

Variables

↓

Render

↓

Validation

↓

AI Provider

↓

Response

↓
Store Version
```

---

# Validation

Check

Empty prompt

Too long

Missing variables

Unsupported language

Invalid template

---

# Length Profiles

Short

100 words

Medium

300 words

Long

1000 words

Custom

User-defined

---

# Tone Profiles

Professional

Friendly

Casual

Formal

Humorous

Inspirational

Technical

Sales

Neutral

---

# Audience Profiles

General

Developers

Business

Students

Beginners

Experts

Investors

---

# Formatting Rules

Markdown

Plain text

Bullet list

Paragraph

HTML

Facebook optimized

Telegram optimized

---

# Emoji Level

None

Low

Medium

High

---

# Hashtag Strategy

Generate

0-10 hashtags

Remove duplicates

Language-specific

Optional

---

# CTA Profiles

Follow page

Visit website

Comment below

Share post

Read more

Subscribe

Optional

---

# AI Provider Independence

Prompt Engine must not depend on:

OpenAI

Claude

Gemini

Any provider

Only produce final prompt.

---

# Cost Optimization

Short context

↓

Cheap summarizer

↓

Final generator

↓

Short output

Avoid unnecessary tokens.

---

# Prompt Cache

TTL

300 seconds

Memory only

No Redis

---

# A/B Testing

Version A

↓

Version B

↓

Compare

Metrics

Engagement

Cost

Readability

Length

---

# Future Memory Layer

Long-term memory

↓

Project memory

↓

Topic memory

↓

Prompt Engine

Future table

memory_entries

---

# Future RAG

Knowledge base

↓

Retriever

↓

Context

↓

Prompt Engine

↓

Generation

---

# Future Agent Layer

Research Agent

↓

Trend Agent

↓

Memory Agent

↓

Prompt Engine

↓

Content Agent

---

# Example Final Prompt

```text
You are a professional technology journalist.

Write a friendly article.

Topic:

AI News

Source:

{{source_content}}

Target audience:

General users.

Language:

Vietnamese.

Maximum words:

500.

Generate title and hashtags.
```

---

# Metrics

Prompt execution count

Average tokens

Average latency

Success rate

Provider usage

Cost

---

# Performance Goals

Render time

<10ms

Memory

<5MB

No external dependency

---

# Absolute Rules

Prompt Engine must never depend on AI providers.

Variables must never crash rendering.

Versioning required.

Rollback supported.

Provider independent.

Production-ready only.
