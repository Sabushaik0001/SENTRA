"""Pydantic schemas for selection sheet data."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class SelectionOut(BaseModel):
    id: UUID
    lot_id: str
    option_code: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    color: Optional[str] = None
    location_number: Optional[str] = None
    change_order_status: Optional[bool] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SelectionListResponse(BaseModel):
    lot_id: str
    count: int
    selections: List[SelectionOut]
