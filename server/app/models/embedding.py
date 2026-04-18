from pgvector.sqlalchemy import Vector
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.mixins import IdMixin, TimestampMixin


class Embedding(Base, IdMixin, TimestampMixin):
    __tablename__ = "embeddings"

    owner_type: Mapped[str] = mapped_column(String(32), index=True)
    owner_id: Mapped[str] = mapped_column(String(36), index=True)
    vector: Mapped[list[float]] = mapped_column(Vector(8))
    model_name: Mapped[str] = mapped_column(String(64), default="heuristic-v1")
