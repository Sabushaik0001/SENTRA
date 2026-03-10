"""Top-level document processing pipeline task."""

import logging
import time
import uuid
from typing import Optional

from app.database import SessionLocal
from app.models.audit import AuditEvent
from app.tasks.celery_worker import celery_app
from app.tasks.extraction_tasks import run_extraction
from app.tasks.mapping_tasks import run_mapping_and_order
from app.utils.audit_helper import log_audit_event

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=30)
def process_document_pipeline(
    self,
    job_id: str,
    lot_id: str,
    selection_doc_id: str,
    takeoff_doc_id: str,
    builder_id: Optional[str] = None,
):
    """
    Orchestrate the full document processing pipeline:
    1. classify_document (for both docs)
    2. extract_selection_sheet
    3. extract_takeoff_sheet
    4. run_mapping_engine
    5. generate_order
    """
    start = time.perf_counter()
    db = SessionLocal()

    try:
        logger.info("[%s] Pipeline started for lot %s", job_id, lot_id)

        # Step 1+2: Extract both documents
        run_extraction(job_id, lot_id, selection_doc_id, takeoff_doc_id)

        # Step 3+4: Map and generate order
        run_mapping_and_order(job_id, lot_id, builder_id)

        duration_ms = int((time.perf_counter() - start) * 1000)

        # Audit
        event = AuditEvent(
            job_id=uuid.UUID(job_id),
            event_type="pipeline_completed",
            duration_ms=duration_ms,
            metadata_={"lot_id": lot_id, "builder_id": builder_id},
        )
        db.add(event)
        db.commit()

        logger.info("[%s] Pipeline completed for lot %s in %dms", job_id, lot_id, duration_ms)

    except Exception as exc:
        logger.exception("[%s] Pipeline failed for lot %s: %s", job_id, lot_id, exc)

        duration_ms = int((time.perf_counter() - start) * 1000)

        log_audit_event(
            db=db,
            job_id=uuid.UUID(job_id),
            event_type="pipeline_failed",
            duration_ms=duration_ms,
            metadata={
                "lot_id": lot_id,
                "builder_id": builder_id,
                "error": str(exc),
                "retry_count": self.request.retries,
                "max_retries": self.max_retries,
            }
        )
        
        db.rollback()
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))
    finally:
        db.close()
