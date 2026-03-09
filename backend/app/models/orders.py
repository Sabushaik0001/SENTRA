"""Purchase order models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class OrderDraft(Base):
    __tablename__ = "order_drafts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(String(50))
    builder_id = Column(String(50))
    order_status = Column(String(50))
    total_amount = Column(Float)
    created_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    lines = relationship("OrderLine", back_populates="order", cascade="all, delete-orphan")


class OrderLine(Base):
    __tablename__ = "order_lines"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("order_drafts.id", ondelete="CASCADE"))
    sap_material_code = Column(String(50))
    description = Column(Text)
    quantity = Column(Float)
    uom = Column(String(20))
    category = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    order = relationship("OrderDraft", back_populates="lines")
