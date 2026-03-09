"""Pydantic schemas for take-off sheet data."""

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class TakeoffDataOut(BaseModel):
    id: UUID
    lot_id: str
    room_name: Optional[str] = None
    std_material: Optional[str] = None
    option_code: Optional[str] = None
    sq_yards: Optional[float] = None
    wood_tile_sqft: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TakeoffMappedOut(BaseModel):
    id: UUID
    lot_id: str
    option_code: Optional[str] = None
    room_name: Optional[str] = None
    material_type: Optional[str] = None
    quantity: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TakeoffListResponse(BaseModel):
    lot_id: str
    count: int
    rows: List[TakeoffDataOut]
