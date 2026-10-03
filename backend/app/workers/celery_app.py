"""
Celery application configuration — Phase 7.

Configures Celery with Redis as the broker and result backend.
All settings are sourced from environment variables.

Usage:
    celery -A app.workers.celery_app worker --loglevel=info --pool=solo
"""

import os
from dotenv import load_dotenv
from celery import Celery

load_dotenv()

# Celery configuration from environment variables
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

celery_app = Celery(
    "devagent",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task settings
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Result expiration (24 hours)
    result_expires=86400,

    # Windows compatibility: use solo pool by default
    worker_pool="solo",
)

# Auto-discover tasks from the workers package
celery_app.autodiscover_tasks(["app.workers"])
