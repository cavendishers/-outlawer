from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class ImageGeneration(Base, IdMixin, TimestampMixin):
    __tablename__ = "image_generations"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("ai_jobs.id"), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    model_name: Mapped[str] = mapped_column(String(255), default="gpt-image-2")
    aspect_ratio: Mapped[str] = mapped_column(String(16), default="9:16")
    image_size: Mapped[str] = mapped_column(String(8), default="1K")
    reference_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    upstream_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_urls: Mapped[list[str]] = mapped_column(JSON, default=list)
    result_asset_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    raw_response_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
