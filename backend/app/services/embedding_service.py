"""Amazon Titan Embed Text v2 via AWS Bedrock."""

import json
import logging

import boto3

from app.config import (
    AWS_ACCESS_KEY_ID,
    AWS_REGION,
    AWS_SECRET_ACCESS_KEY,
    BEDROCK_EMBEDDING_MODEL,
    EMBED_DIMENSIONS,
)

logger = logging.getLogger(__name__)

_bedrock_client = None


def _get_bedrock_client():
    global _bedrock_client
    if _bedrock_client is None:
        _bedrock_client = boto3.client(
            "bedrock-runtime",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
        )
    return _bedrock_client


def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text using Titan Embed v2."""
    client = _get_bedrock_client()
    body = json.dumps({
        "inputText": text,
        "dimensions": EMBED_DIMENSIONS,
        "normalize": True,
    })
    response = client.invoke_model(
        modelId=BEDROCK_EMBEDDING_MODEL,
        body=body,
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(response["body"].read())
    return result["embedding"]


def generate_embeddings_batch(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a batch of texts sequentially."""
    embeddings = []
    for text in texts:
        try:
            emb = generate_embedding(text)
            embeddings.append(emb)
        except Exception as exc:
            logger.error("Embedding failed for text (%.50s...): %s", text, exc)
            embeddings.append([])
    return embeddings
