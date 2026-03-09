"""
Load SAP materials from Excel into PostgreSQL and Pinecone.

Usage:
    python -m scripts.load_sap_materials --file Materials.xlsx
    python -m scripts.load_sap_materials --file Materials.xlsx --skip-existing
    python -m scripts.load_sap_materials --file Materials.xlsx --workers 20

Handles 240K+ rows with concurrent embedding generation and batch upserts.
"""

import argparse
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import boto3
import pandas as pd
from pinecone import Pinecone, ServerlessSpec

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    BEDROCK_EMBEDDING_MODEL,
    EMBED_DIMENSIONS,
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
)
from app.database import Base, SessionLocal, engine
from app.models.sap_materials import SapMaterial

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(message)s")
logger = logging.getLogger(__name__)

PINECONE_BATCH_SIZE = 100
DB_COMMIT_BATCH = 500


def get_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
    )


def embed_text(client, text: str) -> list:
    """Generate a single embedding using Titan Embed v2."""
    body = json.dumps({"inputText": text[:8000], "dimensions": EMBED_DIMENSIONS, "normalize": True})
    response = client.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


def embed_batch(client, items: list) -> list:
    """Embed a batch of (sap_code, text) tuples. Returns list of (sap_code, text, embedding)."""
    results = []
    for sap_code, text in items:
        try:
            emb = embed_text(client, text)
            results.append((sap_code, text, emb))
        except Exception as exc:
            logger.warning("Embedding failed for %s: %s", sap_code, exc)
            results.append((sap_code, text, []))
    return results


def ensure_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        logger.info("Creating Pinecone index '%s' (dim=%d)", PINECONE_INDEX_NAME, EMBED_DIMENSIONS)
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBED_DIMENSIONS,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=AWS_REGION),
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status["ready"]:
            time.sleep(1)
    return pc.Index(PINECONE_INDEX_NAME)


