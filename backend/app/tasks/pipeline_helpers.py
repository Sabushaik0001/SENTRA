"""Shared helpers for pipeline status transitions and audit logging."""

import uuid
from datetime import datetime

from app.models.audit import AuditEvent
from app.models.documents import Document


def transition(db, doc_id, new_status: str, job_id: str, extra_meta: dict = None) -> str:
    """
    Update a document's status and write an audit_events row in a single commit.
    Returns the previous status.
    """
    if not isinstance(doc_id, uuid.UUID):
        doc_id = uuid.UUID(str(doc_id))

    doc = db.query(Document).filter(Document.id == doc_id).first()
    prev_status = doc.status if doc else "unknown"

    if doc:
        doc.status = new_status
        doc.updated_at = datetime.utcnow()

    meta = {
        "document_id": str(doc_id),
        "from": prev_status,
        "to": new_status,
    }
    if extra_meta:
        meta.update(extra_meta)

    db.add(AuditEvent(
        job_id=uuid.UUID(job_id) if job_id else None,
        event_type="status_changed",
        metadata_=meta,
    ))
    db.commit()
    return prev_status


def emit_audit(db, job_id: str, event_type: str, metadata: dict) -> None:
    """Write a standalone audit event and commit."""
    db.add(AuditEvent(
        job_id=uuid.UUID(job_id) if job_id else None,
        event_type=event_type,
        metadata_=metadata,
    ))
    db.commit()
