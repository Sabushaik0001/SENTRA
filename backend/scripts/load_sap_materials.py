"""
Load SAP materials from Excel into PostgreSQL and Pinecone.

Usage:
    python -m scripts.load_sap_materials --file Materials.xlsx
    python -m scripts.load_sap_materials --file Materials.xlsx --workers 20
    python -m scripts.load_sap_materials --file Materials.xlsx --chunk-size 2000

Handles 240K+ rows with:
  - Full wipe of Pinecone index and PostgreSQL sap_materials table before loading
  - Chunked processing (default 1000 rows per chunk)
  - Async orchestration with concurrent embedding generation
  - Batch upserts to Pinecone (100 vectors per upsert)
"""

import argparse
import asyncio
import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
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


# ── Bedrock helpers ──────────────────────────────────────────────────────────

def _make_bedrock_client():
    return boto3.client(
        "bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID or None,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
    )


def _embed_text(client, text: str) -> list[float]:
    """Generate a single embedding using Titan Embed v2."""
    body = json.dumps({"inputText": text[:8000], "dimensions": EMBED_DIMENSIONS, "normalize": True})
    response = client.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    return json.loads(response["body"].read())["embedding"]


def _embed_single(client, sap_code: str, text: str) -> tuple[str, str, list[float]]:
    """Embed one item, returning (sap_code, text, embedding). Returns empty list on failure."""
    try:
        emb = _embed_text(client, text)
        return (sap_code, text, emb)
    except Exception as exc:
        logger.warning("Embedding failed for %s: %s", sap_code, exc)
        return (sap_code, text, [])


# ── Pinecone helpers ─────────────────────────────────────────────────────────

def get_pinecone_index(wipe: bool = False) -> "pinecone.Index":
    """Return Pinecone index handle. If wipe=True, delete all vectors first."""
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

    index = pc.Index(PINECONE_INDEX_NAME)

    if wipe:
        logger.info("Deleting ALL vectors from Pinecone index '%s' ...", PINECONE_INDEX_NAME)
        index.delete(delete_all=True)
        logger.info("Pinecone index wiped.")

    return index


def wipe_postgres():
    """Delete all rows from sap_materials table."""
    db = SessionLocal()
    try:
        count = db.query(SapMaterial).count()
        logger.info("Deleting %d rows from sap_materials table ...", count)
        db.query(SapMaterial).delete()
        db.commit()
        logger.info("PostgreSQL sap_materials table wiped.")
    finally:
        db.close()


# ── Async orchestration ─────────────────────────────────────────────────────

def _build_embed_text(desc: str, mfr: str, style: str) -> str:
    """Compose a rich text string for embedding from all available fields."""
    parts = []
    if desc and desc != "nan":
        parts.append(desc)
    if mfr and mfr != "nan":
        parts.append(f"Manufacturer: {mfr}")
    if style and style != "nan":
        parts.append(f"Style: {style}")
    return " | ".join(parts) if parts else ""


async def _embed_chunk_async(
    loop: asyncio.AbstractEventLoop,
    executor: ThreadPoolExecutor,
    chunk: list[tuple[str, str, str, str]],
) -> list[tuple[str, str, str, str, list[float]]]:
    """Embed a chunk of rows concurrently using the thread pool.

    Each item in chunk is (sap_code, desc, mfr, style).
    Returns list of (sap_code, desc, mfr, style, embedding).
    """
    client = _make_bedrock_client()

    futures = []
    for sap_code, desc, mfr, style in chunk:
        embed_text = _build_embed_text(desc, mfr, style)
        fut = loop.run_in_executor(executor, _embed_single, client, sap_code, embed_text)
        futures.append((sap_code, desc, mfr, style, fut))

    results = []
    for sap_code, desc, mfr, style, fut in futures:
        _, _, embedding = await fut
        results.append((sap_code, desc, mfr, style, embedding))

    return results


async def _upsert_pinecone_async(
    loop: asyncio.AbstractEventLoop,
    executor: ThreadPoolExecutor,
    pc_index,
    vectors: list[dict],
):
    """Upsert vectors to Pinecone in batches, off the event loop."""
    for i in range(0, len(vectors), PINECONE_BATCH_SIZE):
        batch = vectors[i : i + PINECONE_BATCH_SIZE]
        await loop.run_in_executor(executor, pc_index.upsert, batch)


def _save_to_postgres(rows: list[tuple[str, str, str, str]]):
    """Bulk insert rows into PostgreSQL sap_materials table."""
    db = SessionLocal()
    try:
        for sap_code, desc, mfr, style in rows:
            material = SapMaterial(
                sap_code=sap_code,
                description=desc,
                material_category=style,
                trade_type=mfr,
                uom="",
            )
            db.add(material)
        db.commit()
        return len(rows)
    except Exception as exc:
        logger.error("PostgreSQL batch insert failed: %s", exc)
        db.rollback()
        return 0
    finally:
        db.close()


