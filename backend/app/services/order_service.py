"""Purchase order generation from mapped takeoff data."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.orders import OrderDraft, OrderLine
from app.models.rules import LaborRule, SundryRule
from app.models.takeoff import TakeoffMapped
from app.services.sap_matching_service import match_material

logger = logging.getLogger(__name__)


def generate_order(db: Session, lot_id: str, builder_id: Optional[str] = None) -> OrderDraft:
    """
    Generate a purchase order draft from mapped takeoff data.

    1. Load mapped materials for the lot.
    2. Match each material to an SAP code via vector search.
    3. Apply sundry rules (add sundry items per material category).
    4. Apply labor rules (add labor lines per material category).
    5. Create order_drafts + order_lines.
    """
    mapped_rows = db.query(TakeoffMapped).filter(TakeoffMapped.lot_id == lot_id).all()
    if not mapped_rows:
        raise ValueError(f"No mapped data found for lot {lot_id}. Run mapping first.")

    order = OrderDraft(
        lot_id=lot_id,
        builder_id=builder_id,
        order_status="draft",
        total_amount=0.0,
        created_by="system",
    )
    db.add(order)
    db.flush()

    lines = []
    categories_seen = set()

    for row in mapped_rows:
        material_type = row.material_type or ""
        match = match_material(db, material_type)

        sap_code = match["sap_code"] if match else "UNMATCHED"
        category = match.get("category", "") if match else ""

        line = OrderLine(
            order_id=order.id,
            sap_material_code=sap_code,
            description=material_type,
            quantity=row.quantity or 0.0,
            uom=match.get("uom", "EA") if match else "EA",
            category=category,
        )
        db.add(line)
        lines.append(line)

        if category:
            categories_seen.add(category)

    # Add sundry items
    for cat in categories_seen:
        sundry_rules = db.query(SundryRule).filter(SundryRule.material_category == cat).all()
        for rule in sundry_rules:
            sundry_match = match_material(db, rule.sundry_item or "")
            sundry_line = OrderLine(
                order_id=order.id,
                sap_material_code=sundry_match["sap_code"] if sundry_match else "UNMATCHED",
                description=rule.sundry_item,
                quantity=rule.quantity_ratio or 1.0,
                uom=rule.uom or "EA",
                category="sundry",
            )
            db.add(sundry_line)
            lines.append(sundry_line)

    # Add labor lines
    for cat in categories_seen:
        labor_rules = db.query(LaborRule).filter(LaborRule.material_category == cat).all()
        for rule in labor_rules:
            labor_line = OrderLine(
                order_id=order.id,
                sap_material_code=rule.sap_labor_code or "UNMATCHED",
                description=rule.description or f"Labor for {cat}",
                quantity=1.0,
                uom="EA",
                category="labor",
            )
            db.add(labor_line)
            lines.append(labor_line)

    order.total_amount = sum(l.quantity or 0 for l in lines)
    db.commit()
    db.refresh(order)

    logger.info("Generated order %s with %d lines for lot %s", order.id, len(lines), lot_id)
    return order
