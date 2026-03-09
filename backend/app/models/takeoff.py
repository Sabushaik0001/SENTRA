"""Take-off sheet models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class TakeoffData(Base):
    __tablename__ = "takeoff_data"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(String(50), index=True)
    room_name = Column(Text)
    std_material = Column(Text)
    option_code = Column(String(100))
    subfloor = Column(Text)
    material_width = Column(Float)
    cut_length = Column(Float)
    sq_yards = Column(Float)
    pad_sq_yards = Column(Float)
    wood_tile_sqft = Column(Float)
    shoe_base_lf = Column(Float)
    cabinet_sides_lf = Column(Float)
    toe_kick_lf = Column(Float)
    nosing_lf = Column(Float)
    threshold_lf = Column(Float)
    t_molding_lf = Column(Float)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class TakeoffMapped(Base):
    __tablename__ = "takeoff_mapped"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(String(50))
    option_code = Column(String(100))
    room_name = Column(Text)
    material_type = Column(Text)
    quantity = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
