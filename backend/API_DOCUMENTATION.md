# SENTRA API Documentation

Base URL: `http://localhost:8000`

---

## Health Check

### `GET /health`
Returns API health status.

**Response:**
```json
{
  "status": "healthy"
}
```

---

## Documents

### `POST /documents/upload`
Upload selection sheet + takeoff sheet PDFs. Triggers the full async pipeline (classify → extract → map → generate order).

**Request:** `multipart/form-data`
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `selection_sheet` | File (PDF) | Yes | Selection sheet document |
| `takeoff_sheet` | File (PDF/XLSX) | Yes | Take-off sheet document |
| `builder_id` | string | No | Builder identifier (e.g. "Ryan Homes") |

**Response (202 Accepted):**
```json
{
  "job_id": "7e5ef4bf-8c4b-4dec-9444-b44580c77f8b",
  "lot_id": "LOT-DAB53C3F",
  "status": "queued",
  "selection_sheet_s3": "s3://sentra-demo/documents/2026-03-09/LOT-DAB53C3F/selection_sheet.pdf",
  "takeoff_sheet_s3": "s3://sentra-demo/documents/2026-03-09/LOT-DAB53C3F/takeoff_sheet.pdf",
  "message": "Pipeline queued. Poll GET /documents/{lot_id}/status for progress."
}
```

**What happens behind the scenes:**
1. Generates a unique `LOT-{8-char-hex}` ID
2. Uploads both files to S3 at `documents/YYYY-MM-DD/{lot_id}/`
3. Creates `Document` records in DB (status=`uploaded`)
4. Dispatches Celery pipeline:
   - **Step 1:** Classify both documents (Claude LLM → `document_classifications` table)
   - **Step 2:** Extract selection sheet (PDF → page images → Claude Vision → `selections` table)
   - **Step 3:** Extract takeoff sheet (PDF → page images → Claude Vision → `takeoff_data` table)
   - **Step 4:** Save extracted JSONs to S3 as `selection_sheet.json` and `takeoff_sheet.json`
   - **Step 5:** Run deterministic mapping engine (`takeoff_mapped` table)
   - **Step 6:** Generate purchase order via SAP vector search (`order_drafts` + `order_lines` tables)

---

### `GET /documents/{lot_id}/status`
Poll document processing status.

**Response (200):**
```json
[
  {
    "id": "1b3f6971-6bfe-46b2-9545-26ab9afe2521",
    "lot_id": "LOT-DAB53C3F",
    "document_type": "selection_sheet",
    "file_name": "Selection Sheet - SAR_BLW-R3-2127C.pdf",
    "s3_path": "s3://sentra-demo/documents/2026-03-09/LOT-DAB53C3F/selection_sheet.pdf",
    "status": "extracted",
    "created_at": "2026-03-09T12:42:25.154033"
  },
  {
    "id": "8cfa632b-a2fc-44b4-b019-7d5067ed8113",
    "lot_id": "LOT-DAB53C3F",
    "document_type": "takeoff_sheet",
    "file_name": "TAKE OFF - LOT 2127C.pdf",
    "s3_path": "s3://sentra-demo/documents/2026-03-09/LOT-DAB53C3F/takeoff_sheet.pdf",
    "status": "extracted",
    "created_at": "2026-03-09T12:42:25.154041"
  }
]
```

**Status values:** `uploaded` → `classified` → `extracted`

---

## Extraction

### `POST /extraction/{lot_id}/run`
Manually trigger extraction for an already-uploaded lot (re-run extraction without re-uploading).

**Response (200):**
```json
{
  "lot_id": "LOT-DAB53C3F",
  "results": [
    {
      "document_id": "1b3f6971-6bfe-46b2-9545-26ab9afe2521",
      "extracted_count": 45,
      "status": "extracted"
    },
    {
      "document_id": "8cfa632b-a2fc-44b4-b019-7d5067ed8113",
      "extracted_count": 42,
      "status": "extracted"
    }
  ]
}
```

