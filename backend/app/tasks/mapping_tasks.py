"""Mapping and order generation tasks."""

import logging
from typing import Optional

from app.database import SessionLocal
from app.services.mapping_service import run_mapping
from app.services.order_service import generate_order

logger = logging.getLogger(__name__)


def run_mapping_and_order(job_id: str, lot_id: str, builder_id: Optional[str] = None):
    """Run material mapping then generate the purchase order."""
    db = SessionLocal()
    try:
        logger.info("[%s] Running mapping engine for lot %s", job_id, lot_id)
        run_mapping(db, lot_id)

        logger.info("[%s] Generating order for lot %s", job_id, lot_id)
        order = generate_order(db, lot_id, builder_id)
        logger.info("[%s] Order %s generated for lot %s", job_id, order.id, lot_id)

    finally:
        db.close()
