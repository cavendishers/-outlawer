from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class GraphViewpoint(Base, IdMixin, TimestampMixin):
    __tablename__ = "graph_viewpoints"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    scope: Mapped[str] = mapped_column(String(64), default="overview", index=True)
    anchor_type: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    anchor_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    filters_json: Mapped[dict] = mapped_column(JSON, default=dict)
    layout_json: Mapped[dict] = mapped_column(JSON, default=dict)
