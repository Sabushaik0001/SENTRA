"""SAP material and confirmed mapping models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class SapMaterial(Base):
    __tablename__ = "sap_materials"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sap_code = Column(String(50), unique=True, index=True)
    description = Column(Text)
    material_category = Column(String(100))
    trade_type = Column(String(100))
    uom = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class ConfirmedMapping(Base):
    __tablename__ = "confirmed_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_name = Column(String(255), index=True)
    sap_code = Column(String(50))
    confidence_score = Column(Float)
    approved_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
