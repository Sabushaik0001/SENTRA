"""Business rules: substitution matrix, sundry rules, labor rules."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base


class MaterialSubstitutionMatrix(Base):
    __tablename__ = "material_substitution_matrix"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    when_option_selected = Column(String(50))
    replaces_material_type = Column(String(100))
    room = Column(String(100))
    with_material_type = Column(String(100))
    builder_id = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class SundryRule(Base):
    __tablename__ = "sundry_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_category = Column(String(100))
    sundry_item = Column(String(255))
    quantity_ratio = Column(Float)
    uom = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)


class LaborRule(Base):
    __tablename__ = "labor_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    material_category = Column(String(100))
    sap_labor_code = Column(String(50))
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
