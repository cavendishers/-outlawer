from sqlalchemy import ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class CharacterCard(Base, IdMixin, TimestampMixin):
    __tablename__ = "character_cards"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="draft", index=True)
    title: Mapped[str] = mapped_column(String(255))
    card_format: Mapped[str] = mapped_column(String(32), default="sillytavern")
    card_version: Mapped[str] = mapped_column(String(32), default="chara_card_v2")
    mode: Mapped[str] = mapped_column(String(32), default="faithful")
    spec_json: Mapped[dict] = mapped_column(JSON, default=dict)
    source_snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
    avatar_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True, index=True)
    role_image_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True, index=True)
    export_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True, index=True)
