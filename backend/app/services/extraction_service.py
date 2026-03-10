"""
extraction_service.py — PDF → Page Images → Claude Vision → Structured JSON → DB

Flow:
  1. Receive PDF bytes
  2. Convert each page to a PNG image (300 DPI) via pdf2image
  3. Send each page image to Claude Sonnet 4.5 Vision via LiteLLM
  4. Parse structured JSON from each page
  5. Aggregate all pages and populate selections / takeoff_data tables
"""

import base64
import io
import json
import logging
import os
import tempfile
import uuid
from typing import Any, Dict, List

import litellm
from pdf2image import convert_from_bytes
from sqlalchemy.orm import Session

from app.config import CLAUDE_MODEL
from app.models.documents import Document
from app.models.selections import Selection
from app.models.takeoff import TakeoffData

logger = logging.getLogger(__name__)

def _get_prompt_from_db(db: Session, builder_id: str, document_type: str) -> str:
    """
    Load active prompt template from database for given builder and document type.
    Falls back to hardcoded prompts if not found.
    """
    from app.models.documents import PromptTemplate
    
    if not builder_id:
        logger.warning("No builder_id provided, using hardcoded prompt for %s", document_type)
        if document_type == "selection_sheet":
            return SELECTION_SHEET_PROMPT
        elif document_type == "takeoff_sheet":
            return TAKEOFF_SHEET_PROMPT
        else:
            raise ValueError(f"Unknown document type: {document_type}")
    
    template = db.query(PromptTemplate).filter(
        PromptTemplate.builder_id == builder_id,
        PromptTemplate.document_type == document_type,
        PromptTemplate.is_active == True
    ).order_by(PromptTemplate.version.desc()).first()
    
    if template:
        logger.info("Using database prompt (builder=%s, type=%s, version=%d)", 
                   builder_id, document_type, template.version)
        return template.prompt_text
    
    # Fallback to hardcoded
    logger.warning("No database prompt found for %s/%s, using hardcoded fallback", 
                  builder_id, document_type)
    if document_type == "selection_sheet":
        return SELECTION_SHEET_PROMPT
    elif document_type == "takeoff_sheet":
        return TAKEOFF_SHEET_PROMPT
    else:
        raise ValueError(f"Unknown document type: {document_type}")

# ── Prompts ──────────────────────────────────────────────────────────────────

SELECTION_SHEET_PROMPT = """You are an expert document data extraction system.

The input provided to you is a single page image extracted from a construction selection PDF document.

Your task is to extract ALL structured information from the page including:

1. Header metadata
2. All tables
3. Section names
4. Every row in each table
5. Any additional structured content like change orders

IMPORTANT RULES

1. DO NOT summarize.
2. DO NOT skip any rows.
3. DO NOT merge rows.
4. Preserve the exact values from the image.
5. If a column value is empty return null.
6. If a section contains multiple tables extract them separately.
7. If rows wrap across lines reconstruct them correctly.
8. Maintain the section hierarchy.

--------------------------------

STEP 1 — Extract Document Metadata (if present)

Extract fields such as:

Address
City
State
Zip
Business Phone
Fax
Spec/Model
Start Date
Projected Settlement Date
Lumber Scheduled Date
Product Name
Community
Lot
Permit Number
Purchaser Name
CoPurchaser Name
Sales Manager
Sales Rep
Project Manager

--------------------------------

STEP 2 — Detect Sections

Each page may contain multiple sections formatted like:

SELECTED OPTIONS | LEVEL ENTRY
SELECTED OPTIONS | DESIGNER INTERIORS
SELECTED OPTIONS | FOUNDATIONS
SELECTED OPTIONS | KITCHEN
SELECTED OPTIONS | FLOORING
SELECTED OPTIONS | ELECTRICAL AND HOME TECHNOLOGY
CUSTOM OPTIONS
CHANGE ORDER

Treat each as a separate section.

--------------------------------

STEP 3 — Extract Tables

Each section usually contains a table with columns like:

Option
Description
Category
Quantity
Color/Location

Extract EVERY row exactly.

Example row format:

{
  "option": "FTA",
  "description": "MAIN LEVEL ENTRY W/BASEMENT",
  "category": "B (A)",
  "quantity": null,
  "color_location": null
}

--------------------------------

STEP 4 — Extract Change Orders

If a CHANGE ORDER section appears extract:

Change
Option
Description
Added Description
Color/Location
Quantity
Category
Create Person
Date
Status

--------------------------------

STEP 5 — Return Structured JSON

Return data in the following structure:

{
  "page_number": <page_number>,

  "metadata": {
    "address": "",
    "city": "",
    "state": "",
    "zip": "",
    "spec_model": "",
    "start_date": "",
    "projected_settlement_date": "",
    "product": "",
    "community": "",
    "lot": "",
    "permit_number": "",
    "purchaser_name": "",
    "copurchaser_name": "",
    "sales_manager": "",
    "sales_rep": "",
    "project_manager": ""
  },

  "sections": [
    {
      "section_name": "SELECTED OPTIONS | LEVEL ENTRY",
      "rows": [
        {
          "option": "",
          "description": "",
          "category": "",
          "quantity": "",
          "color_location": ""
        }
      ]
    }
  ],

  "change_orders": [
    {
      "change_order_number": "",
      "date": "",
      "status": "",
      "rows": [
        {
          "change": "",
          "option": "",
          "description": "",
          "added_description": "",
          "color_location": "",
          "quantity": "",
          "category": "",
          "create_person": ""
        }
      ]
    }
  ]
}

--------------------------------

STEP 6 — Validation

Before returning the output:

Verify every visible table row is captured
Ensure section titles match exactly
Ensure JSON format is valid

--------------------------------

Output ONLY valid JSON.
Do not include explanations."""

