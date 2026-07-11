"""add manual evidence and knowledge collections

Revision ID: 20260711_03
Revises: 20260711_02
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_03"
down_revision = "20260711_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manual_knowledge_evidence",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("note_id", sa.String(length=36), nullable=True),
        sa.Column("raw_asset_id", sa.String(length=36), nullable=True),
        sa.Column("excerpt", sa.Text(), nullable=True),
        sa.Column("curator_note", sa.Text(), nullable=True),
        sa.Column("provenance_type", sa.String(length=32), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["note_id"], ["notes.id"]),
        sa.ForeignKeyConstraint(["raw_asset_id"], ["raw_assets.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "target_type", "target_id", "note_id", "raw_asset_id"):
        op.create_index(op.f(f"ix_manual_knowledge_evidence_{column}"), "manual_knowledge_evidence", [column])

    op.create_table(
        "knowledge_collections",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("collection_type", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("story_title", sa.String(length=255), nullable=True),
        sa.Column("story_summary", sa.Text(), nullable=True),
        sa.Column("story_body", sa.Text(), nullable=True),
        sa.Column("story_style", sa.String(length=32), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    for column in ("user_id", "collection_type", "status"):
        op.create_index(op.f(f"ix_knowledge_collections_{column}"), "knowledge_collections", [column])

    op.create_table(
        "knowledge_collection_items",
        sa.Column("collection_id", sa.String(length=36), nullable=False),
        sa.Column("item_type", sa.String(length=32), nullable=False),
        sa.Column("item_id", sa.String(length=36), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("curator_note", sa.Text(), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collection_id"], ["knowledge_collections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "item_type", "item_id", name="uq_collection_item_target"),
    )
    for column in ("collection_id", "item_type", "item_id"):
        op.create_index(op.f(f"ix_knowledge_collection_items_{column}"), "knowledge_collection_items", [column])


def downgrade() -> None:
    for column in ("item_id", "item_type", "collection_id"):
        op.drop_index(op.f(f"ix_knowledge_collection_items_{column}"), table_name="knowledge_collection_items")
    op.drop_table("knowledge_collection_items")
    for column in ("status", "collection_type", "user_id"):
        op.drop_index(op.f(f"ix_knowledge_collections_{column}"), table_name="knowledge_collections")
    op.drop_table("knowledge_collections")
    for column in ("raw_asset_id", "note_id", "target_id", "target_type", "user_id"):
        op.drop_index(op.f(f"ix_manual_knowledge_evidence_{column}"), table_name="manual_knowledge_evidence")
    op.drop_table("manual_knowledge_evidence")
