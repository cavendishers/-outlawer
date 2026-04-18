from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class ReviewAction(Base, IdMixin, TimestampMixin):
    __tablename__ = "review_actions"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    action_type: Mapped[str] = mapped_column(String(32), index=True)
    status_before: Mapped[str | None] = mapped_column(String(32), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(32), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class EntityMergeHistory(Base, IdMixin, TimestampMixin):
    __tablename__ = "entity_merge_history"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    survivor_entity_id: Mapped[str] = mapped_column(String(36), index=True)
    merged_entity_id: Mapped[str] = mapped_column(String(36), index=True)
    merge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)


class EventMergeHistory(Base, IdMixin, TimestampMixin):
    __tablename__ = "event_merge_history"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    survivor_event_id: Mapped[str] = mapped_column(String(36), index=True)
    merged_event_id: Mapped[str] = mapped_column(String(36), index=True)
    merge_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