---

### `GET /extraction/selections/{lot_id}`
Get all extracted selection rows for a lot.

**Response (200):**
```json
{
  "lot_id": "LOT-DAB53C3F",
  "count": 45,
  "selections": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "lot_id": "LOT-DAB53C3F",
      "option_code": "FTA",
      "description": "MAIN LEVEL ENTRY W/BASEMENT",
      "category": "B (A)",
      "quantity": null,
      "color": null,
      "location_number": "SELECTED OPTIONS | LEVEL ENTRY",
      "change_order_status": false,
      "created_at": "2026-03-09T12:43:00.000000"
    },
    {
      "id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
      "lot_id": "LOT-DAB53C3F",
      "option_code": "HH6",
      "description": "LUXURY VINYL PLANK - GREAT ROOM",
      "category": "C",
      "quantity": 1,
      "color": "COASTAL OAK",
      "location_number": "SELECTED OPTIONS | FLOORING",
      "change_order_status": false,
      "created_at": "2026-03-09T12:43:00.000000"
    }
  ]
}
```

---

### `GET /extraction/takeoff/{lot_id}`
Get all extracted takeoff rows for a lot.

**Response (200):**
```json
{
  "lot_id": "LOT-DAB53C3F",
  "count": 42,
  "rows": [
    {
      "id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
      "lot_id": "LOT-DAB53C3F",
      "room_name": "GREAT ROOM",
      "std_material": "CARPET",
      "option_code": "HH6",
      "subfloor": "PLYWOOD",
      "material_width": 12.0,
      "cut_length": 15.5,
      "sq_yards": 20.67,
      "pad_sq_yards": 20.67,
      "wood_tile_sqft": null,
      "shoe_base_lf": 45.0,
      "cabinet_sides_lf": null,
      "toe_kick_lf": null,
      "nosing_lf": null,
      "threshold_lf": 3.0,
      "t_molding_lf": null,
      "notes": "REPLACES CARPET W/ LVP",
      "created_at": "2026-03-09T12:43:30.000000"
    },
    {
      "id": "d4e5f6a7-b8c9-0123-defa-234567890123",
      "lot_id": "LOT-DAB53C3F",
      "room_name": "KITCHEN",
      "std_material": "VCT",
      "option_code": null,
      "subfloor": "PLYWOOD",
      "material_width": null,
      "cut_length": null,
      "sq_yards": null,
      "pad_sq_yards": null,
      "wood_tile_sqft": 125.0,
      "shoe_base_lf": 32.0,
      "cabinet_sides_lf": 8.0,
      "toe_kick_lf": 12.0,
      "nosing_lf": null,
      "threshold_lf": 3.0,
      "t_molding_lf": null,
      "notes": null,
      "created_at": "2026-03-09T12:43:30.000000"
    }
  ]
}
```

---

## Mapping

### `POST /mapping/sap-search`
Search SAP materials catalog using vector similarity (Pinecone).

**Request:**
```json
{
  "material_description": "Luxury Vinyl Plank Coastal Oak",
  "top_k": 5
}
```

**Response (200):**
```json
[
  {
    "sap_code": "MAT-LVP-001",
    "description": "LVP COASTAL OAK 7x48 CLICK LOCK",
    "category": "FLOORING",
    "uom": "SF",
    "score": 0.95,
    "status": "auto_mapped"
  },
  {
    "sap_code": "MAT-LVP-002",
    "description": "LVP COASTAL OAK 6x36 GLUE DOWN",
    "category": "FLOORING",
    "uom": "SF",
    "score": 0.88,
    "status": "needs_review"
  },
  {
    "sap_code": "MAT-LVP-003",
    "description": "LVP DRIFTWOOD OAK 7x48",
    "category": "FLOORING",
    "uom": "SF",
    "score": 0.72,
    "status": "manual"
  }
]
```

**Score thresholds:**
- `> 0.92` → `auto_mapped` (high confidence, used directly)
- `0.75 - 0.92` → `needs_review` (human review required)
- `< 0.75` → `manual` (no good match found)

