"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (one level above backend/)
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

# ── AWS / Bedrock ────────────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

# ── LLM Models ───────────────────────────────────────────────────────────────
CLAUDE_MODEL: str = os.getenv(
    "CLAUDE_MODEL",
    os.getenv("BEDROCK_MODEL", "bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"),
)
BEDROCK_EMBEDDING_MODEL: str = os.getenv(
    "BEDROCK_EMBEDDING_MODEL",
    os.getenv("EMBED_MODEL", "amazon.titan-embed-text-v2:0"),
)
EMBED_DIMENSIONS: int = int(os.getenv("EMBED_DIMENSIONS", "1024"))

# ── Pinecone ─────────────────────────────────────────────────────────────────
PINECONE_API_KEY: str = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME: str = os.getenv("PINECONE_INDEX_NAME", "sap-materials")

# ── PostgreSQL ───────────────────────────────────────────────────────────────
POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_DB: str = os.getenv("POSTGRES_DB", "sentra")
POSTGRES_USER: str = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))

DATABASE_URL: str = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

# ── Redis / Celery ───────────────────────────────────────────────────────────
REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# ── S3 ───────────────────────────────────────────────────────────────────────
S3_BUCKET: str = os.getenv("S3_BUCKET", "sentra-demo")

# ── Concurrency ──────────────────────────────────────────────────────────────
MAX_CONCURRENT_EXTRACTIONS: int = int(os.getenv("MAX_CONCURRENT_EXTRACTIONS", "5"))
MAX_CONCURRENT_EMBEDDINGS: int = int(os.getenv("MAX_CONCURRENT_EMBEDDINGS", "10"))
