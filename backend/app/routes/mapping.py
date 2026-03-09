"""Mapping and SAP material search endpoints."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.mapping_service import run_mapping
from app.services.sap_matching_service import search_sap_material

logger = logging.getLogger(__name__)
router = APIRouter()


class SapSearchRequest(BaseModel):
    material_description: str
    top_k: int = 5


class SapSearchResult(BaseModel):
    sap_code: str
    description: str
    category: str
    uom: str
    score: float
    status: str


@router.post("/sap-search", response_model=list[SapSearchResult])
def sap_search(req: SapSearchRequest):
    """Vector search for SAP materials by description."""
    return search_sap_material(req.material_description, req.top_k)


@router.post("/{lot_id}/run")
def run_material_mapping(lot_id: str, db: Session = Depends(get_db)):
    """Run the deterministic mapping engine for a lot."""
    mapped = run_mapping(db, lot_id)
    return {"lot_id": lot_id, "mapped_count": len(mapped), "status": "completed"}
