"""Document classification using Claude via LiteLLM."""

import json
import logging
import uuid

import litellm
from sqlalchemy.orm import Session

from app.config import CLAUDE_MODEL, LITELLM_MAX_RETRIES, LITELLM_TIMEOUT, LITELLM_FALLBACK_MODELS
from app.models.documents import Document, DocumentClassification

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """You are a construction document classifier.
Analyze this document and return a JSON object with:
- document_type: one of "selection_sheet", "takeoff_sheet", "unknown"
- builder_id: the builder identifier (e.g., "RYAN", "DR_HORTON", "LENNAR") if found, else null
- builder_format: the specific format code (e.g., "RYAN_PST00-03", "RYAN_PISA_TORRE") if identifiable, else null
- format: "standard", "custom", or "unknown"
- confidence: a float 0-1
Look for builder names like "Ryan Homes", "NVR", plan names like "PISA TORRE", and format codes in headers.
Return ONLY valid JSON. No markdown, no explanation."""


class ClassificationService:
    """Service for classifying construction documents using Claude."""
    
    def __init__(self, db: Session):
        """Initialize classification service with database session."""
        self.db = db
    
    def classify_document(self, document_id: uuid.UUID, file_content: str) -> DocumentClassification:
        """
        Call Claude to classify a document and persist the result.
        
        Args:
            document_id: UUID of the document to classify
            file_content: Text content extracted from the document
            
        Returns:
            DocumentClassification object with classification results
            
        Raises:
            ValueError: If document not found
            Exception: If classification fails after retries
        """
        doc = self.db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise ValueError(f"Document {document_id} not found")

        try:
            response = litellm.completion(
                model=CLAUDE_MODEL,
                messages=[
                    {"role": "user", "content": f"{CLASSIFICATION_PROMPT}\n\nDocument content (first 3000 chars):\n{file_content[:3000]}"},
                ],
                temperature=0,
                max_tokens=512,
                num_retries=LITELLM_MAX_RETRIES,
                timeout=LITELLM_TIMEOUT,
                fallbacks=LITELLM_FALLBACK_MODELS,
            )

            raw = response.choices[0].message.content or "{}"
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            result = json.loads(raw)

            # Extract builder_format or construct from builder_id
            builder_format = result.get("builder_format")
            if not builder_format and result.get("builder_id"):
                builder_format = f"{result.get('builder_id')}_{result.get('format', 'STANDARD')}"

            classification = DocumentClassification(
                document_id=document_id,
                document_type=result.get("document_type", "unknown"),
                builder_id=result.get("builder_id"),
                format=builder_format or result.get("format"),
                confidence_score=result.get("confidence", 0.0),
            )
            self.db.add(classification)
            self.db.commit()
            self.db.refresh(classification)

            doc.status = "classified"
            self.db.commit()

            logger.info("Classified document %s as %s (%.2f)", document_id, classification.document_type, classification.confidence_score or 0)
            return classification
        
        except Exception as exc:
            logger.exception("Error classifying document %s: %s", document_id, exc)
            
            # Mark document as needing manual review
            doc.status = "needs_manual_review"
            self.db.commit()
            
            # Re-raise to trigger Celery retry
            raise


# Backward compatibility: keep function wrapper for existing code
def classify_document(db: Session, document_id: uuid.UUID, file_content: str) -> DocumentClassification:
    """
    Convenience function wrapper for ClassificationService.
    Maintains backward compatibility with existing code.
    """
    service = ClassificationService(db)
    return service.classify_document(document_id, file_content)