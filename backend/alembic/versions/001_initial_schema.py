"""Initial schema — all tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-09
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE SCHEMA IF NOT EXISTS sentra')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    op.create_table(
        "documents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lot_id", sa.String(50)),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("document_type", sa.String(50)),
        sa.Column("file_name", sa.Text),
        sa.Column("s3_path", sa.Text),
        sa.Column("status", sa.String(50), server_default="uploaded"),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )
    op.create_index("idx_documents_lot_id", "documents", ["lot_id"], schema="sentra")

    op.create_table(
        "document_classifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sentra.documents.id", ondelete="CASCADE")),
        sa.Column("document_type", sa.String(50)),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("format", sa.String(50)),
        sa.Column("confidence_score", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("document_type", sa.String(50)),
        sa.Column("version", sa.Integer),
        sa.Column("prompt_text", sa.Text),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("TRUE")),
        sa.Column("created_by", sa.String(100)),
        sa.Column("performance_metrics", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "selections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lot_id", sa.String(50)),
        sa.Column("option_code", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("category", sa.String(10)),
        sa.Column("quantity", sa.Integer),
        sa.Column("color", sa.String(100)),
        sa.Column("location_number", sa.String(50)),
        sa.Column("change_order_status", sa.Boolean),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )
    op.create_index("idx_selections_lot_id", "selections", ["lot_id"], schema="sentra")

    op.create_table(
        "takeoff_data",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lot_id", sa.String(50)),
        sa.Column("room_name", sa.String(100)),
        sa.Column("std_material", sa.String(100)),
        sa.Column("option_code", sa.String(50)),
        sa.Column("subfloor", sa.String(100)),
        sa.Column("material_width", sa.Float),
        sa.Column("cut_length", sa.Float),
        sa.Column("sq_yards", sa.Float),
        sa.Column("pad_sq_yards", sa.Float),
        sa.Column("wood_tile_sqft", sa.Float),
        sa.Column("shoe_base_lf", sa.Float),
        sa.Column("cabinet_sides_lf", sa.Float),
        sa.Column("toe_kick_lf", sa.Float),
        sa.Column("nosing_lf", sa.Float),
        sa.Column("threshold_lf", sa.Float),
        sa.Column("t_molding_lf", sa.Float),
        sa.Column("notes", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )
    op.create_index("idx_takeoff_lot_id", "takeoff_data", ["lot_id"], schema="sentra")

    op.create_table(
        "takeoff_mapped",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lot_id", sa.String(50)),
        sa.Column("option_code", sa.String(50)),
        sa.Column("room_name", sa.String(100)),
        sa.Column("material_type", sa.String(100)),
        sa.Column("quantity", sa.Float),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "material_substitution_matrix",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("when_option_selected", sa.String(50)),
        sa.Column("replaces_material_type", sa.String(100)),
        sa.Column("room", sa.String(100)),
        sa.Column("with_material_type", sa.String(100)),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "sap_materials",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("sap_code", sa.String(50), unique=True),
        sa.Column("description", sa.Text),
        sa.Column("material_category", sa.String(100)),
        sa.Column("trade_type", sa.String(100)),
        sa.Column("uom", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )
    op.create_index("idx_sap_code", "sap_materials", ["sap_code"], schema="sentra")

    op.create_table(
        "confirmed_mappings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("material_name", sa.String(255)),
        sa.Column("sap_code", sa.String(50)),
        sa.Column("confidence_score", sa.Float),
        sa.Column("approved_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )
    op.create_index("idx_confirmed_material", "confirmed_mappings", ["material_name"], schema="sentra")

    op.create_table(
        "sundry_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("material_category", sa.String(100)),
        sa.Column("sundry_item", sa.String(255)),
        sa.Column("quantity_ratio", sa.Float),
        sa.Column("uom", sa.String(20)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "labor_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("material_category", sa.String(100)),
        sa.Column("sap_labor_code", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "order_drafts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("lot_id", sa.String(50)),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("order_status", sa.String(50)),
        sa.Column("total_amount", sa.Float),
        sa.Column("created_by", sa.String(100)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sentra.order_drafts.id", ondelete="CASCADE")),
        sa.Column("sap_material_code", sa.String(50)),
        sa.Column("description", sa.Text),
        sa.Column("quantity", sa.Float),
        sa.Column("uom", sa.String(20)),
        sa.Column("category", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "corrections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("document_id", postgresql.UUID(as_uuid=True)),
        sa.Column("field_name", sa.String(100)),
        sa.Column("original_value", sa.Text),
        sa.Column("corrected_value", sa.Text),
        sa.Column("corrected_by", sa.String(100)),
        sa.Column("corrected_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("job_id", postgresql.UUID(as_uuid=True)),
        sa.Column("event_type", sa.String(100)),
        sa.Column("user_id", sa.String(100)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("metadata", postgresql.JSONB),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )

    op.create_table(
        "builder_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("builder_id", sa.String(50)),
        sa.Column("builder_name", sa.String(100)),
        sa.Column("plan", sa.String(100)),
        sa.Column("selection_sheet_format", sa.String(50)),
        sa.Column("takeoff_sheet_format", sa.String(50)),
        sa.Column("created_at", sa.DateTime, server_default=sa.text("CURRENT_TIMESTAMP")),
        schema="sentra",
    )


def downgrade() -> None:
    for table in [
        "builder_configs", "audit_events", "corrections", "order_lines",
        "order_drafts", "labor_rules", "sundry_rules", "confirmed_mappings",
        "sap_materials", "material_substitution_matrix", "takeoff_mapped",
        "takeoff_data", "selections", "prompt_templates",
        "document_classifications", "documents",
    ]:
        op.drop_table(table, schema="sentra")
    op.execute("DROP SCHEMA IF EXISTS sentra")