TAKEOFF_SHEET_PROMPT = """You are an expert construction document data extraction system.

The input provided to you is a single page image extracted from a construction Take Off Sheet.

Your task is to extract ALL structured information from the page.

IMPORTANT RULES

1. DO NOT summarize.
2. DO NOT skip any rows.
3. DO NOT merge rows.
4. Preserve the exact values from the image.
5. If a column value is empty return null.
6. If rows wrap across lines reconstruct them correctly.

Extract ALL rows from the table. Each row must have:

- room_name: the room or area name
- std_material: standard material code or type
- option_code: option code if this is an optional row, else null
- subfloor: subfloor type if present
- material_width: float or null
- cut_length: float or null
- sq_yards: float or null
- pad_sq_yards: float or null
- wood_tile_sqft: float or null
- shoe_base_lf: float or null
- cabinet_sides_lf: float or null
- toe_kick_lf: float or null
- nosing_lf: float or null
- threshold_lf: float or null
- t_molding_lf: float or null
- notes: any notes including REPLACES logic
- base_opt_elev: B for base, O for optional, E for elevation (if present)

Also extract any keys or legends on the page.

Return data in this structure:

{
  "page_number": <page_number>,
  "keys": {},
  "section": "",
  "rows": [
    {
      "room_name": "",
      "std_material": "",
      "option_code": null,
      "subfloor": null,
      "material_width": null,
      "cut_length": null,
      "sq_yards": null,
      "pad_sq_yards": null,
      "wood_tile_sqft": null,
      "shoe_base_lf": null,
      "cabinet_sides_lf": null,
      "toe_kick_lf": null,
      "nosing_lf": null,
      "threshold_lf": null,
      "t_molding_lf": null,
      "notes": null,
      "base_opt_elev": null
    }
  ]
}

Output ONLY valid JSON.
Do not include explanations."""


# ── PDF to Images ────────────────────────────────────────────────────────────

POPPLER_PATH = r"C:\poppler\poppler-24.08.0\Library\bin"


def convert_pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[bytes]:
    """Convert a PDF to a list of PNG image byte arrays, one per page."""
    import shutil
    poppler = POPPLER_PATH if shutil.which("pdfinfo") is None and os.path.isdir(POPPLER_PATH) else None
    images = convert_from_bytes(pdf_bytes, dpi=dpi, fmt="png", poppler_path=poppler)
    image_bytes_list = []
    for img in images:
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        image_bytes_list.append(buf.getvalue())
    logger.info("Converted PDF to %d page images at %d DPI", len(image_bytes_list), dpi)
    return image_bytes_list


# ── Claude Vision per page ───────────────────────────────────────────────────