async def process_all(
    unique_rows: list[tuple[str, str, str, str]],
    pc_index,
    workers: int,
    chunk_size: int,
):
    """Main async loop: process all rows in chunks of chunk_size."""
    loop = asyncio.get_event_loop()
    total = len(unique_rows)
    inserted_db = 0
    inserted_pc = 0
    failed = 0
    start_time = time.perf_counter()

    executor = ThreadPoolExecutor(max_workers=workers)

    for chunk_start in range(0, total, chunk_size):
        chunk = unique_rows[chunk_start : chunk_start + chunk_size]

        # 1) Generate embeddings concurrently
        embedded = await _embed_chunk_async(loop, executor, chunk)

        # 2) Prepare Pinecone vectors and DB rows
        pc_vectors = []
        db_rows = []
        for sap_code, desc, mfr, style, embedding in embedded:
            db_rows.append((sap_code, desc, mfr, style))
            if embedding:
                pc_vectors.append({
                    "id": sap_code,
                    "values": embedding,
                    "metadata": {
                        "description": desc[:500],
                        "category": style[:100] if style else "",
                        "manufacturer": mfr[:100] if mfr else "",
                    },
                })
            else:
                failed += 1

        # 3) Insert into PostgreSQL and upsert to Pinecone concurrently
        db_task = loop.run_in_executor(executor, _save_to_postgres, db_rows)
        pc_task = _upsert_pinecone_async(loop, executor, pc_index, pc_vectors)

        db_count, _ = await asyncio.gather(db_task, pc_task)
        inserted_db += db_count
        inserted_pc += len(pc_vectors)

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

    executor.shutdown(wait=True)
    elapsed = time.perf_counter() - start_time
    logger.info(
        "DONE in %.1f min | DB: %d | Pinecone: %d | Failed: %d",
        elapsed / 60, inserted_db, inserted_pc, failed,
    )


# ── Main ─────────────────────────────────────────────────────────────────────

def main(file_path: str, workers: int = 10, chunk_size: int = 1000):
    # 1) Read Excel
    logger.info("Reading Excel file: %s", file_path)
    df = pd.read_excel(file_path)
    df.columns = [c.strip() for c in df.columns]
    logger.info("Loaded %d rows. Columns: %s", len(df), list(df.columns))

    # 2) Map columns
    col_sap = next((c for c in df.columns if c.lower() in ("material", "sap_code", "material_number")), None)
    col_desc = next((c for c in df.columns if c.lower() in ("material description", "description")), None)
    col_mfr = next((c for c in df.columns if c.lower() in ("manufacturer",)), None)
    col_style = next((c for c in df.columns if c.lower() in ("style",)), None)

    if not col_sap or not col_desc:
        logger.error("Cannot find Material or Description columns. Found: %s", list(df.columns))
        return

    logger.info(
        "Column mapping: sap_code=%s, description=%s, manufacturer=%s, style=%s",
        col_sap, col_desc, col_mfr, col_style,
    )

    # 3) Prepare unique rows
    rows_to_process = []
    for _, row in df.iterrows():
        sap_code = str(row.get(col_sap, "")).strip()
        if not sap_code or sap_code == "nan":
            continue
        desc = str(row.get(col_desc, "")).strip()
        mfr = str(row.get(col_mfr, "")).strip() if col_mfr else ""
        style = str(row.get(col_style, "")).strip() if col_style else ""
        rows_to_process.append((sap_code, desc, mfr, style))

    seen = set()
    unique_rows = []
    for sap_code, desc, mfr, style in rows_to_process:
        if sap_code not in seen:
            seen.add(sap_code)
            unique_rows.append((sap_code, desc, mfr, style))

    total = len(unique_rows)
    logger.info(
        "Processing %d unique SAP codes (from %d total rows, %d duplicates removed)",
        total, len(rows_to_process), len(rows_to_process) - total,
    )

    # 4) Ensure DB tables exist
    Base.metadata.create_all(engine)

    # 5) Wipe existing data
    wipe_postgres()
    pc_index = get_pinecone_index(wipe=True)

    # 6) Process all rows async
    logger.info("Starting async processing with %d workers, chunk_size=%d ...", workers, chunk_size)
    asyncio.run(process_all(unique_rows, pc_index, workers, chunk_size))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load SAP materials from Excel into PostgreSQL + Pinecone")
    parser.add_argument("--file", required=True, help="Path to Materials.xlsx")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent embedding workers (default: 10)")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Rows per chunk (default: 1000)")
    args = parser.parse_args()
    main(args.file, workers=args.workers, chunk_size=args.chunk_size)
