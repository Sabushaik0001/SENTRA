"""Selection sheet extraction results."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class Selection(Base):
    __tablename__ = "selections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(String(50), index=True)
    option_code = Column(String(100))
    description = Column(Text)
    category = Column(String(50))
    quantity = Column(Integer)
    color = Column(Text)
    location_number = Column(Text)
    change_order_status = Column(Boolean)
    created_at = Column(DateTime, default=datetime.utcnow)
