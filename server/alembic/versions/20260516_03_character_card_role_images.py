"""add generated role images to character cards"""

from alembic import op
import sqlalchemy as sa

revision = "20260516_03"
down_revision = "20260516_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("character_cards", sa.Column("role_image_asset_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_character_cards_role_image_asset_id_raw_assets",
        "character_cards",
        "raw_assets",
        ["role_image_asset_id"],
        ["id"],
    )
    op.create_index(op.f("ix_character_cards_role_image_asset_id"), "character_cards", ["role_image_asset_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_character_cards_role_image_asset_id"), table_name="character_cards")
    op.drop_constraint("fk_character_cards_role_image_asset_id_raw_assets", "character_cards", type_="foreignkey")
    op.drop_column("character_cards", "role_image_asset_id")
