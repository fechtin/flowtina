"""Gunicorn configuration tuned for a 1 CPU / 1GB VPS (single worker)."""

from __future__ import annotations

import multiprocessing

bind = "127.0.0.1:8000"
workers = 1  # single process to keep memory < 300MB
worker_class = "uvicorn.workers.UvicornWorker"
threads = 4
timeout = 120
graceful_timeout = 30
keepalive = 5
max_requests = 1000
max_requests_jitter = 100
preload_app = False

# Never start the in-process scheduler inside the web worker; the dedicated
# flowtina-scheduler service owns it.
raw_env = ["SCHEDULER_ENABLED=false"]

_ = multiprocessing  # imported for documentation of intent; workers stay at 1
