"""Celery application configuration."""

from kombu import Queue

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
        "app.tasks.failed_tasks",
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
    # Requeue the message if the worker dies mid-task (prevents silent drops)
    task_reject_on_worker_lost=True,
    # Queue definitions
    task_queues=[
        Queue("default"),
        Queue("failed_jobs"),
    ],
    task_default_queue="default",
    # Route DLQ handler to the failed_jobs queue
    task_routes={
        "app.tasks.failed_tasks.handle_failed_job": {"queue": "failed_jobs"},
    },
)
