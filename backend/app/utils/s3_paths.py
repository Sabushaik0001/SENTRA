"""S3 key generation utilities."""

from datetime import datetime


def build_s3_key(lot_id: str, filename: str) -> str:
    """
    Build a date-partitioned S3 key.

    Format: documents/YYYY/MM/DD/{lot_id}/{filename}
    Example: documents/2026/03/10/LOT-A1B2C3D4/selection_sheet.pdf
    """
    now = datetime.utcnow()
    return f"documents/{now.year}/{now.month:02d}/{now.day:02d}/{lot_id}/{filename}"
