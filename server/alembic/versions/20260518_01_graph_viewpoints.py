"""add graph viewpoints"""

from alembic import op
import sqlalchemy as sa

revision = "20260518_01"
down_revision = "20260516_03"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "graph_viewpoints",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("anchor_type", sa.String(length=32), nullable=True),
        sa.Column("anchor_id", sa.String(length=36), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=False),
        sa.Column("layout_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_graph_viewpoints_anchor_id"), "graph_viewpoints", ["anchor_id"], unique=False)
    op.create_index(op.f("ix_graph_viewpoints_anchor_type"), "graph_viewpoints", ["anchor_type"], unique=False)
    op.create_index(op.f("ix_graph_viewpoints_scope"), "graph_viewpoints", ["scope"], unique=False)
    op.create_index(op.f("ix_graph_viewpoints_user_id"), "graph_viewpoints", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_graph_viewpoints_user_id"), table_name="graph_viewpoints")
    op.drop_index(op.f("ix_graph_viewpoints_scope"), table_name="graph_viewpoints")
    op.drop_index(op.f("ix_graph_viewpoints_anchor_type"), table_name="graph_viewpoints")
    op.drop_index(op.f("ix_graph_viewpoints_anchor_id"), table_name="graph_viewpoints")
    op.drop_table("graph_viewpoints")
