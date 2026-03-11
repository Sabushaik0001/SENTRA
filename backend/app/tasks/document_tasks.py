"""Celery tasks for document extraction pipeline."""

import logging
import time
import uuid
from typing import Optional

from app.database import SessionLocal
from app.tasks.celery_worker import celery_app
from app.tasks.extraction_tasks import run_extraction
from app.tasks.mapping_tasks import run_mapping_and_order
from app.tasks.pipeline_helpers import emit_audit

logger = logging.getLogger(__name__)


class _PipelineBase(celery_app.Task):
    """Base task class — routes permanently failed jobs to the DLQ after max retries."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        job_id = args[0] if args else kwargs.get("job_id", task_id)
        lot_id = args[1] if len(args) > 1 else kwargs.get("lot_id", "unknown")

        from app.tasks.failed_tasks import handle_failed_job

        handle_failed_job.apply_async(
            kwargs={
                "job_id": str(job_id),
                "lot_id": str(lot_id),
                "task_name": self.name,
                "error_message": str(exc),
                "traceback_str": str(einfo),
                "retry_count": self.max_retries,
            },
            queue="failed_jobs",
        )


@celery_app.task(
    bind=True,
    base=_PipelineBase,
    max_retries=3,
    default_retry_delay=30,
)
def extract_documents_task(
    self,
    job_id: str,
    lot_id: str,
    selection_doc_id: str,
    takeoff_doc_id: str,
):
    """
    Celery task triggered by POST /extraction/{lot_id}/run.
    Runs extraction for both documents with full status transitions + audit events.
    On failure retries up to 3 times (exponential backoff), then routes to DLQ.
    """
    start = time.perf_counter()
    db = SessionLocal()

    try:
        logger.info("[%s] Extraction started for lot %s", job_id, lot_id)

        emit_audit(db, job_id, "extraction_started", {
            "lot_id": lot_id,
            "selection_doc_id": selection_doc_id,
            "takeoff_doc_id": takeoff_doc_id,
        })

        run_extraction(job_id, lot_id, selection_doc_id, takeoff_doc_id)

        duration_ms = int((time.perf_counter() - start) * 1000)
        emit_audit(db, job_id, "extraction_completed", {
            "lot_id": lot_id,
            "duration_ms": duration_ms,
        })

        logger.info(
            "[%s] Extraction completed for lot %s in %dms", job_id, lot_id, duration_ms
        )

    except Exception as exc:
        logger.exception("[%s] Extraction failed for lot %s: %s", job_id, lot_id, exc)
        db.rollback()
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        db.close()
