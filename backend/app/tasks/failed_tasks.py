"""Dead letter queue consumer — captures permanently failed pipeline jobs."""

import logging
import uuid
from datetime import datetime

from app.database import SessionLocal
from app.models.audit import AuditEvent
from app.models.documents import Document
from app.tasks.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.failed_tasks.handle_failed_job",
    queue="failed_jobs",
    max_retries=0,
)
def handle_failed_job(
    job_id: str,
    lot_id: str,
    task_name: str,
    error_message: str,
    traceback_str: str,
    retry_count: int,
):
    """
    DLQ consumer: persist failure details to audit_events and mark all
    documents in the lot as 'failed'.
    Called automatically via on_failure after max retries are exhausted.
    """
    logger.error(
        "[DLQ] job=%s lot=%s task=%s retries=%d error=%s",
        job_id, lot_id, task_name, retry_count, error_message,
    )

    db = SessionLocal()
    try:
        # Write pipeline_failed audit event
        db.add(AuditEvent(
            job_id=uuid.UUID(job_id) if job_id else None,
            event_type="pipeline_failed",
            metadata_={
                "lot_id": lot_id,
                "task": task_name,
                "error": error_message,
                "traceback": traceback_str,
                "retries": retry_count,
            },
        ))

        # Mark every document in the lot as failed
        docs = db.query(Document).filter(Document.lot_id == lot_id).all()
        for doc in docs:
            doc.status = "failed"
            doc.updated_at = datetime.utcnow()

        db.commit()
        logger.info(
            "[DLQ] Marked %d document(s) as failed for lot %s", len(docs), lot_id
        )

    except Exception:
        db.rollback()
        logger.exception("[DLQ] Failed to persist failure record for job %s", job_id)
    finally:
        db.close()
