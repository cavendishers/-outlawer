"""add character card records"""

from alembic import op
import sqlalchemy as sa

revision = "20260516_02"
down_revision = "20260516_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "character_cards",
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("source_entity_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("card_format", sa.String(length=32), nullable=False),
        sa.Column("card_version", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("spec_json", sa.JSON(), nullable=False),
        sa.Column("source_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("avatar_asset_id", sa.String(length=36), nullable=True),
        sa.Column("export_asset_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["avatar_asset_id"], ["raw_assets.id"]),
        sa.ForeignKeyConstraint(["export_asset_id"], ["raw_assets.id"]),
        sa.ForeignKeyConstraint(["source_entity_id"], ["entities.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_character_cards_avatar_asset_id"), "character_cards", ["avatar_asset_id"], unique=False)
    op.create_index(op.f("ix_character_cards_export_asset_id"), "character_cards", ["export_asset_id"], unique=False)
    op.create_index(op.f("ix_character_cards_source_entity_id"), "character_cards", ["source_entity_id"], unique=False)
    op.create_index(op.f("ix_character_cards_status"), "character_cards", ["status"], unique=False)
    op.create_index(op.f("ix_character_cards_user_id"), "character_cards", ["user_id"], unique=False)
    op.create_index(
        "ix_character_cards_user_entity_created",
        "character_cards",
        ["user_id", "source_entity_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_character_cards_user_entity_created", table_name="character_cards")
    op.drop_index(op.f("ix_character_cards_user_id"), table_name="character_cards")
    op.drop_index(op.f("ix_character_cards_status"), table_name="character_cards")
    op.drop_index(op.f("ix_character_cards_source_entity_id"), table_name="character_cards")
    op.drop_index(op.f("ix_character_cards_export_asset_id"), table_name="character_cards")
    op.drop_index(op.f("ix_character_cards_avatar_asset_id"), table_name="character_cards")
    op.drop_table("character_cards")
