# AI Video Generation Engine (SDD)

> Feature Module Specification

---

# Goal

Implement a reusable AI Video Generation Engine that can generate short talking-avatar videos from an existing character image and a news/article script.

This module is an extension of the existing Facebook automation platform.

The platform already supports:

* Facebook Page Management
* Publishing
* Comment Reply
* Messenger Reply
* Scheduler

This feature only provides AI video generation.

Publishing is handled by the existing Publish Service.

---

# Functional Requirements

Input

* Page ID
* Character Image
* News Script
* Voice Configuration

Output

* MP4 video
* Subtitle
* Thumbnail
* Metadata

---

# High Level Architecture

```text
API

↓

Video Job Service

↓

Queue

↓

GPU Resource Manager

↓

GPU Provider

↓

Video Worker

↓

Storage

↓

Publish Service
```

---

# Components

## Video Job Service

Responsibilities

* Receive requests
* Validate input
* Create Video Job
* Push Queue

No AI logic.

---

## Queue

Recommended

Redis + BullMQ

or existing queue system.

Queue Name

video-generation

Job Payload

```json
{
  "pageId": "...",
  "script": "...",
  "voiceId": "...",
  "characterImage": "...",
  "language": "vi",
  "publishAfterGenerate": true
}
```

---

## GPU Resource Manager

Responsibilities

* Request GPU instance
* Select provider
* Start instance
* Monitor status
* Destroy idle instance

Support

* Vast.ai
* RunPod

Interface

```ts
start()

stop()

getStatus()

executeJob()
```

---

# GPU Provider Interface

Every provider must implement

```typescript
interface GPUProvider {

search()

create()

destroy()

status()

uploadFiles()

downloadFiles()

execute()

}
```

Future providers

* Vast.ai
* RunPod
* Local GPU

---

# Vast Provider

Responsibilities

Search

↓

Create Instance

↓

Wait Ready

↓

Upload Assets

↓

Execute Worker

↓

Download Result

↓

Destroy Instance

Auto destroy

enabled by default.

---

# Worker Container

Each GPU instance runs

Video Worker

Responsibilities

Receive Job

↓

Download Assets

↓

Generate Audio

↓

Talking Avatar

↓

Subtitle

↓

Merge Video

↓

Upload Result

↓

Notify API

Worker must be stateless.

---

# Video Pipeline

Step 1

Generate TTS

Recommended interface

```typescript
generateSpeech()

↓

wav
```

Provider configurable.

---

Step 2

Talking Avatar

Input

* Image
* Audio

Output

Talking Video

Recommended providers

* LivePortrait
* EchoMimic

Interface

```typescript
generateTalkingAvatar()
```

---

Step 3

Subtitle

Generate SRT

No AI required.

---

Step 4

Merge

FFmpeg

Responsibilities

Merge

* avatar
* subtitle
* music
* intro
* outro

Output

MP4

---

# Storage

Store

Input

Character

Audio

Subtitle

Output

Video

Thumbnail

Use existing storage service.

---

# Database

Table

video_jobs

Fields

* id
* page_id
* status
* provider
* gpu_instance
* worker
* script
* audio_url
* subtitle_url
* output_url
* duration
* cost
* started_at
* completed_at
* error

---

Table

gpu_instances

Fields

* id
* provider
* external_id
* status
* price
* gpu_type
* started_at
* stopped_at

---

# Job State

```text
PENDING

↓

WAITING_GPU

↓

STARTING_GPU

↓

UPLOADING

↓

PROCESSING

↓

DOWNLOADING

↓

COMPLETED

↓

PUBLISHED
```

Failure

↓

FAILED

Retry

↓

WAITING_GPU

---

# Retry Strategy

GPU creation failed

Retry 3

Worker timeout

Retry 2

Provider unavailable

Fallback provider

Video generation failed

Retry once

No infinite retry.

---

# Auto Scaling

Configuration

```yaml
gpu:

max_instances: 3

idle_timeout: 300

provider_priority:

- vast

- runpod
```

When Queue increases

Auto create GPU

When Queue empty

Destroy idle GPU

---

# Cost Optimization

Never keep GPU running without jobs.

Batch processing enabled.

If multiple jobs exist

Reuse current GPU.

Destroy after idle timeout.

---

# Configuration

Per Page

```yaml
video:

enabled: true

character_image:

voice:

language:

music:

intro:

outro:

subtitle:

avatar_provider:

tts_provider:

gpu_provider:

publish_after_generate:
```

Everything configurable.

No hardcode.

---

# API

POST

/video/jobs

Create Job

GET

/video/jobs/{id}

Status

POST

/video/jobs/{id}/cancel

Cancel

GET

/video/jobs

History

---

# Logging

Every stage

must generate structured logs.

Include

Job ID

GPU

Duration

Provider

Cost

Retry Count

---

# Metrics

Track

Generation Time

GPU Time

Queue Time

Provider Success Rate

Average Cost

Average Video Length

GPU Utilization

Failure Rate

---

# Error Handling

Must distinguish

Validation Error

GPU Error

Worker Error

Network Error

Provider Error

Storage Error

Never expose provider errors to UI.

---

# Security

Never expose provider API keys.

Workers download signed URLs only.

Temporary files removed after processing.

---

# Coding Rules

* SOLID
* Dependency Injection
* Provider Pattern
* Repository Pattern
* Queue First
* No business logic inside controllers
* Stateless workers
* Configuration Driven

---

# Acceptance Criteria

The feature is completed when:

✓ User submits a script.

✓ Job enters queue.

✓ GPU instance starts automatically.

✓ Worker generates audio.

✓ Worker generates talking avatar.

✓ Subtitle generated.

✓ Video merged.

✓ Video uploaded.

✓ GPU destroyed automatically after idle timeout.

✓ Existing Publish Service can publish generated video without modification.

---

# Future Extensions

The architecture must support without breaking changes:

* Multiple characters
* Multiple avatars
* Multiple languages
* Emotion control
* Gesture generation
* Background replacement
* AI camera movement
* Multi-scene videos
* Lip sync provider replacement
* Additional GPU providers
* Multiple social platforms
* Batch rendering
* Priority queues
* Cost-based provider routing
