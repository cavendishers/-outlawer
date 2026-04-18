from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class Event(Base, IdMixin, TimestampMixin):
    __tablename__ = "events"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    source_note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), nullable=True, index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    time_precision: Mapped[str] = mapped_column(String(32), default="unknown")
    time_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timeline_sort_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    location_text: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)


class TimelineItem(Base, IdMixin, TimestampMixin):
    __tablename__ = "timeline_items"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    event_id: Mapped[str | None] = mapped_column(ForeignKey("events.id"), nullable=True, index=True)
    note_id: Mapped[str | None] = mapped_column(ForeignKey("notes.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(255))
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_time: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sort_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    time_precision: Mapped[str] = mapped_column(String(32), default="unknown")
    importance_score: Mapped[float | None] = mapped_column(nullable=True)
