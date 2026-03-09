"""Purchase order endpoints."""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.orders import OrderDraft, OrderLine
from app.services.order_service import generate_order

logger = logging.getLogger(__name__)
router = APIRouter()


class OrderLineOut(BaseModel):
    sap_material_code: Optional[str] = None
    description: Optional[str] = None
    quantity: Optional[float] = None
    uom: Optional[str] = None
    category: Optional[str] = None

    model_config = {"from_attributes": True}


class OrderDraftOut(BaseModel):
    id: UUID
    lot_id: Optional[str] = None
    builder_id: Optional[str] = None
    order_status: Optional[str] = None
    total_amount: Optional[float] = None
    lines: List[OrderLineOut]

    model_config = {"from_attributes": True}


@router.post("/{lot_id}/generate", response_model=OrderDraftOut)
def create_order(lot_id: str, builder_id: Optional[str] = None, db: Session = Depends(get_db)):
    """Generate a purchase order draft for a lot."""
    order = generate_order(db, lot_id, builder_id)
    return order


@router.get("/{lot_id}", response_model=List[OrderDraftOut])
def get_orders(lot_id: str, db: Session = Depends(get_db)):
    """Get all order drafts for a lot."""
    orders = db.query(OrderDraft).filter(OrderDraft.lot_id == lot_id).all()
    if not orders:
        raise HTTPException(status_code=404, detail=f"No orders for lot {lot_id}")
    return orders
