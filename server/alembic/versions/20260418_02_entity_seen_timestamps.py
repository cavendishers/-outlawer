"""convert entity seen fields to timestamptz"""

from alembic import op
import sqlalchemy as sa

revision = "20260418_02"
down_revision = "20260418_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "entities",
        "first_seen_at",
        existing_type=sa.String(length=64),
        type_=sa.DateTime(timezone=True),
        postgresql_using="NULLIF(first_seen_at, '')::timestamptz",
        existing_nullable=True,
    )
    op.alter_column(
        "entities",
        "last_seen_at",
        existing_type=sa.String(length=64),
        type_=sa.DateTime(timezone=True),
        postgresql_using="NULLIF(last_seen_at, '')::timestamptz",
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "entities",
        "last_seen_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(length=64),
        postgresql_using="last_seen_at::text",
        existing_nullable=True,
    )
    op.alter_column(
        "entities",
        "first_seen_at",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.String(length=64),
        postgresql_using="first_seen_at::text",
        existing_nullable=True,
    )