def _extract_page_with_vision(
    image_bytes: bytes,
    page_number: int,
    prompt: str,
) -> Dict[str, Any]:
    """Send a single page image to Claude Vision and return parsed JSON."""
    b64 = base64.standard_b64encode(image_bytes).decode("utf-8")

    # Inject page number into prompt
    full_prompt = prompt.replace("<page_number>", str(page_number))

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                    },
                },
                {"type": "text", "text": full_prompt},
            ],
        }
    ]

    response = litellm.completion(
        model=CLAUDE_MODEL,
        messages=messages,
        temperature=0,
        max_tokens=8192,
    )

    raw = response.choices[0].message.content or "{}"
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.removeprefix("```json").removeprefix("```")
    if raw.endswith("```"):
        raw = raw.removesuffix("```")
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Claude sometimes returns multiple JSON objects concatenated.
        # Try to parse them individually and merge.
        try:
            decoder = json.JSONDecoder()
            objects = []
            idx = 0
            while idx < len(raw):
                raw_trimmed = raw[idx:].lstrip()
                if not raw_trimmed:
                    break
                obj, end = decoder.raw_decode(raw_trimmed)
                objects.append(obj)
                idx += len(raw) - len(raw_trimmed) + end
            if objects:
                # Merge: keep first object as base, combine rows/sections
                merged = objects[0]
                for extra in objects[1:]:
                    for key in ("rows", "sections", "change_orders"):
                        if key in extra:
                            merged.setdefault(key, []).extend(extra[key])
                    if "keys" in extra and "keys" in merged:
                        merged["keys"].update(extra["keys"])
                logger.info("Merged %d JSON objects from page %d", len(objects), page_number)
                return merged
        except (json.JSONDecodeError, ValueError):
            pass
        logger.error("Failed to parse JSON from page %d.\nRaw: %s", page_number, raw[:500])
        return {"page_number": page_number, "error": "JSON parse failed"}


# ── Selection Sheet Extraction ───────────────────────────────────────────────

def extract_selection_sheet_from_bytes(
    db: Session,
    document_id: uuid.UUID,
    file_bytes: bytes,
    file_name: str,
    lot_id: str,
    builder_id: str,
) -> List[Selection]:
    """
    Full pipeline: PDF bytes → page images → Claude Vision → selections table.
    Returns list of created Selection records.
    """
    logger.info("Starting selection sheet extraction for lot %s (%s)", lot_id, file_name)

    # Step 1: Convert PDF to page images
    page_images = convert_pdf_to_images(file_bytes)
    prompt = _get_prompt_from_db(db, builder_id, "selection_sheet")

    # Step 2: Extract each page with Claude Vision
    all_page_results = []
    for idx, img_bytes in enumerate(page_images, start=1):
        logger.info("Extracting page %d/%d for lot %s", idx, len(page_images), lot_id)
        page_data = _extract_page_with_vision(img_bytes, idx, prompt)
        all_page_results.append(page_data)

    # Step 3: Populate selections table from all pages
    selections = []
    for page_data in all_page_results:
        if "error" in page_data:
            continue

        # Extract rows from sections
        for section in page_data.get("sections", []):
            section_name = section.get("section_name", "")
            for row in section.get("rows", []):
                sel = Selection(
                    lot_id=lot_id,
                    option_code=row.get("option"),
                    description=row.get("description"),
                    category=row.get("category"),
                    quantity=_safe_int(row.get("quantity")),
                    color=row.get("color_location"),
                    location_number=section_name,
                    change_order_status=False,
                )
                db.add(sel)
                selections.append(sel)

        # Extract change order rows
        for co in page_data.get("change_orders", []):
            for row in co.get("rows", []):
                sel = Selection(
                    lot_id=lot_id,
                    option_code=row.get("option"),
                    description=row.get("description"),
                    category=row.get("category"),
                    quantity=_safe_int(row.get("quantity")),
                    color=row.get("color_location"),
                    location_number=row.get("added_description"),
                    change_order_status=True,
                )
                db.add(sel)
                selections.append(sel)

    # Save raw JSON + structured rows
    _save_extracted_json(db, document_id, all_page_results, len(page_images))
    db.commit()
    logger.info(
        "Extracted %d selections from %d pages for lot %s",
        len(selections), len(page_images), lot_id,
    )
    return selections


# ── Takeoff Sheet Extraction ─────────────────────────────────────────────────

