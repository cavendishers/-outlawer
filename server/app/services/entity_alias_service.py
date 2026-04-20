from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entity import Entity, EntityAlias
from app.utils.text import normalize_name


def list_entity_alias_rows(db: Session, entity_id: str) -> list[EntityAlias]:
    return db.scalars(
        select(EntityAlias).where(EntityAlias.entity_id == entity_id).order_by(EntityAlias.created_at.asc())
    ).all()


def list_entity_alias_values(db: Session, entity: Entity) -> list[str]:
    return _normalize_alias_values(list_entity_alias_rows(db, entity.id), entity)


def build_entity_alias_map(db: Session, entities: list[Entity]) -> dict[str, list[str]]:
    if not entities:
        return {}
    entity_by_id = {entity.id: entity for entity in entities}
    rows = db.scalars(
        select(EntityAlias)
        .where(EntityAlias.entity_id.in_(entity_by_id.keys()))
        .order_by(EntityAlias.created_at.asc())
    ).all()

    grouped_rows: dict[str, list[EntityAlias]] = defaultdict(list)
    for row in rows:
        grouped_rows[row.entity_id].append(row)

    return {
        entity_id: _normalize_alias_values(grouped_rows.get(entity_id, []), entity)
        for entity_id, entity in entity_by_id.items()
    }


def upsert_entity_alias_value(
    db: Session,
    *,
    entity: Entity,
    alias: str,
    alias_type: str,
) -> EntityAlias | None:
    cleaned = str(alias or "").strip()
    if not cleaned:
        return None
    normalized = normalize_name(cleaned)
    if not normalized:
        return None
    reserved = {normalize_name(entity.display_name), normalize_name(entity.canonical_name)}
    if normalized in reserved:
        return None

    row = db.scalar(
        select(EntityAlias).where(
            EntityAlias.entity_id == entity.id,
            EntityAlias.normalized_alias == normalized,
        )
    )
    if row is None:
        row = EntityAlias(
            entity_id=entity.id,
            alias=cleaned,
            normalized_alias=normalized,
            alias_type=alias_type,
        )
    else:
        row.alias = cleaned
        row.alias_type = alias_type or row.alias_type or "manual"
    db.add(row)
    return row


def _normalize_alias_values(rows: list[EntityAlias], entity: Entity) -> list[str]:
    seen: set[str] = set()
    values: list[str] = []
    reserved = {normalize_name(entity.display_name), normalize_name(entity.canonical_name)}
    for row in rows:
        cleaned = str(row.alias or "").strip()
        if not cleaned:
            continue
        normalized = normalize_name(cleaned)
        if not normalized or normalized in seen or normalized in reserved:
            continue
        seen.add(normalized)
        values.append(cleaned)
    return values
