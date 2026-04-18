from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class AssetDerivative(Base, IdMixin, TimestampMixin):
    __tablename__ = "asset_derivatives"

    asset_id: Mapped[str] = mapped_column(ForeignKey("raw_assets.id"), index=True)
    derivative_type: Mapped[str] = mapped_column(String(64))
    content: Mapped[str] = mapped_column(Text)
    meta_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[str] = mapped_column(String(32), default="v1")

    asset = relationship("RawAsset", back_populates="derivatives")
