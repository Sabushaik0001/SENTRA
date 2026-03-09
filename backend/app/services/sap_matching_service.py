"""Vector search against Pinecone for SAP material matching."""

import logging
import time
from typing import Dict, List, Optional

from pinecone import Pinecone, ServerlessSpec
from sqlalchemy.orm import Session

from app.config import AWS_REGION, EMBED_DIMENSIONS, PINECONE_API_KEY, PINECONE_INDEX_NAME
from app.models.sap_materials import ConfirmedMapping
from app.services.embedding_service import generate_embedding

logger = logging.getLogger(__name__)

_pc = None
_index = None

AUTO_MAP_THRESHOLD = 0.92
REVIEW_THRESHOLD = 0.75


def _get_index():
    global _pc, _index
    if _index is None:
        _pc = Pinecone(api_key=PINECONE_API_KEY)
        existing = [idx.name for idx in _pc.list_indexes()]
        if PINECONE_INDEX_NAME not in existing:
            logger.info("Creating Pinecone index '%s'", PINECONE_INDEX_NAME)
            _pc.create_index(
                name=PINECONE_INDEX_NAME,
                dimension=EMBED_DIMENSIONS,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region=AWS_REGION),
            )
            while not _pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
                time.sleep(1)
        _index = _pc.Index(PINECONE_INDEX_NAME)
    return _index


def search_sap_material(material_description: str, top_k: int = 5) -> List[Dict]:
    """
    Search Pinecone for matching SAP materials.
    Returns list of dicts with: sap_code, description, category, uom, score, status.
    """
    embedding = generate_embedding(material_description)
    index = _get_index()

    results = index.query(vector=embedding, top_k=top_k, include_metadata=True)

    matches = []
    for match in results.get("matches", []):
        score = match["score"]
        if score >= AUTO_MAP_THRESHOLD:
            status = "auto_mapped"
        elif score >= REVIEW_THRESHOLD:
            status = "needs_review"
        else:
            status = "manual_mapping"

        matches.append({
            "sap_code": match["id"],
            "description": match.get("metadata", {}).get("description", ""),
            "category": match.get("metadata", {}).get("category", ""),
            "uom": match.get("metadata", {}).get("uom", ""),
            "score": round(score, 4),
            "status": status,
        })

    return matches


def match_material(db: Session, material_name: str) -> Optional[Dict]:
    """
    Try confirmed_mappings cache first, then fall back to vector search.
    Returns the best match or None.
    """
    cached = (
        db.query(ConfirmedMapping)
        .filter(ConfirmedMapping.material_name == material_name)
        .first()
    )
    if cached:
        return {
            "sap_code": cached.sap_code,
            "score": cached.confidence_score,
            "status": "cached",
            "source": "confirmed_mappings",
        }

    matches = search_sap_material(material_name, top_k=1)
    if matches:
        best = matches[0]
        if best["status"] == "auto_mapped":
            mapping = ConfirmedMapping(
                material_name=material_name,
                sap_code=best["sap_code"],
                confidence_score=best["score"],
                approved_by="system",
            )
            db.add(mapping)
            db.commit()
        return best

    return None
