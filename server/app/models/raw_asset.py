from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class RawAsset(Base, IdMixin, TimestampMixin):
    __tablename__ = "raw_assets"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(32), index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="manual")
    title: Mapped[str] = mapped_column(String(255))
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    bucket_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="uploaded", index=True)

    user = relationship("User", back_populates="assets")
    derivatives = relationship("AssetDerivative", back_populates="asset", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="asset")
