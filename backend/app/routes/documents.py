"""Document upload and status endpoints."""

import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.documents import Document
from app.schemas.document_schema import DocumentStatusResponse, DocumentUploadResponse
from app.services.s3_service import upload_file_to_s3
from app.tasks.document_tasks import process_document_pipeline
from app.utils.s3_paths import build_s3_key
from app.utils.audit_helper import log_audit_event

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/upload", response_model=DocumentUploadResponse, status_code=202)
async def upload_documents(
    selection_sheet: UploadFile = File(..., description="Selection sheet PDF"),
    takeoff_sheet: UploadFile = File(..., description="Takeoff sheet (PDF or Excel)"),
    builder_id: str = Form(None, description="Optional builder identifier"),
    db: Session = Depends(get_db),
):
    """Upload selection sheet + takeoff sheet. Triggers async processing pipeline."""
    lot_id = f"LOT-{uuid.uuid4().hex[:8].upper()}"
    job_id = uuid.uuid4()

    # Upload selection sheet to S3
    sel_bytes = await selection_sheet.read()
    sel_s3_key = build_s3_key(lot_id, "selection_sheet.pdf")
    sel_s3_path = upload_file_to_s3(sel_bytes, sel_s3_key, content_type="application/pdf")

    sel_doc = Document(
        lot_id=lot_id,
        builder_id=builder_id,
        document_type="selection_sheet",
        file_name=selection_sheet.filename,
        s3_path=sel_s3_path,
        status="uploaded",
    )
    db.add(sel_doc)

    # Upload takeoff sheet to S3
    to_bytes = await takeoff_sheet.read()
    to_ext = (takeoff_sheet.filename or "file.xlsx").rsplit(".", 1)[-1]
    to_s3_key = build_s3_key(lot_id, f"takeoff_sheet.{to_ext}")
    to_content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if to_ext in ("xlsx", "xls") else "application/pdf"
    to_s3_path = upload_file_to_s3(to_bytes, to_s3_key, content_type=to_content_type)

    to_doc = Document(
        lot_id=lot_id,
        builder_id=builder_id,
        document_type="takeoff_sheet",
        file_name=takeoff_sheet.filename,
        s3_path=to_s3_path,
        status="uploaded",
    )
    db.add(to_doc)
    db.commit()
    db.refresh(sel_doc)
    db.refresh(to_doc)

    log_audit_event(
        db=db,
        job_id=job_id,
        event_type="documents_uploaded",
        user_id=None,  # Need to add user authentication
        metadata={
            "lot_id": lot_id,
            "builder_id": builder_id,
            "selection_sheet_id": str(sel_doc.id),
            "takeoff_sheet_id": str(to_doc.id),
            "selection_sheet_filename": selection_sheet.filename,
            "takeoff_sheet_filename": takeoff_sheet.filename,
        }
    )

    # Dispatch Celery pipeline
    process_document_pipeline.delay(
        str(job_id), lot_id, str(sel_doc.id), str(to_doc.id), builder_id
    )

    return DocumentUploadResponse(
        job_id=job_id,
        lot_id=lot_id,
        status="queued",
        selection_sheet_s3=sel_s3_path,
        takeoff_sheet_s3=to_s3_path,
        message="Processing started. Poll GET /documents/{lot_id}/status for progress.",
    )


@router.get("/{lot_id}/status", response_model=List[DocumentStatusResponse])
def get_document_status(lot_id: str, db: Session = Depends(get_db)):
    """Get processing status for all documents in a lot."""
    docs = db.query(Document).filter(Document.lot_id == lot_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail=f"No documents found for lot {lot_id}")
    return docs
