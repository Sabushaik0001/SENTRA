"""Audit, corrections, and builder config models."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


class Correction(Base):
    __tablename__ = "corrections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True))
    field_name = Column(String(100))
    original_value = Column(Text)
    corrected_value = Column(Text)
    corrected_by = Column(String(100))
    corrected_at = Column(DateTime, default=datetime.utcnow)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True))
    event_type = Column(String(100))
    user_id = Column(String(100))
    duration_ms = Column(Integer)
    metadata_ = Column("metadata", JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)


class BuilderConfig(Base):
    __tablename__ = "builder_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    builder_id = Column(String(50))
    builder_name = Column(String(100))
    plan = Column(String(100))
    selection_sheet_format = Column(String(50))
    takeoff_sheet_format = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)
