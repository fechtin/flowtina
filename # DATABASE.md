# DATABASE.md

# AI Content Automation Platform

Database Version: 1.0

Default Database:

SQLite

Optional:

PostgreSQL

ORM:

SQLAlchemy + Alembic

---

# Database Design Principles

* UUID primary key
* Soft delete
* created_at
* updated_at
* deleted_at
* indexed foreign keys
* snake_case naming
* no cascade delete
* audit log enabled

---

# ERD

```text
User
 ├── Projects
 │     ├── AI Providers
 │     ├── Prompt Templates
 │     ├── Topics
 │     ├── Sources
 │     ├── Scheduler Jobs
 │     ├── Posts
 │     ├── Facebook Pages
 │     ├── Telegram Configs
 │     ├── Reports
 │     └── Logs
```

---

# Base Columns

All tables contain:

```sql
id UUID PRIMARY KEY

created_at DATETIME

updated_at DATETIME

deleted_at DATETIME NULL
```

---

# users

```sql
id
email UNIQUE
password_hash
name
avatar
language
timezone
is_admin
active
last_login_at
created_at
updated_at
deleted_at
```

Indexes

```sql
email
active
```

---

# refresh_tokens

```sql
id
user_id FK users
token
expires_at
revoked
created_at
```

Indexes

```sql
user_id
token
```

---

# projects

```sql
id
user_id FK users
name
description
active
created_at
updated_at
deleted_at
```

Indexes

```sql
user_id
active
```

---

# ai_providers

```sql
id
project_id
provider
base_url
api_key_encrypted
model
temperature
top_p
max_tokens
timeout_seconds
enabled
created_at
updated_at
```

Provider values

```text
openai
gemini
claude
openrouter
deepseek
ollama
lmstudio
vllm
custom
```

---

# system_prompts

```sql
id
project_id
name
content
version
active
created_at
```

---

# prompt_templates

```sql
id
project_id
name
type
template
language
active
created_at
```

Types

```text
news
seo
marketing
educational
question
quote
short_post
long_post
```

---

# topics

```sql
id
project_id
topic
priority
active
```

---

# rss_sources

```sql
id
project_id
url
enabled
last_sync_at
```

---

# url_sources

```sql
id
project_id
url
enabled
```

---

# keyword_sources

```sql
id
project_id
keyword
priority
```

---

# api_sources

```sql
id
project_id
name
endpoint
headers_json
enabled
```

---

# source_cache

```sql
id
project_id
hash
title
content
source_type
published_at
```

Purpose:

deduplicate content

---

# scheduler_jobs

```sql
id
project_id
name
cron_expression
timezone
enabled
last_run_at
next_run_at
```

---

# scheduler_history

```sql
id
job_id
started_at
finished_at
status
duration_ms
message
```

---

# posts

```sql
id
project_id
title
content
hashtags
language
status
publish_at
created_by_ai
```

Status

```text
draft
scheduled
published
failed
archived
```

---

# post_versions

```sql
id
post_id
version
content
created_at
```

Purpose

history and rollback

---

# generated_images

```sql
id
post_id
prompt
image_url
provider
```

---

# facebook_pages

```sql
id
project_id
page_name
page_id
access_token_encrypted
enabled
```

---

# facebook_posts

```sql
id
post_id
page_id
facebook_post_id
status
published_at
response_json
```

---

# facebook_publish_logs

```sql
id
facebook_post_id
status
message
created_at
```

---

# telegram_configs

```sql
id
project_id
bot_token_encrypted
chat_id
enabled
```

---

# telegram_logs

```sql
id
project_id
message
status
created_at
```

---

# reports

```sql
id
project_id
type
period_start
period_end
content
sent
created_at
```

Types

```text
daily
weekly
monthly
```

---

# ai_usage_logs

```sql
id
project_id
provider
model
prompt_tokens
completion_tokens
total_tokens
cost
duration_ms
created_at
```

---

# api_keys

```sql
id
project_id
name
key_hash
active
created_at
```

---

# user_settings

```sql
id
user_id
theme
language
timezone
default_model
daily_budget
retry_count
```

---

# notifications

```sql
id
user_id
title
content
read
created_at
```

---

# audit_logs

```sql
id
user_id
action
resource
resource_id
old_data_json
new_data_json
created_at
```

---

# system_logs

```sql
id
level
module
message
created_at
```

---

# backups

```sql
id
filename
size
status
created_at
```

---

# plugin_registry

```sql
id
name
type
enabled
version
```

Future types

```text
facebook
telegram
instagram
twitter
linkedin
wordpress
youtube
tiktok
discord
email
```

---

# file_storage

```sql
id
path
filename
size
mime_type
```

---

# tags

```sql
id
name
```

---

# post_tags

```sql
post_id
tag_id
```

Composite Index

```sql
post_id + tag_id
```

---

# execution_queue

```sql
id
task_type
payload_json
status
retry_count
next_retry_at
```

Status

```text
pending
running
completed
failed
```

---

# Index Strategy

Frequently indexed

```sql
email

user_id

project_id

post_id

job_id

created_at

status
```

---

# Encryption

AES encryption for:

api_key

facebook token

telegram token

refresh token

---

# Soft Delete Policy

Never physical delete:

users

projects

posts

prompts

jobs

Instead

deleted_at IS NOT NULL

---

# Migration Strategy

Alembic

Naming

```python
20260701_create_users

20260702_create_projects

20260703_create_ai_providers
```

One migration per table.

---

# Estimated Table Count

Core Tables

38+

Future plugins

20+

Total

60+ tables

Production ready.
