"""Celery application configuration."""

from celery import Celery

from app.config import REDIS_URL

celery_app = Celery(
    "sentra",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.document_tasks",
        "app.tasks.extraction_tasks",
        "app.tasks.mapping_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
