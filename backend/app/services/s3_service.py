"""AWS S3 upload and download operations."""

import logging

import boto3
from botocore.exceptions import ClientError

from app.config import AWS_ACCESS_KEY_ID, AWS_REGION, AWS_SECRET_ACCESS_KEY, S3_BUCKET

logger = logging.getLogger(__name__)

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            aws_access_key_id=AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY or None,
        )
    return _s3_client


def upload_file_to_s3(file_bytes: bytes, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """Upload bytes to S3. Returns the full s3 path."""
    client = _get_s3_client()
    client.put_object(
        Bucket=S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    s3_path = f"s3://{S3_BUCKET}/{s3_key}"
    logger.info("Uploaded to %s", s3_path)
    return s3_path


def download_file_from_s3(s3_key: str) -> bytes:
    """Download a file from S3. Returns raw bytes."""
    client = _get_s3_client()
    try:
        response = client.get_object(Bucket=S3_BUCKET, Key=s3_key)
        return response["Body"].read()
    except ClientError as e:
        logger.error("S3 download failed for key %s: %s", s3_key, e)
        raise


def generate_presigned_url(s3_key: str, expires_in: int = 3600) -> str:
    """Generate a presigned URL for temporary access."""
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": S3_BUCKET, "Key": s3_key},
        ExpiresIn=expires_in,
    )
