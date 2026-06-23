# PLUGINS.md

# Flowtina Plugin Architecture

Version: 1.0

---

# Vision

Flowtina must be built as a plugin-based platform.

Core system should remain small.

All integrations must be modular.

Future channels and AI providers should be installable without modifying the core.

---

# Plugin Categories

```text
AI Providers

Social Channels

Messaging

CMS

Storage

Analytics

Media

Workflow

Notifications

Utilities
```

---

# Plugin Architecture

```text
Core System
      │
Plugin Manager
      │
----------------------------
│ AI Plugins
│ Social Plugins
│ Messaging Plugins
│ CMS Plugins
│ Analytics Plugins
│ Utility Plugins
----------------------------
```

---

# Folder Structure

```text
plugins/

facebook/

telegram/

openai/

gemini/

claude/

deepseek/

openrouter/

ollama/

wordpress/

threads/

twitter/

linkedin/

youtube/

discord/

email/

base/
```

---

# Base Plugin Interface

```python
class BasePlugin:

    def name(self)->str:
        pass

    def version(self)->str:
        pass

    def enabled(self)->bool:
        pass

    async def initialize(self):
        pass

    async def shutdown(self):
        pass
```

---

# Plugin Metadata

plugin.json

```json
{
  "name":"facebook",
  "version":"1.0.0",
  "author":"Flowtina",
  "type":"social",
  "enabled":true
}
```

---

# Plugin Registry

Table

plugin_registry

Fields

id

name

type

version

enabled

installed_at

updated_at

---

# Plugin Manager

Responsibilities

Discover plugins

Load plugins

Unload plugins

Enable

Disable

Update

Health check

---

Services

PluginManager

PluginLoader

PluginRegistryService

PluginHealthService

---

# AI Provider Plugins

## OpenAI

Models

GPT

o-series

Responses API

---

## Gemini

Google AI Studio

Vertex AI

---

## Claude

Anthropic API

---

## OpenRouter

Multiple providers

---

## DeepSeek

---

## Ollama

Local models

---

## LM Studio

OpenAI-compatible

---

## vLLM

Local inference

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

# Social Plugins

## Facebook

Capabilities

Connect pages

Publish text

Publish image

Insights

History

Retry

Graph API only

No browser automation

---

## Instagram

Future

Business account

Image posts

Reels

---

## Threads

Future

Publish text

Schedule

---

## X / Twitter

Future

Tweet

Thread

Media upload

---

## LinkedIn

Future

Company pages

Post article

---

## Pinterest

Future

Pins

Boards

---

# CMS Plugins

## WordPress

Capabilities

Create posts

Categories

Tags

Images

SEO metadata

---

## Ghost

Future

---

## Medium

Future

---

# Messaging Plugins

## Telegram

Bot

Reports

Notifications

Alerts

---

## Discord

Webhook

Channels

Reports

---

## Slack

Future

---

## Email

SMTP

Daily reports

Error reports

Attachments

---

# Storage Plugins

## Local Storage

Default

uploads/

---

## S3

Future

---

## Cloudflare R2

Future

---

## Google Drive

Future

---

# Analytics Plugins

## Internal Metrics

Posts

Tokens

Costs

Errors

---

## Google Analytics

Future

---

## Plausible

Future

---

# Media Plugins

## DALL-E

Prompt only

---

## Flux

Prompt only

---

## SDXL

Prompt only

---

## ComfyUI

Future

---

## Automatic1111

Future

---

# Notification Plugins

Telegram

Discord

Email

Slack

---

# Workflow Plugins

Future

If

Then

Condition

Delay

Loop

Branch

---

Example

```text
RSS Source

↓

Generate Content

↓

Publish Facebook

↓

Send Telegram

↓

Archive
```

---

# Event System

Events

post.created

post.published

post.failed

job.started

job.finished

provider.timeout

telegram.sent

facebook.error

---

Event Bus

Internal only.

No Redis.

In-memory queue.

---

# Plugin Installation

Marketplace

Install

Enable

Disable

Remove

Upgrade

Rollback

---

# Plugin Health

Status

healthy

warning

error

disabled

---

Metrics

execution_count

avg_duration

error_count

last_run

---

# Plugin Configuration

Each plugin owns config.

Example

facebook.yaml

```yaml
enabled: true

retry_count: 3

timeout: 60
```

---

# Versioning

Semantic version

Example

1.0.0

1.1.0

2.0.0

---

# Compatibility

Plugins declare

minimum_core_version

maximum_core_version

---

# Plugin Sandbox

Plugins cannot

access database directly

modify core services

override authentication

overwrite core settings

---

Only communicate via:

Service layer

Events

Plugin API

---

# Future Marketplace

Categories

AI

Social

CMS

Messaging

Media

Analytics

Utilities

---

# Plugin API

Expose

register_plugin()

enable_plugin()

disable_plugin()

health_check()

list_plugins()

---

# Sequence Diagram

```text
Core

↓

Plugin Manager

↓

Load Plugin

↓

Initialize

↓

Register Events

↓

Ready
```

---

# Absolute Rules

Plugins must be independent.

No plugin may bypass service layer.

No duplicated code.

No plugin may modify database schema directly.

Plugins communicate only through interfaces and events.

Everything must be production-ready.
