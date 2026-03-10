"""Helper functions for audit event logging."""

import logging
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


def log_audit_event(
    db: Session,
    job_id: uuid.UUID,
    event_type: str,
    user_id: Optional[str] = None,
    duration_ms: Optional[int] = None,
    metadata: Optional[dict] = None,
):
    """
    Create an audit event record.
    
    Args:
        db: Database session
        job_id: Job/pipeline UUID
        event_type: Event type (e.g., 'document_uploaded', 'extraction_completed')
        user_id: Optional user identifier
        duration_ms: Optional duration in milliseconds
        metadata: Optional metadata dict (lot_id, builder_id, document_id, etc.)
    """
    try:
        event = AuditEvent(
            job_id=job_id,
            event_type=event_type,
            user_id=user_id,
            duration_ms=duration_ms,
            metadata_=metadata or {},
        )
        db.add(event)
        db.commit()
        logger.info("Audit event logged: %s (job_id=%s)", event_type, job_id)
    except Exception as exc:
        logger.error("Failed to log audit event %s: %s", event_type, exc)
        db.rollback()