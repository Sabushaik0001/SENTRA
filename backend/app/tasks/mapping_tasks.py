"""Mapping and order generation tasks."""

import logging
from typing import Optional

from app.database import SessionLocal
from app.models.documents import Document
from app.services.mapping_service import run_mapping
from app.services.order_service import generate_order
from app.tasks.pipeline_helpers import emit_audit, transition

logger = logging.getLogger(__name__)


def _transition_lot(db, lot_id: str, new_status: str, job_id: str, extra_meta: dict = None):
    """Transition all documents in a lot to a new status."""
    docs = db.query(Document).filter(Document.lot_id == lot_id).all()
    for doc in docs:
        transition(db, doc.id, new_status, job_id, {"lot_id": lot_id, **(extra_meta or {})})


def run_mapping_and_order(job_id: str, lot_id: str, builder_id: Optional[str] = None):
    """Run material mapping then generate the purchase order, with status transitions."""
    db = SessionLocal()
    try:
        # --- Mapping ---
        logger.info("[%s] Running mapping engine for lot %s", job_id, lot_id)
        _transition_lot(db, lot_id, "mapping", job_id)
        run_mapping(db, lot_id)
        _transition_lot(db, lot_id, "mapped", job_id)

        # --- Order generation ---
        logger.info("[%s] Generating order for lot %s", job_id, lot_id)
        _transition_lot(db, lot_id, "generating_order", job_id)
        order = generate_order(db, lot_id, builder_id)
        _transition_lot(db, lot_id, "complete", job_id, {"order_id": str(order.id)})

        logger.info("[%s] Order %s generated for lot %s", job_id, order.id, lot_id)

    finally:
        db.close()
