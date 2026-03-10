"""
Seed builder_configs table with Ryan Homes record.

Usage:
    docker compose exec api python -m scripts.seed_builder_configs
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.audit import BuilderConfig

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


def seed_builder_configs():
    """Insert Ryan Homes builder configuration."""
    db = SessionLocal()
    
    try:
        # Check if already exists
        existing = db.query(BuilderConfig).filter(BuilderConfig.builder_id == "RYAN").first()
        if existing:
            logger.info("Ryan Homes config already exists (id=%s). Skipping.", existing.id)
            return
        
        # Create Ryan Homes record
        ryan_homes = BuilderConfig(
            builder_id="RYAN",
            builder_name="Ryan Homes",
            plan="PISA_TORRE",
            selection_sheet_format="PST00-03",
            takeoff_sheet_format="PST00-03",
        )
        
        db.add(ryan_homes)
        db.commit()
        db.refresh(ryan_homes)
        
        logger.info("✓ Seeded Ryan Homes config (id=%s)", ryan_homes.id)
        
    except Exception as exc:
        logger.error("Failed to seed builder_configs: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_builder_configs()