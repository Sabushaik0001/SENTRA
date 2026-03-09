"""FastAPI application entry point."""

import logging

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routes import documents, extraction, mapping, orders
from app.utils.logger import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="SENTRA — AI Purchase Order Generation",
    description="PDF document processing pipeline: upload, extract, map, generate POs.",
    version="1.0.0",
)

app.include_router(documents.router, prefix="/documents", tags=["Documents"])
app.include_router(extraction.router, prefix="/extraction", tags=["Extraction"])
app.include_router(mapping.router, prefix="/mapping", tags=["Mapping"])
app.include_router(orders.router, prefix="/orders", tags=["Orders"])


@app.get("/health")
async def health():
    return JSONResponse(content={"status": "ok"})
