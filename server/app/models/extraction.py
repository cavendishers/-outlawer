from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class ExtractionRun(Base, IdMixin, TimestampMixin):
    __tablename__ = "extraction_runs"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    source_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True)
    raw_result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    normalized_result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="success")
    extractor_name: Mapped[str] = mapped_column(String(128), default="heuristic")
    extractor_version: Mapped[str] = mapped_column(String(32), default="v1")


class ExtractionEvidence(Base, IdMixin, TimestampMixin):
    __tablename__ = "extraction_evidence"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    source_note_id: Mapped[str] = mapped_column(ForeignKey("notes.id"), index=True)
    source_asset_id: Mapped[str | None] = mapped_column(ForeignKey("raw_assets.id"), nullable=True)
    target_type: Mapped[str] = mapped_column(String(32), index=True)
    target_id: Mapped[str] = mapped_column(String(36), index=True)
    field_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_text: Mapped[str] = mapped_column(Text)
    evidence_offset_start: Mapped[int | None] = mapped_column(nullable=True)
    evidence_offset_end: Mapped[int | None] = mapped_column(nullable=True)
    extractor_name: Mapped[str] = mapped_column(String(128), default="heuristic")
    extractor_version: Mapped[str] = mapped_column(String(32), default="v1")
    confidence_score: Mapped[float | None] = mapped_column(nullable=True)


class MergeCandidate(Base, IdMixin, TimestampMixin):
    __tablename__ = "merge_candidates"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    object_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(36), index=True)
    candidate_id: Mapped[str] = mapped_column(String(36), index=True)
    score: Mapped[float] = mapped_column()
    reason_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
