"""Widen selection/takeoff columns and add extracted_json to documents.

Revision ID: 002
Revises: 001
Create Date: 2026-03-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Documents: add extracted_json and page_count
    op.add_column("documents", sa.Column("extracted_json", postgresql.JSONB, nullable=True))
    op.add_column("documents", sa.Column("page_count", sa.Integer, nullable=True))

    # Selections: widen narrow columns
    op.alter_column("selections", "option_code", type_=sa.String(100))
    op.alter_column("selections", "category", type_=sa.String(50))
    op.alter_column("selections", "color", type_=sa.Text)
    op.alter_column("selections", "location_number", type_=sa.Text)

    # Takeoff: widen narrow columns
    op.alter_column("takeoff_data", "room_name", type_=sa.Text)
    op.alter_column("takeoff_data", "std_material", type_=sa.Text)
    op.alter_column("takeoff_data", "option_code", type_=sa.String(100))
    op.alter_column("takeoff_data", "subfloor", type_=sa.Text)

    # Takeoff mapped: widen
    op.alter_column("takeoff_mapped", "option_code", type_=sa.String(100))
    op.alter_column("takeoff_mapped", "room_name", type_=sa.Text)
    op.alter_column("takeoff_mapped", "material_type", type_=sa.Text)


def downgrade() -> None:
    op.alter_column("selections", "option_code", type_=sa.String(50))
    op.alter_column("selections", "category", type_=sa.String(10))
    op.alter_column("selections", "color", type_=sa.String(100))
    op.alter_column("selections", "location_number", type_=sa.String(50))

    op.alter_column("takeoff_data", "room_name", type_=sa.String(100))
    op.alter_column("takeoff_data", "std_material", type_=sa.String(100))
    op.alter_column("takeoff_data", "option_code", type_=sa.String(50))
    op.alter_column("takeoff_data", "subfloor", type_=sa.String(100))

    op.alter_column("takeoff_mapped", "option_code", type_=sa.String(50))
    op.alter_column("takeoff_mapped", "room_name", type_=sa.String(100))
    op.alter_column("takeoff_mapped", "material_type", type_=sa.String(100))

    op.drop_column("documents", "page_count")
    op.drop_column("documents", "extracted_json")
