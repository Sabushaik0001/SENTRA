"""Document-related models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lot_id = Column(String(50), index=True)
    builder_id = Column(String(50))
    document_type = Column(String(50))
    file_name = Column(Text)
    s3_path = Column(Text)
    status = Column(String(50), default="uploaded") # Valid statuses: uploaded, classified, extracted, failed
    extracted_json = Column(JSONB, nullable=True)
    page_count = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    classifications = relationship("DocumentClassification", back_populates="document", cascade="all, delete-orphan")


class DocumentClassification(Base):
    __tablename__ = "document_classifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"))
    document_type = Column(String(50))
    builder_id = Column(String(50))
    format = Column(String(50))
    confidence_score = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="classifications")


class PromptTemplate(Base):
    __tablename__ = "prompt_templates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    builder_id = Column(String(50))
    document_type = Column(String(50))
    version = Column(Integer)
    prompt_text = Column(Text)
    is_active = Column(Boolean, default=True)
    created_by = Column(String(100))
    performance_metrics = Column(JSONB)
    created_at = Column(DateTime, default=datetime.utcnow)
