"""Extraction endpoints: trigger extraction and view results."""

import logging
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.documents import Document
from app.models.selections import Selection
from app.models.takeoff import TakeoffData
from app.schemas.selection_schema import SelectionListResponse, SelectionOut
from app.schemas.takeoff_schema import TakeoffDataOut, TakeoffListResponse
from app.tasks.document_tasks import extract_documents_task

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{lot_id}/run", status_code=202)
def run_extraction_for_lot(lot_id: str, db: Session = Depends(get_db)):
    """
    Dispatch Celery extraction task for a lot.
    Documents must already be uploaded and classified.
    Poll GET /documents/{lot_id}/status to track progress.
    """
    docs = db.query(Document).filter(Document.lot_id == lot_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail=f"No documents found for lot {lot_id}")

    sel_doc = next((d for d in docs if d.document_type == "selection_sheet"), None)
    to_doc = next((d for d in docs if d.document_type == "takeoff_sheet"), None)

    if not sel_doc or not to_doc:
        raise HTTPException(
            status_code=400,
            detail="Both selection_sheet and takeoff_sheet documents are required.",
        )

    job_id = str(uuid.uuid4())

    extract_documents_task.delay(
        job_id,
        lot_id,
        str(sel_doc.id),
        str(to_doc.id),
    )

    return {
        "lot_id": lot_id,
        "job_id": job_id,
        "status": "queued",
        "message": "Extraction queued. Poll GET /documents/{lot_id}/status for progress.",
    }


@router.get("/selections/{lot_id}", response_model=SelectionListResponse)
def get_selections(lot_id: str, db: Session = Depends(get_db)):
    """Return all extracted selections for a lot."""
    rows = db.query(Selection).filter(Selection.lot_id == lot_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No selections for lot {lot_id}")
    return SelectionListResponse(lot_id=lot_id, count=len(rows), selections=rows)


@router.get("/takeoff/{lot_id}", response_model=TakeoffListResponse)
def get_takeoff(lot_id: str, db: Session = Depends(get_db)):
    """Return all extracted takeoff rows for a lot."""
    rows = db.query(TakeoffData).filter(TakeoffData.lot_id == lot_id).all()
    if not rows:
        raise HTTPException(status_code=404, detail=f"No takeoff data for lot {lot_id}")
    return TakeoffListResponse(lot_id=lot_id, count=len(rows), rows=rows)
