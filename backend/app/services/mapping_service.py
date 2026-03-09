"""Deterministic material mapping engine using substitution rules."""

import logging

from sqlalchemy.orm import Session

from app.models.rules import MaterialSubstitutionMatrix
from app.models.selections import Selection
from app.models.takeoff import TakeoffData, TakeoffMapped

logger = logging.getLogger(__name__)


def run_mapping(db: Session, lot_id: str) -> list[TakeoffMapped]:
    """
    Apply substitution matrix rules to takeoff data based on selected options.

    1. Load selected option codes for this lot.
    2. Load all takeoff rows for this lot.
    3. For each takeoff row, check if a substitution rule applies.
    4. Write final material assignments to takeoff_mapped.
    """
    # Gather selected option codes
    selections = db.query(Selection).filter(Selection.lot_id == lot_id).all()
    selected_codes = {s.option_code for s in selections if s.option_code}

    # Load substitution rules
    rules = db.query(MaterialSubstitutionMatrix).all()
    rule_map: dict[tuple[str, str], str] = {}
    for rule in rules:
        if rule.when_option_selected in selected_codes:
            key = (rule.room or "", rule.replaces_material_type or "")
            rule_map[key] = rule.with_material_type or ""

    # Load takeoff rows
    takeoff_rows = db.query(TakeoffData).filter(TakeoffData.lot_id == lot_id).all()

    mapped_rows = []
    for row in takeoff_rows:
        room = row.room_name or ""
        material = row.std_material or ""

        # Check if a substitution rule overrides this material
        substituted = rule_map.get((room, material))
        final_material = substituted if substituted else material

        # Determine primary quantity
        quantity = row.sq_yards or row.wood_tile_sqft or 0.0

        mapped = TakeoffMapped(
            lot_id=lot_id,
            option_code=row.option_code,
            room_name=room,
            material_type=final_material,
            quantity=quantity,
        )
        db.add(mapped)
        mapped_rows.append(mapped)

    db.commit()
    logger.info("Mapped %d takeoff rows for lot %s (%d substitutions applied)", len(mapped_rows), lot_id, len(rule_map))
    return mapped_rows
