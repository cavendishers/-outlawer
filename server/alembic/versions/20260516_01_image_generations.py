"""add image generation records"""

from alembic import op
import sqlalchemy as sa

revision = "20260516_01"
down_revision = "20260421_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "image_generations",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("job_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("aspect_ratio", sa.String(length=16), nullable=False),
        sa.Column("image_size", sa.String(length=8), nullable=False),
        sa.Column("reference_asset_ids", sa.JSON(), nullable=False),
        sa.Column("upstream_task_id", sa.String(length=255), nullable=True),
        sa.Column("result_urls", sa.JSON(), nullable=False),
        sa.Column("result_asset_ids", sa.JSON(), nullable=False),
        sa.Column("raw_response_json", sa.JSON(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["ai_jobs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_image_generations_created_at"), "image_generations", ["created_at"], unique=False)
    op.create_index(op.f("ix_image_generations_job_id"), "image_generations", ["job_id"], unique=False)
    op.create_index(op.f("ix_image_generations_status"), "image_generations", ["status"], unique=False)
    op.create_index(op.f("ix_image_generations_user_id"), "image_generations", ["user_id"], unique=False)
    op.create_index(
        "ix_image_generations_user_status_created",
        "image_generations",
        ["user_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_image_generations_user_status_created", table_name="image_generations")
    op.drop_index(op.f("ix_image_generations_user_id"), table_name="image_generations")
    op.drop_index(op.f("ix_image_generations_status"), table_name="image_generations")
    op.drop_index(op.f("ix_image_generations_job_id"), table_name="image_generations")
    op.drop_index(op.f("ix_image_generations_created_at"), table_name="image_generations")
    op.drop_table("image_generations")