def main(file_path: str, workers: int = 10, skip_existing: bool = False):
    # Read Excel
    logger.info("Reading Excel file: %s", file_path)
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    logger.info("Loaded %d rows. Columns: %s", len(df), list(df.columns))

    # Map columns — adapt to actual Excel: Material, Material Description, Manufacturer, Style
    col_sap = next((c for c in df.columns if c.lower() in ("material", "sap_code", "material_number")), None)
    col_desc = next((c for c in df.columns if c.lower() in ("material description", "description")), None)
    col_mfr = next((c for c in df.columns if c.lower() in ("manufacturer",)), None)
    col_style = next((c for c in df.columns if c.lower() in ("style",)), None)

    if not col_sap or not col_desc:
        logger.error("Cannot find Material or Description columns. Found: %s", list(df.columns))
        return

    logger.info("Column mapping: sap_code=%s, description=%s, manufacturer=%s, style=%s",
                col_sap, col_desc, col_mfr, col_style)

    # Ensure DB tables exist
    Base.metadata.create_all(engine)

    # Get existing SAP codes to skip duplicates
    db = SessionLocal()
    existing_codes = set()
    if skip_existing:
        existing_codes = {r[0] for r in db.query(SapMaterial.sap_code).all()}
        logger.info("Found %d existing SAP codes in DB — will skip", len(existing_codes))
    db.close()

    # Prepare rows
    rows_to_process = []
    for _, row in df.iterrows():
        sap_code = str(row.get(col_sap, "")).strip()
        if not sap_code or sap_code == "nan":
            continue
        if sap_code in existing_codes:
            continue
        desc = str(row.get(col_desc, "")).strip()
        mfr = str(row.get(col_mfr, "")).strip() if col_mfr else ""
        style = str(row.get(col_style, "")).strip() if col_style else ""
        rows_to_process.append((sap_code, desc, mfr, style))

    # Deduplicate by sap_code (keep first occurrence)
    seen = set()
    unique_rows = []
    for sap_code, desc, mfr, style in rows_to_process:
        if sap_code not in seen:
            seen.add(sap_code)
            unique_rows.append((sap_code, desc, mfr, style))

    total = len(unique_rows)
    logger.info("Processing %d unique SAP codes (from %d total rows, %d duplicates removed)",
                total, len(rows_to_process), len(rows_to_process) - total)

    # Setup Pinecone
    pc_index = ensure_pinecone_index()

    # Process in chunks using thread pool for concurrent embeddings
    chunk_size = workers * 5  # each worker gets ~5 items per batch
    inserted_db = 0
    inserted_pc = 0
    failed = 0
    start_time = time.perf_counter()

    for chunk_start in range(0, total, chunk_size):
        chunk = unique_rows[chunk_start:chunk_start + chunk_size]

        # Split chunk across workers
        worker_batches = []
        per_worker = max(1, len(chunk) // workers)
        for i in range(0, len(chunk), per_worker):
            batch = [(sap, desc) for sap, desc, _, _ in chunk[i:i + per_worker]]
            worker_batches.append(batch)

        # Concurrent embedding generation
        all_embedded = []
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(embed_batch, get_bedrock_client(), batch): batch for batch in worker_batches}
            for future in as_completed(futures):
                try:
                    all_embedded.extend(future.result())
                except Exception as exc:
                    logger.error("Worker failed: %s", exc)
                    failed += len(futures[future])

        # Build lookup for metadata
        meta_lookup = {sap: (desc, mfr, style) for sap, desc, mfr, style in chunk}

        # Upsert into PostgreSQL + Pinecone
        db = SessionLocal()
        pc_batch = []
        try:
            for sap_code, text, embedding in all_embedded:
                desc, mfr, style = meta_lookup.get(sap_code, (text, "", ""))

                # PostgreSQL — upsert (insert or update)
                existing = db.query(SapMaterial).filter(SapMaterial.sap_code == sap_code).first()
                if existing:
                    existing.description = desc
                    existing.material_category = style
                    existing.trade_type = mfr
                else:
                    material = SapMaterial(
                        sap_code=sap_code,
                        description=desc,
                        material_category=style,
                        trade_type=mfr,
                        uom="",
                    )
                    db.add(material)
                inserted_db += 1

                # Pinecone
                if embedding:
                    pc_batch.append({
                        "id": sap_code,
                        "values": embedding,
                        "metadata": {
                            "description": desc[:500],
                            "category": style[:100] if style else "",
                            "manufacturer": mfr[:100] if mfr else "",
                        },
                    })

                    if len(pc_batch) >= PINECONE_BATCH_SIZE:
                        pc_index.upsert(vectors=pc_batch)
                        inserted_pc += len(pc_batch)
                        pc_batch = []

            db.commit()

            # Flush remaining Pinecone batch
            if pc_batch:
                pc_index.upsert(vectors=pc_batch)
                inserted_pc += len(pc_batch)
                pc_batch = []

        except Exception as exc:
            logger.error("Batch failed: %s", exc)
            db.rollback()
            failed += len(chunk)
        finally:
            db.close()

        # Progress
        processed = chunk_start + len(chunk)
        elapsed = time.perf_counter() - start_time
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (total - processed) / rate if rate > 0 else 0
        logger.info(
            "Progress: %d/%d (%.1f%%) | DB: %d | Pinecone: %d | Failed: %d | %.1f rows/sec | ETA: %.0f min",
            processed, total, 100 * processed / total,
            inserted_db, inserted_pc, failed, rate, remaining / 60,
        )

    elapsed = time.perf_counter() - start_time
    logger.info("DONE in %.1f min | DB: %d | Pinecone: %d | Failed: %d", elapsed / 60, inserted_db, inserted_pc, failed)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load SAP materials from Excel")
    parser.add_argument("--file", required=True, help="Path to Materials.xlsx")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent embedding workers (default: 10)")
    parser.add_argument("--skip-existing", action="store_true", help="Skip SAP codes already in the DB")
    args = parser.parse_args()
    main(args.file, workers=args.workers, skip_existing=args.skip_existing)
