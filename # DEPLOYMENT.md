# DEPLOYMENT.md

# Flowtina Deployment Architecture

Version: 1.0

Target Environment:

Ubuntu 22.04 LTS

Minimum Server:

1 CPU

1GB RAM

20GB SSD

No Docker

No Kubernetes

No Redis

No Celery

Single VPS deployment

---

# Design Goals

Low memory footprint

Easy installation

Simple maintenance

24/7 operation

Auto recovery

Production-ready

---

# Directory Structure

```text
/opt/flowtina/

backend/
frontend/
logs/
uploads/
database/
backups/
scripts/
config/
ssl/
```

---

# User

Never run as root.

Create user:

```bash
flowtina
```

Directories owner:

```bash
chown -R flowtina:flowtina /opt/flowtina
```

---

# Python Environment

Python 3.12

Virtual environment

```bash
/opt/flowtina/venv
```

Install

```bash
python3.12 -m venv venv
```

---

# Frontend Build

Vue3

Output:

```text
dist/
```

Served by:

Nginx

---

# Backend

Start

```bash
uvicorn app.main:app
```

Production

Use

gunicorn + uvicorn workers

Workers

1

Threads

4

Command

```bash
gunicorn app.main:app \
-k uvicorn.workers.UvicornWorker \
-w 1 \
--threads 4
```

---

# Reverse Proxy

Nginx

Ports

80

443

Backend

127.0.0.1:8000

Frontend

Static files

---

# Example Nginx

```nginx
server {

server_name flowtina.com;

location /api {

proxy_pass http://127.0.0.1:8000;

}

location / {

root /opt/flowtina/frontend/dist;

try_files $uri $uri/ /index.html;

}

}
```

---

# SSL

Let's Encrypt

Use

certbot

Auto renew

cron daily

---

# systemd Services

## Backend

flowtina-api.service

```ini
[Unit]
Description=Flowtina API

[Service]
User=flowtina

WorkingDirectory=/opt/flowtina/backend

ExecStart=/opt/flowtina/venv/bin/gunicorn app.main:app

Restart=always

RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Scheduler

flowtina-scheduler.service

Responsible

APScheduler

Background jobs

Reports

Cleanup

---

# Frontend

No service required.

Served by nginx.

---

# Startup Sequence

```text
Ubuntu

↓

systemd

↓

flowtina-api

↓

scheduler

↓

nginx

↓

Ready
```

---

# SQLite Configuration

PRAGMA

```sql
journal_mode=WAL

synchronous=NORMAL

cache_size=10000

temp_store=MEMORY
```

Benefits

Lower disk I/O

Faster reads

---

# Database Location

```text
/opt/flowtina/database/app.db
```

Backup

```text
/opt/flowtina/backups/
```

---

# Logging

Directory

```text
logs/
```

Files

system.log

api.log

scheduler.log

facebook.log

telegram.log

ai.log

---

Retention

30 days

Compression

zip

Rotation

daily

---

# Uploads

Directory

```text
uploads/

images/

csv/

txt/
```

Max file size

20MB

---

# Backup Strategy

Daily

SQLite dump

Compressed

zip

Filename

```text
backup_YYYYMMDD.zip
```

Keep

30 backups

---

# Restore

Manual

Admin UI

CLI

---

# Cron Jobs

Daily backup

Log cleanup

Health check

SSL renewal

Old file cleanup

---

# Memory Optimization

Target

<300MB

Rules

Single gunicorn worker

Lazy imports

No Redis

No Celery

SQLite

Connection pool size

5

LRU cache only

---

# CPU Target

Idle

<5%

Normal

10%

Peak

<50%

---

# Monitoring

Health endpoint

```text
/api/v1/health
```

Metrics

CPU

RAM

Disk

Scheduler

Database

AI provider

Telegram

Facebook

---

# Prometheus

Optional

Endpoint

```text
/metrics
```

---

# Alerts

Telegram notifications

Database failure

Scheduler stopped

Low disk space

Provider timeout

Facebook publish failure

---

# Firewall

ufw

Allow

22

80

443

Block everything else

---

# Fail2ban

Enable

SSH protection

---

# Environment Variables

.env

```env
APP_NAME=Flowtina

DATABASE_URL=sqlite:///database/app.db

JWT_SECRET=

ENCRYPTION_KEY=

LOG_LEVEL=INFO
```

Never commit .env

---

# install.sh

Responsibilities

Create directories

Create virtualenv

Install dependencies

Run migrations

Build frontend

Create systemd services

Enable services

Configure permissions

---

# update.sh

Backup database

Pull source

Install requirements

Run migrations

Restart services

---

# rollback.sh

Restore backup

Restart services

---

# Upgrade Strategy

Zero downtime not required.

Simple restart acceptable.

---

# HTTPS

Mandatory

Redirect HTTP → HTTPS

HSTS enabled

---

# Security

bcrypt

AES encryption

JWT

Rate limiting

No root execution

Fail2ban

UFW

---

# Recovery

Restart policy

always

Restart delay

5 seconds

---

# Disaster Recovery

Restore database

Restore uploads

Restart services

Estimated time

<10 minutes

---

# Performance Targets

Startup

<3 seconds

Memory

<300MB

API latency

<100ms

Dashboard

<2 seconds

---

# Production Checklist

HTTPS enabled

Firewall enabled

Fail2ban enabled

Backup configured

Scheduler enabled

Log rotation enabled

systemd auto restart enabled

SQLite WAL enabled

Telegram alerts configured

Environment secrets configured

---

# Absolute Rules

No Docker

No Redis

No Celery

No Kubernetes

Single VPS deployment

Everything must run reliably on 1 CPU + 1GB RAM

Production-ready only
