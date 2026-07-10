"""add graph conflict dispositions

Revision ID: 20260711_02
Revises: 20260711_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260711_02"
down_revision = "20260711_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_conflict_dispositions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("conflict_id", sa.String(length=255), nullable=False),
        sa.Column("disposition", sa.String(length=32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "conflict_id", name="uq_graph_conflict_disposition_user_conflict"),
    )
    op.create_index(
        op.f("ix_graph_conflict_dispositions_conflict_id"),
        "graph_conflict_dispositions",
        ["conflict_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graph_conflict_dispositions_disposition"),
        "graph_conflict_dispositions",
        ["disposition"],
        unique=False,
    )
    op.create_index(
        op.f("ix_graph_conflict_dispositions_user_id"),
        "graph_conflict_dispositions",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_graph_conflict_dispositions_user_id"), table_name="graph_conflict_dispositions")
    op.drop_index(op.f("ix_graph_conflict_dispositions_disposition"), table_name="graph_conflict_dispositions")
    op.drop_index(op.f("ix_graph_conflict_dispositions_conflict_id"), table_name="graph_conflict_dispositions")
    op.drop_table("graph_conflict_dispositions")
