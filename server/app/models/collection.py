from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class KnowledgeCollection(Base, IdMixin, TimestampMixin):
    __tablename__ = "knowledge_collections"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_type: Mapped[str] = mapped_column(String(32), default="topic", index=True)
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    story_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    story_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    story_style: Mapped[str] = mapped_column(String(32), default="documentary")


class KnowledgeCollectionItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "knowledge_collection_items"
    __table_args__ = (
        UniqueConstraint("collection_id", "item_type", "item_id", name="uq_collection_item_target"),
    )

    collection_id: Mapped[str] = mapped_column(ForeignKey("knowledge_collections.id", ondelete="CASCADE"), index=True)
    item_type: Mapped[str] = mapped_column(String(32), index=True)
    item_id: Mapped[str] = mapped_column(String(36), index=True)
    sort_order: Mapped[int] = mapped_column(default=0)
    curator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
