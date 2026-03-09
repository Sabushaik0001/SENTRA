"""Pydantic schemas for document endpoints."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    job_id: UUID
    lot_id: str
    status: str
    selection_sheet_s3: str
    takeoff_sheet_s3: str
    message: str


class DocumentStatusResponse(BaseModel):
    id: UUID
    lot_id: str
    document_type: str
    file_name: str
    s3_path: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ClassificationResponse(BaseModel):
    id: UUID
    document_id: UUID
    document_type: str
    builder_id: Optional[str] = None
    format: Optional[str] = None
    confidence_score: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}
