"""
Gunicorn Configuration for FerrikBot v3.2
Optimized for Render Free Tier (512 MB RAM)
"""

import os

# Server socket
bind = "0.0.0.0:5000"
backlog = 2048

# Worker processes
workers = 1  # Free tier optimal
worker_class = "gevent"  # CRITICAL for async
worker_connections = 1000
threads = 4

# Timeouts
timeout = 120  # 2 minutes
keepalive = 5
graceful_timeout = 30

# Memory management
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"
access_log_format = '%(h)s %(t)s "%(r)s" %(s)s %(b)s'

# Security
limit_request_line = 4094
limit_request_fields = 100

# Process naming
proc_name = "ferrikbot"

# Reload on code changes (dev only)
reload = os.environ.get('FLASK_ENV') == 'development'


# Hooks for logging
def on_starting(server):
    print("=" * 70)
    print("🚀 Gunicorn starting FerrikBot v3.2")
    print("=" * 70)


def when_ready(server):
    print("=" * 70)
    print("✅ Gunicorn ready!")
    print(f"   Workers: {workers}")
    print(f"   Worker class: {worker_class}")
    print(f"   Threads: {threads}")
    print(f"   Timeout: {timeout}s")
    print("=" * 70)


def post_fork(server, worker):
    print(f"✅ Worker spawned (pid: {worker.pid})")


def worker_exit(server, worker):
    print(f"👋 Worker exited (pid: {worker.pid})")
