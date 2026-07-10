from sqlalchemy import ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class GraphConflictDisposition(Base, IdMixin, TimestampMixin):
    __tablename__ = "graph_conflict_dispositions"
    __table_args__ = (UniqueConstraint("user_id", "conflict_id", name="uq_graph_conflict_disposition_user_conflict"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    conflict_id: Mapped[str] = mapped_column(String(255), index=True)
    disposition: Mapped[str] = mapped_column(String(32), default="open", index=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    snapshot_json: Mapped[dict] = mapped_column(JSON, default=dict)