---

### `POST /mapping/{lot_id}/run`
Run the deterministic mapping engine on extracted takeoff data. Applies substitution rules from `material_substitution_matrix` table.

**Response (200):**
```json
{
  "lot_id": "LOT-DAB53C3F",
  "mapped_count": 38,
  "status": "completed"
}
```

**What it does:**
1. Loads selected option codes from `selections` table
2. Loads substitution rules from `material_substitution_matrix` (e.g., "HH6 selected → replace CARPET with LVP in GREAT_ROOM")
3. Applies rules to each `takeoff_data` row
4. Writes results to `takeoff_mapped` table

---

## Orders

### `POST /orders/{lot_id}/generate`
Generate a purchase order draft from mapped takeoff data.

**Query Params:**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `builder_id` | string | No | Builder identifier |

**Response (200):**
```json
{
  "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
  "lot_id": "LOT-DAB53C3F",
  "builder_id": "Ryan Homes",
  "order_status": "draft",
  "total_amount": null,
  "lines": [
    {
      "sap_material_code": "MAT-LVP-001",
      "description": "LVP COASTAL OAK 7x48 CLICK LOCK",
      "quantity": 125.0,
      "uom": "SF",
      "category": "FLOORING"
    },
    {
      "sap_material_code": "MAT-TRANS-001",
      "description": "TRANSITION STRIP T-MOLD OAK",
      "quantity": 6.0,
      "uom": "EA",
      "category": "SUNDRY"
    },
    {
      "sap_material_code": "LAB-FLOOR-001",
      "description": "FLOORING INSTALLATION LABOR",
      "quantity": 1.0,
      "uom": "EA",
      "category": "LABOR"
    }
  ]
}
```

**What it does:**
1. Loads all `takeoff_mapped` rows for the lot
2. For each row: vector-searches SAP materials via Pinecone (`sap_matching_service`)
3. Checks `confirmed_mappings` cache first for previous matches
4. Applies `sundry_rules` (auto-adds accessories per material category)
5. Applies `labor_rules` (auto-adds labor lines per material category)
6. Creates `OrderDraft` with all `OrderLine` children

---

### `GET /orders/{lot_id}`
Get all order drafts for a lot.

**Response (200):**
```json
[
  {
    "id": "e5f6a7b8-c9d0-1234-efab-345678901234",
    "lot_id": "LOT-DAB53C3F",
    "builder_id": "Ryan Homes",
    "order_status": "draft",
    "total_amount": null,
    "lines": [
      {
        "sap_material_code": "MAT-LVP-001",
        "description": "LVP COASTAL OAK 7x48 CLICK LOCK",
        "quantity": 125.0,
        "uom": "SF",
        "category": "FLOORING"
      }
    ]
  }
]
```

---

## S3 File Structure

After a complete pipeline run, the S3 bucket contains:
```
sentra-demo/
  documents/
    2026-03-09/
      LOT-DAB53C3F/
        selection_sheet.pdf        ← uploaded PDF
        selection_sheet.json       ← extracted data (Claude Vision output)
        takeoff_sheet.pdf          ← uploaded PDF
        takeoff_sheet.json         ← extracted data (Claude Vision output)
```

---

## Database Tables Populated

| Step | Table | Description |
|------|-------|-------------|
| Upload | `documents` | 2 records (selection + takeoff), status=`uploaded` |
| Classify | `document_classifications` | Classification result per document |
| Extract | `selections` | All selection option rows from selection sheet |
| Extract | `takeoff_data` | All room/material rows from takeoff sheet |
| Extract | `documents.extracted_json` | Raw JSON stored as JSONB |
| Map | `takeoff_mapped` | Takeoff rows after substitution rules applied |
| Order | `order_drafts` | Purchase order header |
| Order | `order_lines` | Individual PO line items (materials + sundry + labor) |
| Audit | `audit_events` | Pipeline completion log with duration |