def extract_takeoff_sheet_from_bytes(
    db: Session,
    document_id: uuid.UUID,
    file_bytes: bytes,
    file_name: str,
    lot_id: str,
    builder_id: str,
) -> List[TakeoffData]:
    """
    Full pipeline: PDF bytes → page images → Claude Vision → takeoff_data table.
    Returns list of created TakeoffData records.
    """
    logger.info("Starting takeoff sheet extraction for lot %s (%s)", lot_id, file_name)

    # Step 1: Convert PDF to page images
    page_images = convert_pdf_to_images(file_bytes)
    prompt = _get_prompt_from_db(db, builder_id, "takeoff_sheet")

    # Step 2: Extract each page with Claude Vision
    all_page_results = []
    for idx, img_bytes in enumerate(page_images, start=1):
        logger.info("Extracting page %d/%d for lot %s", idx, len(page_images), lot_id)
        page_data = _extract_page_with_vision(img_bytes, idx, prompt)
        all_page_results.append(page_data)

    # Step 3: Populate takeoff_data table from all pages
    takeoff_rows = []
    for page_data in all_page_results:
        if "error" in page_data:
            continue

        for row in page_data.get("rows", []):
            td = TakeoffData(
                lot_id=lot_id,
                room_name=row.get("room_name"),
                std_material=row.get("std_material"),
                option_code=row.get("option_code"),
                subfloor=row.get("subfloor"),
                material_width=_safe_float(row.get("material_width")),
                cut_length=_safe_float(row.get("cut_length")),
                sq_yards=_safe_float(row.get("sq_yards")),
                pad_sq_yards=_safe_float(row.get("pad_sq_yards")),
                wood_tile_sqft=_safe_float(row.get("wood_tile_sqft")),
                shoe_base_lf=_safe_float(row.get("shoe_base_lf")),
                cabinet_sides_lf=_safe_float(row.get("cabinet_sides_lf")),
                toe_kick_lf=_safe_float(row.get("toe_kick_lf")),
                nosing_lf=_safe_float(row.get("nosing_lf")),
                threshold_lf=_safe_float(row.get("threshold_lf")),
                t_molding_lf=_safe_float(row.get("t_molding_lf")),
                notes=row.get("notes"),
            )
            db.add(td)
            takeoff_rows.append(td)

    _save_extracted_json(db, document_id, all_page_results, len(page_images))
    db.commit()
    logger.info(
        "Extracted %d takeoff rows from %d pages for lot %s",
        len(takeoff_rows), len(page_images), lot_id,
    )
    return takeoff_rows


# ── Helpers ──────────────────────────────────────────────────────────────────

def _safe_int(val) -> int:
    """Convert to int, return None if not possible."""
    if val is None:
        return None
    try:
        return int(val)
    except (ValueError, TypeError):
        return None


def _safe_float(val) -> float:
    """Convert to float, return None if not possible."""
    if val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _save_extracted_json(
    db: Session,
    document_id: uuid.UUID,
    page_results: List[Dict[str, Any]],
    page_count: int,
):
    """Save raw extraction JSON to documents table, upload to S3, and update status."""
    from app.services.s3_service import upload_file_to_s3

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.extracted_json = page_results
        doc.page_count = page_count
        doc.status = "extracted"

        # Upload extracted JSON to S3 alongside the source PDF
        if doc.s3_path:
            # Derive JSON filename from document_type (e.g. selection_sheet → selection_sheet.json)
            json_filename = f"{doc.document_type}.json" if doc.document_type else "extracted.json"
            # Get the S3 folder from existing path: strip bucket prefix and filename
            s3_key = "/".join(doc.s3_path.split("/")[3:])  # remove s3://bucket/
            s3_folder = s3_key.rsplit("/", 1)[0]  # remove filename
            json_s3_key = f"{s3_folder}/{json_filename}"

            json_bytes = json.dumps(page_results, indent=2, ensure_ascii=False).encode("utf-8")
            json_s3_path = upload_file_to_s3(json_bytes, json_s3_key, content_type="application/json")
            logger.info("Uploaded extracted JSON to %s", json_s3_path)


def _update_doc_status(db: Session, document_id: uuid.UUID, status: str):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc:
        doc.status = status
        db.commit()
