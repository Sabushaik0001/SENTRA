# SENTRA Database Schema

PostgreSQL 16 · 16 tables · All primary keys are UUID (uuid-ossp extension)

---

## Table of Contents

1. [documents](#1-documents)
2. [document_classifications](#2-document_classifications)
3. [prompt_templates](#3-prompt_templates)
4. [selections](#4-selections)
5. [takeoff_data](#5-takeoff_data)
6. [takeoff_mapped](#6-takeoff_mapped)
7. [sap_materials](#7-sap_materials)
8. [confirmed_mappings](#8-confirmed_mappings)
9. [material_substitution_matrix](#9-material_substitution_matrix)
10. [sundry_rules](#10-sundry_rules)
11. [labor_rules](#11-labor_rules)
12. [order_drafts](#12-order_drafts)
13. [order_lines](#13-order_lines)
14. [corrections](#14-corrections)
15. [audit_events](#15-audit_events)
16. [builder_configs](#16-builder_configs)

---

## 1. `documents`

Upload tracking for every incoming document.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `lot_id` | VARCHAR | 50 | NULL | — | Indexed |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `document_type` | VARCHAR | 50 | NULL | — | |
| `file_name` | TEXT | — | NULL | — | |
| `s3_path` | TEXT | — | NULL | — | |
| `status` | VARCHAR | 50 | NULL | `'uploaded'` | |
| `extracted_json` | JSONB | — | NULL | — | Added in migration 002 |
| `page_count` | INTEGER | — | NULL | — | Added in migration 002 |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |
| `updated_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | Updated on record change |

**Indexes:** `idx_documents_lot_id` on `(lot_id)`

---

## 2. `document_classifications`

Claude classification result for each document.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `document_id` | UUID | — | NULL | — | FK → `documents.id` ON DELETE CASCADE |
| `document_type` | VARCHAR | 50 | NULL | — | |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `format` | VARCHAR | 50 | NULL | — | |
| `confidence_score` | FLOAT8 | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Foreign Keys:** `document_id` → `documents(id)` CASCADE DELETE

---

## 3. `prompt_templates`

Versioned LLM prompt templates per builder and document type.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `document_type` | VARCHAR | 50 | NULL | — | |
| `version` | INTEGER | — | NULL | — | |
| `prompt_text` | TEXT | — | NULL | — | |
| `is_active` | BOOLEAN | — | NULL | `TRUE` | |
| `created_by` | VARCHAR | 100 | NULL | — | |
| `performance_metrics` | JSONB | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 4. `selections`

Extracted rows from Selection Sheets (one row per selected option/material).

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `lot_id` | VARCHAR | 50 | NULL | — | Indexed |
| `option_code` | VARCHAR | 100 | NULL | — | Widened from 50 in migration 002 |
| `description` | TEXT | — | NULL | — | |
| `category` | VARCHAR | 50 | NULL | — | Widened from 10 in migration 002 |
| `quantity` | INTEGER | — | NULL | — | |
| `color` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `location_number` | TEXT | — | NULL | — | Widened from VARCHAR(50) in migration 002 |
| `change_order_status` | BOOLEAN | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Indexes:** `idx_selections_lot_id` on `(lot_id)`

---

## 5. `takeoff_data`

Raw extracted rows from Take-Off Sheets (measurements per room).

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `lot_id` | VARCHAR | 50 | NULL | — | Indexed |
| `room_name` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `std_material` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `option_code` | VARCHAR | 100 | NULL | — | Widened from 50 in migration 002 |
| `subfloor` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `material_width` | FLOAT8 | — | NULL | — | |
| `cut_length` | FLOAT8 | — | NULL | — | |
| `sq_yards` | FLOAT8 | — | NULL | — | |
| `pad_sq_yards` | FLOAT8 | — | NULL | — | |
| `wood_tile_sqft` | FLOAT8 | — | NULL | — | |
| `shoe_base_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `cabinet_sides_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `toe_kick_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `nosing_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `threshold_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `t_molding_lf` | FLOAT8 | — | NULL | — | Linear feet |
| `notes` | TEXT | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Indexes:** `idx_takeoff_lot_id` on `(lot_id)`

---

## 6. `takeoff_mapped`

Post-mapping result after substitution rules have been applied to `takeoff_data`.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `lot_id` | VARCHAR | 50 | NULL | — | |
| `option_code` | VARCHAR | 100 | NULL | — | Widened from 50 in migration 002 |
| `room_name` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `material_type` | TEXT | — | NULL | — | Widened from VARCHAR(100) in migration 002 |
| `quantity` | FLOAT8 | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 7. `sap_materials`

SAP material catalog loaded from `Materials.xlsx`.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `sap_code` | VARCHAR | 50 | NULL | — | UNIQUE · Indexed |
| `description` | TEXT | — | NULL | — | |
| `material_category` | VARCHAR | 100 | NULL | — | |
| `trade_type` | VARCHAR | 100 | NULL | — | |
| `uom` | VARCHAR | 20 | NULL | — | Unit of measure |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Indexes:** `idx_sap_code` on `(sap_code)` (UNIQUE)

---

## 8. `confirmed_mappings`

Cached/approved material-name → SAP-code mappings (avoids repeated vector search).

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `material_name` | VARCHAR | 255 | NULL | — | Indexed |
| `sap_code` | VARCHAR | 50 | NULL | — | |
| `confidence_score` | FLOAT8 | — | NULL | — | |
| `approved_by` | VARCHAR | 100 | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Indexes:** `idx_confirmed_material` on `(material_name)`

---

## 9. `material_substitution_matrix`

Business rules: when an option is selected, replace one material type with another in a specific room.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `when_option_selected` | VARCHAR | 50 | NULL | — | e.g. `'HH6'` |
| `replaces_material_type` | VARCHAR | 100 | NULL | — | e.g. `'CARPET'` |
| `room` | VARCHAR | 100 | NULL | — | e.g. `'GREAT_ROOM'` |
| `with_material_type` | VARCHAR | 100 | NULL | — | e.g. `'LVP'` |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 10. `sundry_rules`

Auto-add sundry/accessory items proportional to a material quantity.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `material_category` | VARCHAR | 100 | NULL | — | |
| `sundry_item` | VARCHAR | 255 | NULL | — | |
| `quantity_ratio` | FLOAT8 | — | NULL | — | Multiplier applied to material quantity |
| `uom` | VARCHAR | 20 | NULL | — | Unit of measure |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 11. `labor_rules`

Maps a material category to its corresponding SAP labor line item.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `material_category` | VARCHAR | 100 | NULL | — | |
| `sap_labor_code` | VARCHAR | 50 | NULL | — | |
| `description` | TEXT | — | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 12. `order_drafts`

Header record for a generated purchase order draft.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `lot_id` | VARCHAR | 50 | NULL | — | |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `order_status` | VARCHAR | 50 | NULL | — | e.g. `draft`, `approved` |
| `total_amount` | FLOAT8 | — | NULL | — | |
| `created_by` | VARCHAR | 100 | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 13. `order_lines`

Individual line items belonging to an order draft.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `order_id` | UUID | — | NULL | — | FK → `order_drafts.id` ON DELETE CASCADE |
| `sap_material_code` | VARCHAR | 50 | NULL | — | |
| `description` | TEXT | — | NULL | — | |
| `quantity` | FLOAT8 | — | NULL | — | |
| `uom` | VARCHAR | 20 | NULL | — | Unit of measure |
| `category` | VARCHAR | 50 | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

**Foreign Keys:** `order_id` → `order_drafts(id)` CASCADE DELETE

---

## 14. `corrections`

Human corrections applied to extracted values (feedback loop).

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `document_id` | UUID | — | NULL | — | Soft reference to `documents.id` (no FK constraint) |
| `field_name` | VARCHAR | 100 | NULL | — | |
| `original_value` | TEXT | — | NULL | — | |
| `corrected_value` | TEXT | — | NULL | — | |
| `corrected_by` | VARCHAR | 100 | NULL | — | |
| `corrected_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 15. `audit_events`

Pipeline execution log — one row per significant pipeline event.

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `job_id` | UUID | — | NULL | — | Celery task / pipeline run ID |
| `event_type` | VARCHAR | 100 | NULL | — | |
| `user_id` | VARCHAR | 100 | NULL | — | |
| `duration_ms` | INTEGER | — | NULL | — | |
| `metadata` | JSONB | — | NULL | — | Mapped as `metadata_` in ORM to avoid Python keyword clash |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## 16. `builder_configs`

Per-builder configuration (sheet format preferences).

| Column | Type | Length | Nullable | Default | Notes |
|---|---|---|---|---|---|
| `id` | UUID | — | NOT NULL | `uuid_generate_v4()` | PK |
| `builder_id` | VARCHAR | 50 | NULL | — | |
| `builder_name` | VARCHAR | 100 | NULL | — | |
| `plan` | VARCHAR | 100 | NULL | — | |
| `selection_sheet_format` | VARCHAR | 50 | NULL | — | |
| `takeoff_sheet_format` | VARCHAR | 50 | NULL | — | |
| `created_at` | TIMESTAMP | — | NULL | `CURRENT_TIMESTAMP` | |

---

## Relationships Summary

```
documents (1) ──< document_classifications (N)   [CASCADE DELETE]
order_drafts (1) ──< order_lines (N)              [CASCADE DELETE]
corrections.document_id → documents.id            [soft reference, no FK constraint]
audit_events.job_id                               [no FK, references Celery job]
```

## Indexes Summary

| Index Name | Table | Column(s) |
|---|---|---|
| `idx_documents_lot_id` | `documents` | `lot_id` |
| `idx_selections_lot_id` | `selections` | `lot_id` |
| `idx_takeoff_lot_id` | `takeoff_data` | `lot_id` |
| `idx_sap_code` | `sap_materials` | `sap_code` (UNIQUE) |
| `idx_confirmed_material` | `confirmed_mappings` | `material_name` |

## Migration History

| Revision | Description |
|---|---|
| `001` | Initial schema — all 16 tables |
| `002` | Add `extracted_json` (JSONB) and `page_count` (INTEGER) to `documents`; widen narrow VARCHAR columns in `selections`, `takeoff_data`, `takeoff_mapped` |
