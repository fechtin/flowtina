# API.md

# Flowtina REST API Specification

Version: 1.0

Base URL

```text
/api/v1
```

Authentication

JWT Bearer

Response format

```json
{
  "success": true,
  "message": "",
  "data": {}
}
```

Error format

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": ""
  }
}
```

---

# AUTH

## POST /auth/register

Request

```json
{
  "email":"user@email.com",
  "password":"******",
  "name":"John"
}
```

Response

```json
{
 "access_token":"",
 "refresh_token":""
}
```

---

## POST /auth/login

Request

```json
{
 "email":"",
 "password":""
}
```

Response

```json
{
 "access_token":"",
 "refresh_token":""
}
```

---

## POST /auth/refresh

---

## POST /auth/logout

---

## POST /auth/change-password

---

## GET /auth/profile

---

# PROJECTS

## GET /projects

List projects

---

## POST /projects

```json
{
 "name":"",
 "description":""
}
```

---

## GET /projects/{id}

---

## PUT /projects/{id}

---

## DELETE /projects/{id}

Soft delete only.

---

# AI PROVIDERS

## GET /providers

---

## POST /providers

```json
{
 "provider":"openai",
 "base_url":"",
 "api_key":"",
 "model":"gpt-4.1",
 "temperature":0.7,
 "top_p":1
}
```

---

## PUT /providers/{id}

---

## DELETE /providers/{id}

---

## POST /providers/test

Return

```json
{
 "success":true,
 "latency_ms":250
}
```

---

# SYSTEM PROMPTS

## GET /prompts

---

## POST /prompts

```json
{
 "name":"",
 "content":"",
 "version":1
}
```

---

## PUT /prompts/{id}

---

## DELETE /prompts/{id}

---

# TOPICS

## GET /topics

---

## POST /topics

```json
{
 "topic":"AI news"
}
```

---

## PUT /topics/{id}

---

## DELETE /topics/{id}

---

# RSS SOURCES

## GET /rss

---

## POST /rss

```json
{
 "url":""
}
```

---

## PUT /rss/{id}

---

## DELETE /rss/{id}

---

# URL SOURCES

GET /sources/url

POST /sources/url

PUT /sources/url/{id}

DELETE /sources/url/{id}

---

# API SOURCES

GET /sources/api

POST /sources/api

PUT /sources/api/{id}

DELETE /sources/api/{id}

---

# JOBS

## GET /jobs

Return

```json
[
 {
   "name":"Daily News",
   "next_run":"..."
 }
]
```

---

## POST /jobs

```json
{
 "name":"",
 "cron_expression":"0 */3 * * *"
}
```

---

## PUT /jobs/{id}

---

## DELETE /jobs/{id}

---

## POST /jobs/{id}/run

Execute immediately.

---

## GET /jobs/history

---

# POSTS

## GET /posts

Filters

status

language

keyword

date range

---

## POST /posts

Manual draft

---

## GET /posts/{id}

---

## PUT /posts/{id}

---

## DELETE /posts/{id}

---

## POST /posts/{id}/publish

---

## POST /posts/{id}/retry

---

## GET /posts/versions

---

# FACEBOOK

## GET /facebook/pages

---

## POST /facebook/pages

Connect page

```json
{
 "page_id":"",
 "access_token":""
}
```

---

## DELETE /facebook/pages/{id}

---

## POST /facebook/publish

```json
{
 "post_id":"",
 "page_id":""
}
```

---

## GET /facebook/history

---

## GET /facebook/insights

---

# TELEGRAM

## POST /telegram/config

```json
{
 "bot_token":"",
 "chat_id":""
}
```

---

## POST /telegram/test

Send test message.

---

## GET /telegram/history

---

# REPORTS

## GET /reports

---

## POST /reports/generate

Body

```json
{
 "type":"daily"
}
```

---

## POST /reports/send

---

# DASHBOARD

## GET /dashboard/stats

Return

```json
{
 "posts_today":0,
 "success_rate":98,
 "failed_posts":1
}
```

---

## GET /dashboard/charts

---

## GET /dashboard/recent-posts

---

# LOGS

## GET /logs

Filters

level

module

date

---

## GET /logs/download

---

# SETTINGS

## GET /settings

---

## PUT /settings

```json
{
 "language":"vi",
 "theme":"dark",
 "timezone":"Asia/Ho_Chi_Minh"
}
```

---

# BACKUP

## POST /backup/create

---

## GET /backup/history

---

## POST /backup/restore

---

# FILES

## POST /upload

image

csv

txt

---

## DELETE /files/{id}

---

# NOTIFICATIONS

## GET /notifications

---

## POST /notifications/read

---

# PLUGINS

## GET /plugins

---

## POST /plugins/install

---

## DELETE /plugins/{id}

---

# HEALTH

## GET /health

Response

```json
{
 "database":"ok",
 "scheduler":"ok",
 "memory_mb":120,
 "cpu_percent":3
}
```

---

# Metrics

GET /metrics

Prometheus compatible.

---

# Rate Limits

Anonymous

30/min

Authenticated

300/min

Admin

1000/min

---

# Status Codes

200 OK

201 Created

400 Validation Error

401 Unauthorized

403 Forbidden

404 Not Found

409 Conflict

429 Too Many Requests

500 Internal Error

---

# OpenAPI Requirement

Claude Code must generate:

Swagger UI

ReDoc

Pydantic schemas

Typed responses

Validation

Error handlers

Global exception middleware

Production-ready API only.
