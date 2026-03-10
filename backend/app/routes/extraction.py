"""Extraction endpoints: trigger extraction and view results."""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.documents import Document
from app.models.selections import Selection
from app.models.takeoff import TakeoffData
from app.schemas.selection_schema import SelectionListResponse, SelectionOut
from app.schemas.takeoff_schema import TakeoffDataOut, TakeoffListResponse
from app.services.extraction_service import (
    extract_selection_sheet_from_bytes,
    extract_takeoff_sheet_from_bytes,
)
from app.services.s3_service import download_file_from_s3

logger = logging.getLogger(__name__)
router = APIRouter()


def _s3_key_from_path(s3_path: str) -> str:
    return "/".join(s3_path.split("/")[3:])


@router.post("/{lot_id}/run")
def run_extraction_for_lot(lot_id: str, db: Session = Depends(get_db)):
    """
    Trigger extraction for all documents in a lot.
    Downloads files from S3, sends to Claude Vision, stores results in DB.
    """
    docs = db.query(Document).filter(Document.lot_id == lot_id).all()
    if not docs:
        raise HTTPException(status_code=404, detail=f"No documents found for lot {lot_id}")

    results = {"lot_id": lot_id, "selection_sheet": None, "takeoff_sheet": None}

    for doc in docs:
        if not doc.s3_path:
            logger.warning("Document %s has no s3_path — skipping", doc.id)
            continue

        try:
            file_bytes = download_file_from_s3(_s3_key_from_path(doc.s3_path))
        except Exception as exc:
            logger.error("Failed to download %s from S3: %s", doc.s3_path, exc)
            continue

        file_name = doc.file_name or "document.pdf"

        if doc.document_type == "selection_sheet":
            selections = extract_selection_sheet_from_bytes(
                db, doc.id, file_bytes, file_name, lot_id,
                builder_id=doc.builder_id
            )
            results["selection_sheet"] = {
                "document_id": str(doc.id),
                "extracted_count": len(selections),
                "status": "extracted",
            }

        elif doc.document_type == "takeoff_sheet":
            takeoff_rows = extract_takeoff_sheet_from_bytes(
                db, doc.id, file_bytes, file_name, lot_id,
                builder_id=doc.builder_id
            )
            results["takeoff_sheet"] = {
                "document_id": str(doc.id),
                "extracted_count": len(takeoff_rows),
                "status": "extracted",
            }

    return results


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
