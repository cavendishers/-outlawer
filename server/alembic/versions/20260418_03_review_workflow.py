"""add review workflow tables and merge candidate review fields"""

from alembic import op
import sqlalchemy as sa

revision = "20260418_03"
down_revision = "20260418_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("merge_candidates", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("merge_candidates", sa.Column("review_note", sa.Text(), nullable=True))

    op.create_table(
        "review_actions",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("target_id", sa.String(length=36), nullable=False),
        sa.Column("action_type", sa.String(length=32), nullable=False),
        sa.Column("status_before", sa.String(length=32), nullable=True),
        sa.Column("status_after", sa.String(length=32), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_actions_action_type"), "review_actions", ["action_type"], unique=False)
    op.create_index(op.f("ix_review_actions_target_id"), "review_actions", ["target_id"], unique=False)
    op.create_index(op.f("ix_review_actions_target_type"), "review_actions", ["target_type"], unique=False)
    op.create_index(op.f("ix_review_actions_user_id"), "review_actions", ["user_id"], unique=False)

    op.create_table(
        "entity_merge_history",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("survivor_entity_id", sa.String(length=36), nullable=False),
        sa.Column("merged_entity_id", sa.String(length=36), nullable=False),
        sa.Column("merge_reason", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_entity_merge_history_merged_entity_id"), "entity_merge_history", ["merged_entity_id"], unique=False)
    op.create_index(op.f("ix_entity_merge_history_survivor_entity_id"), "entity_merge_history", ["survivor_entity_id"], unique=False)
    op.create_index(op.f("ix_entity_merge_history_user_id"), "entity_merge_history", ["user_id"], unique=False)

    op.create_table(
        "event_merge_history",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("survivor_event_id", sa.String(length=36), nullable=False),
        sa.Column("merged_event_id", sa.String(length=36), nullable=False),
        sa.Column("merge_reason", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_event_merge_history_merged_event_id"), "event_merge_history", ["merged_event_id"], unique=False)
    op.create_index(op.f("ix_event_merge_history_survivor_event_id"), "event_merge_history", ["survivor_event_id"], unique=False)
    op.create_index(op.f("ix_event_merge_history_user_id"), "event_merge_history", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_event_merge_history_user_id"), table_name="event_merge_history")
    op.drop_index(op.f("ix_event_merge_history_survivor_event_id"), table_name="event_merge_history")
    op.drop_index(op.f("ix_event_merge_history_merged_event_id"), table_name="event_merge_history")
    op.drop_table("event_merge_history")

    op.drop_index(op.f("ix_entity_merge_history_user_id"), table_name="entity_merge_history")
    op.drop_index(op.f("ix_entity_merge_history_survivor_entity_id"), table_name="entity_merge_history")
    op.drop_index(op.f("ix_entity_merge_history_merged_entity_id"), table_name="entity_merge_history")
    op.drop_table("entity_merge_history")

    op.drop_index(op.f("ix_review_actions_user_id"), table_name="review_actions")
    op.drop_index(op.f("ix_review_actions_target_type"), table_name="review_actions")
    op.drop_index(op.f("ix_review_actions_target_id"), table_name="review_actions")
    op.drop_index(op.f("ix_review_actions_action_type"), table_name="review_actions")
    op.drop_table("review_actions")

    op.drop_column("merge_candidates", "review_note")
    op.drop_column("merge_candidates", "reviewed_at")
