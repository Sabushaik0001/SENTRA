# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run the API server
```bash
cd backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Run Celery worker
```bash
cd backend
celery -A app.tasks.celery_worker worker --loglevel=info
```

### Run with Docker Compose (all services)
```bash
cd backend
docker-compose up --build
```

### Database migrations
```bash
cd backend
alembic upgrade head          # apply all migrations
alembic revision --autogenerate -m "description"  # generate new migration
```

### Load SAP materials into PostgreSQL + Pinecone
```bash
cd backend
python -m scripts.load_sap_materials --file ../Materials.xlsx
```

### Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

## Architecture

SENTRA is a production-grade AI document processing system that generates purchase orders from construction documents (Selection Sheets + Take-Off Sheets).

### Pipeline Flow
```
POST /documents/upload
  → S3 upload (date-partitioned: documents/YYYY/MM/DD/LOT_ID/)
  → Celery pipeline:
      1. classify_document    (Claude via LiteLLM → document_classifications)
      2. extract_selection    (Claude via LiteLLM → selections table)
      3. extract_takeoff      (Claude via LiteLLM → takeoff_data table)
      4. run_mapping          (deterministic rules → takeoff_mapped table)
      5. generate_order       (vector search + rules → order_drafts + order_lines)
```

### Key Architectural Decisions

- **LLM calls**: All go through LiteLLM using the `CLAUDE_MODEL` config (currently Claude Sonnet 4.5 via Bedrock). Model string uses LiteLLM format: `bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0`.
- **Embeddings**: Amazon Titan Embed Text v2 via Bedrock (`amazon.titan-embed-text-v2:0`), 1024 dimensions. Called directly via boto3, not LiteLLM.
- **Vector search**: Pinecone serverless index `sap-materials`. Thresholds: >0.92 auto-map, 0.75-0.92 human review, <0.75 manual.
- **Task queue**: Celery with Redis broker. Pipeline has retry logic with exponential backoff (max 3 retries).
- **Mapping engine**: Deterministic Python code in `mapping_service.py`, NOT LLM-driven. Uses `material_substitution_matrix` table for rules (e.g., "HH6 selected → replace CARPET with LVP in GREAT_ROOM").
- **Order generation**: Combines mapped materials + SAP vector search + sundry_rules + labor_rules to produce complete PO.

### Database (PostgreSQL)
16 tables with UUID primary keys. Key tables:
- `documents` / `document_classifications` — upload tracking
- `selections` / `takeoff_data` / `takeoff_mapped` — extraction results
- `sap_materials` / `confirmed_mappings` — SAP material catalog + cached matches
- `material_substitution_matrix` / `sundry_rules` / `labor_rules` — business rules
- `order_drafts` / `order_lines` — generated purchase orders
- `audit_events` — pipeline execution logging

### Module Layout
- `app/routes/` — FastAPI endpoints (documents, extraction, mapping, orders)
- `app/services/` — business logic (s3, classification, extraction, mapping, embedding, sap_matching, order)
- `app/tasks/` — Celery workers (document_tasks orchestrates the pipeline; extraction_tasks and mapping_tasks are sub-steps)
- `app/models/` — SQLAlchemy ORM models
- `app/schemas/` — Pydantic v2 request/response schemas
- `scripts/load_sap_materials.py` — one-time script to ingest Materials.xlsx into PostgreSQL + Pinecone

### Environment
All config loaded from `.env` at project root (one level above `backend/`). See `backend/.env.example` for all variables. Key: `AWS_*`, `PINECONE_*`, `POSTGRES_*`, `REDIS_URL`, `S3_BUCKET`, `CLAUDE_MODEL`, `BEDROCK_EMBEDDING_MODEL`.
