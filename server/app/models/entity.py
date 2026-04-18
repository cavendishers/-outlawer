from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class Entity(Base, IdMixin, TimestampMixin):
    __tablename__ = "entities"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(32), index=True)
    canonical_name: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    alias_json: Mapped[list[str]] = mapped_column(JSON, default=list)
    normalized_name: Mapped[str] = mapped_column(String(255), index=True)
    status: Mapped[str] = mapped_column(String(32), default="active")
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EntityAlias(Base, IdMixin, TimestampMixin):
    __tablename__ = "entity_aliases"

    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    alias: Mapped[str] = mapped_column(String(255))
    normalized_alias: Mapped[str] = mapped_column(String(255), index=True)
    alias_type: Mapped[str] = mapped_column(String(32), default="extracted")


class EventEntity(Base, IdMixin, TimestampMixin):
    __tablename__ = "event_entities"

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    relation_type: Mapped[str] = mapped_column(String(64), default="participates_in")
    display_order: Mapped[int] = mapped_column(default=0)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)


class Relation(Base, IdMixin, TimestampMixin):
    __tablename__ = "relations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(36), index=True)
    relation_type: Mapped[str] = mapped_column(String(64))
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    evidence_count: Mapped[int] = mapped_column(default=1)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)


class NoteEntity(Base, IdMixin, TimestampMixin):
    __tablename__ = "note_entities"

    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    entity_id: Mapped[str] = mapped_column(ForeignKey("entities.id"), index=True)
    mention_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)


class NoteEvent(Base, IdMixin, TimestampMixin):
    __tablename__ = "note_events"

    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), index=True)
    mention_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)
