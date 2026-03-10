"""
Seed prompt_templates table with Ryan Homes extraction prompts.

Usage:
    docker compose exec api python -m scripts.seed_prompt_templates
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import SessionLocal
from app.models.documents import PromptTemplate

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)


def seed_prompt_templates():
    """Insert Ryan Homes prompt templates from prompt files."""
    db = SessionLocal()
    
    try:
        prompts_dir = Path(__file__).resolve().parent.parent / "prompts" / "ryan_homes"
        
        # Seed selection sheet prompt
        selection_file = prompts_dir / "selection_sheet_v1.txt"
        if not selection_file.exists():
            logger.error("Prompt file not found: %s", selection_file)
            return
        
        selection_prompt_text = selection_file.read_text(encoding="utf-8")
        
        existing_selection = db.query(PromptTemplate).filter(
            PromptTemplate.builder_id == "RYAN",
            PromptTemplate.document_type == "selection_sheet",
            PromptTemplate.version == 1
        ).first()
        
        if not existing_selection:
            selection_prompt = PromptTemplate(
                builder_id="RYAN",
                document_type="selection_sheet",
                version=1,
                prompt_text=selection_prompt_text,
                is_active=True,
                created_by="system",
                performance_metrics=None
            )
            db.add(selection_prompt)
            logger.info("✓ Seeded Ryan Homes selection_sheet prompt (version 1)")
        else:
            logger.info("Ryan Homes selection_sheet prompt v1 already exists. Skipping.")
        
        # Seed takeoff sheet prompt
        takeoff_file = prompts_dir / "takeoff_sheet_v1.txt"
        if not takeoff_file.exists():
            logger.error("Prompt file not found: %s", takeoff_file)
            return
        
        takeoff_prompt_text = takeoff_file.read_text(encoding="utf-8")
        
        existing_takeoff = db.query(PromptTemplate).filter(
            PromptTemplate.builder_id == "RYAN",
            PromptTemplate.document_type == "takeoff_sheet",
            PromptTemplate.version == 1
        ).first()
        
        if not existing_takeoff:
            takeoff_prompt = PromptTemplate(
                builder_id="RYAN",
                document_type="takeoff_sheet",
                version=1,
                prompt_text=takeoff_prompt_text,
                is_active=True,
                created_by="system",
                performance_metrics=None
            )
            db.add(takeoff_prompt)
            logger.info("✓ Seeded Ryan Homes takeoff_sheet prompt (version 1)")
        else:
            logger.info("Ryan Homes takeoff_sheet prompt v1 already exists. Skipping.")
        
        db.commit()
        logger.info("✓ Prompt templates seeding completed")
        
    except Exception as exc:
        logger.error("Failed to seed prompt_templates: %s", exc)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_prompt_templates()