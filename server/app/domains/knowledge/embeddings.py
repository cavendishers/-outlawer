from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.embedding import Embedding


def upsert_embedding(
    db: Session,
    *,
    owner_type: str,
    owner_id: str,
    vector: list[float],
    model_name: str,
) -> Embedding:
    row = db.scalar(
        select(Embedding).where(
            Embedding.owner_type == owner_type,
            Embedding.owner_id == owner_id,
            Embedding.model_name == model_name,
        )
    )
    if row is None:
        row = Embedding(
            owner_type=owner_type,
            owner_id=owner_id,
            vector=vector,
            model_name=model_name,
        )
    else:
        row.vector = vector
        row.model_name = model_name
    db.add(row)
    return row
