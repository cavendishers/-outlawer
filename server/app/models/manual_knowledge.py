from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class ManualKnowledgeEvidence(Base, IdMixin, TimestampMixin):
    __tablename__ = "manual_knowledge_evidence"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), nullable=True, index=True)
    raw_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True, index=True)
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    curator_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_type: Mapped[str] = mapped_column(String(32), default="manual")
