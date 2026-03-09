"""Document classification using Claude via LiteLLM."""

import json
import logging
import uuid

import litellm
from sqlalchemy.orm import Session

from app.config import CLAUDE_MODEL
from app.models.documents import Document, DocumentClassification

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a construction document classifier.
Analyze this document and return a JSON object with:
- document_type: one of "selection_sheet", "takeoff_sheet", "unknown"
- builder_id: the builder or community identifier if found, else null
- format: "standard", "custom", or "unknown"
- confidence: a float 0-1

Return ONLY valid JSON. No markdown, no explanation."""


def classify_document(db: Session, document_id: uuid.UUID, file_content: str) -> DocumentClassification:
    """Call Claude to classify a document and persist the result."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise ValueError(f"Document {document_id} not found")

    response = litellm.completion(
        model=CLAUDE_MODEL,
        messages=[
            {"role": "user", "content": f"{CLASSIFICATION_PROMPT}\n\nDocument content (first 3000 chars):\n{file_content[:3000]}"},
        ],
        temperature=0,
        max_tokens=512,
    )

    raw = response.choices[0].message.content or "{}"
    raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    result = json.loads(raw)

    classification = DocumentClassification(
        document_id=document_id,
        document_type=result.get("document_type", "unknown"),
        builder_id=result.get("builder_id"),
        format=result.get("format"),
        confidence_score=result.get("confidence", 0.0),
    )
    db.add(classification)
    db.commit()
    db.refresh(classification)

    doc.status = "classified"
    db.commit()

    logger.info("Classified document %s as %s (%.2f)", document_id, classification.document_type, classification.confidence_score or 0)
    return classification
