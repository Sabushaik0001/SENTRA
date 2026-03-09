"""Extraction tasks: classify and extract documents."""

import logging
import uuid

from app.database import SessionLocal
from app.models.documents import Document
from app.services.classification_service import classify_document
from app.services.extraction_service import (
    extract_selection_sheet_from_bytes,
    extract_takeoff_sheet_from_bytes,
)
from app.services.s3_service import download_file_from_s3

logger = logging.getLogger(__name__)


def _s3_key_from_path(s3_path: str) -> str:
    """Extract S3 key from full s3:// path."""
    return "/".join(s3_path.split("/")[3:])


def _classify_from_filename(db, doc):
    """Classify document based on filename and document_type (already known at upload)."""
    from app.models.documents import DocumentClassification
    classification = DocumentClassification(
        document_id=doc.id,
        document_type=doc.document_type,
        builder_id=doc.builder_id,
        format="standard",
        confidence_score=1.0,
    )
    db.add(classification)
    doc.status = "classified"
    db.commit()
    logger.info("Classified %s as %s (from upload metadata)", doc.id, doc.document_type)


def run_extraction(job_id: str, lot_id: str, selection_doc_id: str, takeoff_doc_id: str):
    """Classify and extract both documents."""
    db = SessionLocal()
    try:
        # Process selection sheet
        sel_doc = db.query(Document).filter(Document.id == uuid.UUID(selection_doc_id)).first()
        if sel_doc and sel_doc.s3_path:
            logger.info("[%s] Processing selection sheet %s", job_id, selection_doc_id)
            sel_bytes = download_file_from_s3(_s3_key_from_path(sel_doc.s3_path))

            # Classify using upload metadata (document_type is already known)
            _classify_from_filename(db, sel_doc)

            # Extract using Vision (sends raw PDF bytes to Claude)
            extract_selection_sheet_from_bytes(
                db, sel_doc.id, sel_bytes, sel_doc.file_name or "selection.pdf", lot_id
            )

        # Process takeoff sheet
        to_doc = db.query(Document).filter(Document.id == uuid.UUID(takeoff_doc_id)).first()
        if to_doc and to_doc.s3_path:
            logger.info("[%s] Processing takeoff sheet %s", job_id, takeoff_doc_id)
            to_bytes = download_file_from_s3(_s3_key_from_path(to_doc.s3_path))

            _classify_from_filename(db, to_doc)

            extract_takeoff_sheet_from_bytes(
                db, to_doc.id, to_bytes, to_doc.file_name or "takeoff.pdf", lot_id
            )

    finally:
        db.close()
