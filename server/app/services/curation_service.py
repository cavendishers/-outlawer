from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_entity, serialize_event, serialize_note
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.note import Note
from app.models.review import ReviewAction
from app.models.style_view import StyleView
from app.services.graph_service import get_timeline_fragments_for_entity
from app.utils.text import normalize_name


EVENT_EDITABLE_FIELDS = {
    "title",
    "summary",
    "description",
    "event_type",
    "status",
    "start_time",
    "end_time",
    "time_precision",
    "time_text",
    "timeline_sort_time",
    "location_text",
}

ENTITY_EDITABLE_FIELDS = {
    "entity_type",
    "canonical_name",
    "display_name",
    "description",
    "status",
    "first_seen_at",
    "last_seen_at",
}


def get_entity_curation_context(db: Session, *, user_id: str, entity_id: str) -> dict[str, Any]:
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    aliases = build_entity_aliases(db, entity.id)
    related_events = build_entity_related_events(db, user_id=user_id, entity_id=entity.id)
    note_count = int(db.scalar(select(func.count()).select_from(NoteEntity).where(NoteEntity.entity_id == entity.id)) or 0)

    return {
        "entity": serialize_entity(entity),
        "aliases": aliases,
        "related_events": related_events,
        "timeline_fragments": get_timeline_fragments_for_entity(db, user_id, entity.id),
        "stats": {
            "alias_count": len(aliases),
            "related_event_count": len(related_events),
            "related_note_count": note_count,
        },
    }


def update_entity(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    status_before = entity.status

    for field in ENTITY_EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field in {"canonical_name", "display_name"}:
            setattr(entity, field, clean_required_string(value, f"{field} is required"))
        elif field in {"entity_type", "status"}:
            setattr(entity, field, clean_required_string(value, f"{field} is required"))
        elif field == "description":
            entity.description = clean_optional_string(value)
        elif field in {"first_seen_at", "last_seen_at"}:
            setattr(entity, field, parse_optional_datetime(value))

    entity.normalized_name = normalize_name(entity.canonical_name)
    compact_entity_alias_json(entity)
    db.add(entity)
    sync_entity_style_view_titles(db, entity)
    log_curation_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=entity.id,
        action_type="update_entity",
        status_before=status_before,
        status_after=entity.status,
        payload_json={field: payload[field] for field in ENTITY_EDITABLE_FIELDS if field in payload},
    )
    db.commit()
    db.refresh(entity)
    return serialize_entity(entity)


def add_entity_alias(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    alias: str,
    alias_type: str | None = None,
) -> dict[str, Any]:
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    cleaned = clean_required_string(alias, "Alias is required")
    normalized = normalize_name(cleaned)
    if not normalized:
        raise ValueError("Alias is required")

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
            alias_type=clean_optional_string(alias_type) or "manual",
        )
    else:
        row.alias = cleaned
        row.alias_type = clean_optional_string(alias_type) or row.alias_type or "manual"
    db.add(row)

    alias_list = list(entity.alias_json or [])
    if cleaned not in alias_list and cleaned not in {entity.display_name, entity.canonical_name}:
        alias_list.append(cleaned)
        entity.alias_json = alias_list
        db.add(entity)

    log_curation_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=entity.id,
        action_type="add_entity_alias",
        status_before=entity.status,
        status_after=entity.status,
        payload_json={"alias": cleaned, "alias_type": row.alias_type},
    )
    db.commit()
    db.refresh(row)
    return serialize_entity_alias(row)


def remove_entity_alias(db: Session, *, user_id: str, entity_id: str, alias_id: str) -> dict[str, Any]:
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    alias = db.get(EntityAlias, alias_id)
    if alias is None or alias.entity_id != entity.id:
        raise ValueError("Alias not found")

    removed_value = alias.alias
    db.delete(alias)
    entity.alias_json = [value for value in list(entity.alias_json or []) if normalize_name(value) != alias.normalized_alias]
    db.add(entity)
    log_curation_action(
        db,
        user_id=user_id,
        target_type="entity",
        target_id=entity.id,
        action_type="remove_entity_alias",
        status_before=entity.status,
        status_after=entity.status,
        payload_json={"alias": removed_value, "alias_id": alias_id},
    )
    db.commit()
    return {"entity_id": entity.id, "alias_id": alias_id, "status": "removed"}


def get_event_curation_context(db: Session, *, user_id: str, event_id: str) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    source_note = db.get(Note, event.source_note_id) if event.source_note_id else None
    participants = build_participants(db, event.id)
    relations = build_relations(db, user_id=user_id, event_id=event.id)

    return {
        "event": {
            **serialize_event(event),
            "source_note_title": source_note.title if source_note else None,
        },
        "participants": participants,
        "relations": relations,
        "stats": {
            "participant_count": len(participants),
            "relation_count": len(relations),
        },
    }


def update_event(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)

    for field in EVENT_EDITABLE_FIELDS:
        if field not in payload:
            continue
        value = payload[field]
        if field == "title":
            title = clean_required_string(value, "Title is required")
            event.title = title
        elif field in {"summary", "description", "event_type", "status", "time_precision", "time_text", "location_text"}:
            setattr(event, field, clean_optional_string(value))
        elif field in {"start_time", "end_time", "timeline_sort_time"}:
            setattr(event, field, parse_optional_datetime(value))

    if event.timeline_sort_time is None:
        event.timeline_sort_time = event.start_time
    if event.time_text is None and event.start_time is not None:
        event.time_text = event.start_time.date().isoformat()
    if event.summary is None and event.description:
        event.summary = event.description[:160]

    db.add(event)
    sync_timeline_items_for_event(db, event)
    sync_event_style_view_titles(db, event)
    db.commit()
    db.refresh(event)
    return {
        **serialize_event(event),
        "source_note_title": db.get(Note, event.source_note_id).title if event.source_note_id and db.get(Note, event.source_note_id) else None,
    }


def upsert_event_participant(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    entity_id: str,
    role: str | None = None,
    relation_type: str | None = None,
) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    normalized_relation_type = clean_required_string(relation_type or "participates_in", "Relation type is required")

    row = db.scalar(select(EventEntity).where(EventEntity.event_id == event.id, EventEntity.entity_id == entity.id))
    if row is None:
        next_order = int(db.scalar(select(func.coalesce(func.max(EventEntity.display_order), -1)).where(EventEntity.event_id == event.id)) or -1) + 1
        row = EventEntity(
            event_id=event.id,
            entity_id=entity.id,
            role=clean_optional_string(role),
            relation_type=normalized_relation_type,
            display_order=next_order,
        )
    else:
        row.role = clean_optional_string(role)
        row.relation_type = normalized_relation_type
    db.add(row)

    sync_participant_relation(db, user_id=user_id, entity=entity, event=event, relation_type=row.relation_type)
    db.commit()
    return {
        "event_id": event.id,
        "entity_id": entity.id,
        "role": row.role,
        "relation_type": row.relation_type,
    }


def remove_event_participant(db: Session, *, user_id: str, event_id: str, entity_id: str) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)

    rows = db.scalars(select(EventEntity).where(EventEntity.event_id == event.id, EventEntity.entity_id == entity.id)).all()
    if not rows:
        raise ValueError("Participant link not found")
    for row in rows:
        db.delete(row)

    relations = db.scalars(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_type == "entity",
            Relation.source_id == entity.id,
            Relation.target_type == "event",
            Relation.target_id == event.id,
        )
    ).all()
    for relation in relations:
        db.delete(relation)

    db.commit()
    return {"event_id": event.id, "entity_id": entity.id, "status": "removed"}


def upsert_event_relation(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    direction: str,
    related_type: str,
    related_id: str,
    relation_type: str,
) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    normalized_direction = clean_required_string(direction, "Direction is required")
    normalized_relation_type = clean_required_string(relation_type, "Relation type is required")
    if normalized_direction not in {"outgoing", "incoming"}:
        raise ValueError("Direction must be outgoing or incoming")

    related_summary = get_owned_object_summary(db, user_id=user_id, object_type=related_type, object_id=related_id)
    if related_summary is None:
        raise ValueError("Related object not found")
    if related_type == "event" and related_id == event.id:
        raise ValueError("Cannot create a self-relation")

    if normalized_direction == "outgoing":
        source_type = "event"
        source_id = event.id
        target_type = related_type
        target_id = related_id
    else:
        source_type = related_type
        source_id = related_id
        target_type = "event"
        target_id = event.id

    relation = db.scalar(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_type == source_type,
            Relation.source_id == source_id,
            Relation.relation_type == normalized_relation_type,
            Relation.target_type == target_type,
            Relation.target_id == target_id,
        )
    )
    if relation is None:
        relation = Relation(
            user_id=user_id,
            source_type=source_type,
            source_id=source_id,
            relation_type=normalized_relation_type,
            target_type=target_type,
            target_id=target_id,
            evidence_count=1,
            meta_json={"source": "curation"},
        )
    else:
        relation.meta_json = {"source": "curation"}
    db.add(relation)
    db.commit()
    db.refresh(relation)

    return serialize_relation_item(db, user_id=user_id, event_id=event.id, relation=relation)


def remove_event_relation(db: Session, *, user_id: str, event_id: str, relation_id: str) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    relation = db.get(Relation, relation_id)
    if (
        relation is None
        or relation.user_id != user_id
        or not (
            (relation.source_type == "event" and relation.source_id == event.id)
            or (relation.target_type == "event" and relation.target_id == event.id)
        )
    ):
        raise ValueError("Relation not found")

    db.delete(relation)
    db.commit()
    return {"relation_id": relation_id, "status": "removed"}


def get_owned_event(db: Session, *, user_id: str, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise ValueError("Event not found")
    return event


def get_owned_entity(db: Session, *, user_id: str, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None or entity.user_id != user_id:
        raise ValueError("Entity not found")
    return entity


def build_participants(db: Session, event_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(EventEntity).where(EventEntity.event_id == event_id).order_by(EventEntity.display_order.asc())).all()
    if not rows:
        return []
    entities = {
        entity.id: entity
        for entity in db.scalars(select(Entity).where(Entity.id.in_([row.entity_id for row in rows]))).all()
    }
    items: list[dict[str, Any]] = []
    for row in rows:
        entity = entities.get(row.entity_id)
        if entity is None:
            continue
        items.append(
            {
                "id": entity.id,
                "display_name": entity.display_name,
                "entity_type": entity.entity_type,
                "role": row.role,
                "relation_type": row.relation_type,
                "confidence_score": row.confidence_score,
            }
        )
    return items


def build_entity_aliases(db: Session, entity_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(EntityAlias).where(EntityAlias.entity_id == entity_id).order_by(EntityAlias.created_at.asc())).all()
    return [serialize_entity_alias(row) for row in rows]


def serialize_entity_alias(row: EntityAlias) -> dict[str, Any]:
    return {
        "id": row.id,
        "alias": row.alias,
        "normalized_alias": row.normalized_alias,
        "alias_type": row.alias_type,
        "created_at": isoformat(row.created_at),
    }


def build_entity_related_events(db: Session, *, user_id: str, entity_id: str) -> list[dict[str, Any]]:
    links = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity_id).order_by(EventEntity.display_order.asc())).all()
    if not links:
        return []

    event_ids = [link.event_id for link in links]
    events = {
        event.id: event
        for event in db.scalars(select(Event).where(Event.user_id == user_id, Event.id.in_(event_ids))).all()
    }
    items: list[dict[str, Any]] = []
    seen_event_ids: set[str] = set()
    for link in links:
        event = events.get(link.event_id)
        if event is None or event.id in seen_event_ids:
            continue
        seen_event_ids.add(event.id)
        items.append(
            {
                "id": event.id,
                "title": event.title,
                "summary": event.summary,
                "time_text": event.time_text,
                "event_type": event.event_type,
                "location_text": event.location_text,
                "role": link.role,
                "relation_type": link.relation_type,
            }
        )
    return items


def build_relations(db: Session, *, user_id: str, event_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Relation)
        .where(
            Relation.user_id == user_id,
            or_(
                (Relation.source_type == "event") & (Relation.source_id == event_id),
                (Relation.target_type == "event") & (Relation.target_id == event_id),
            ),
        )
        .order_by(Relation.created_at.asc())
    ).all()
    return [
        item
        for row in rows
        if (item := serialize_relation_item(db, user_id=user_id, event_id=event_id, relation=row)) is not None
    ]


def serialize_relation_item(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    relation: Relation,
) -> dict[str, Any] | None:
    if relation.source_type == "entity" and relation.target_type == "event" and relation.target_id == event_id:
        return None
    if relation.source_type == "event" and relation.target_type == "entity" and relation.source_id == event_id:
        return None

    if relation.source_type == "event" and relation.source_id == event_id:
        direction = "outgoing"
        peer = get_owned_object_summary(db, user_id=user_id, object_type=relation.target_type, object_id=relation.target_id)
    else:
        direction = "incoming"
        peer = get_owned_object_summary(db, user_id=user_id, object_type=relation.source_type, object_id=relation.source_id)

    if peer is None:
        return None

    return {
        "id": relation.id,
        "direction": direction,
        "relation_type": relation.relation_type,
        "peer": peer,
        "source_type": relation.source_type,
        "source_id": relation.source_id,
        "target_type": relation.target_type,
        "target_id": relation.target_id,
        "meta": relation.meta_json,
        "created_at": isoformat(relation.created_at),
    }


def get_owned_object_summary(
    db: Session,
    *,
    user_id: str,
    object_type: str,
    object_id: str,
) -> dict[str, Any] | None:
    if object_type == "entity":
        entity = db.get(Entity, object_id)
        if entity is None or entity.user_id != user_id:
            return None
        return {
            "id": entity.id,
            "object_type": "entity",
            "label": entity.display_name,
            "subtitle": entity.entity_type,
            "href": f"/story/entity/{entity.id}",
            "data": serialize_entity(entity),
        }
    if object_type == "event":
        event = db.get(Event, object_id)
        if event is None or event.user_id != user_id:
            return None
        return {
            "id": event.id,
            "object_type": "event",
            "label": event.title,
            "subtitle": event.time_text or event.event_type,
            "href": f"/events/{event.id}",
            "data": serialize_event(event),
        }
    if object_type == "note":
        note = db.get(Note, object_id)
        if note is None or note.user_id != user_id:
            return None
        return {
            "id": note.id,
            "object_type": "note",
            "label": note.title,
            "subtitle": note.primary_time.date().isoformat() if note.primary_time else note.status,
            "href": f"/notes/{note.id}",
            "data": serialize_note(note),
        }
    return None


def sync_timeline_items_for_event(db: Session, event: Event) -> None:
    rows = db.scalars(select(TimelineItem).where(TimelineItem.event_id == event.id)).all()
    if not rows:
        rows = [
            TimelineItem(
                user_id=event.user_id,
                event_id=event.id,
                note_id=event.source_note_id,
                title=event.title,
            )
        ]
    for row in rows:
        row.title = event.title
        row.summary = event.summary or event.description
        row.display_time = event.time_text
        row.sort_time = event.timeline_sort_time or event.start_time
        row.time_precision = event.time_precision
        db.add(row)


def sync_event_style_view_titles(db: Session, event: Event) -> None:
    rows = db.scalars(select(StyleView).where(StyleView.target_type == "event", StyleView.target_id == event.id)).all()
    for row in rows:
        row.title = f"事件档案：{event.title}"
        db.add(row)


def sync_entity_style_view_titles(db: Session, entity: Entity) -> None:
    rows = db.scalars(select(StyleView).where(StyleView.target_type == "entity", StyleView.target_id == entity.id)).all()
    for row in rows:
        row.title = f"人物档案：{entity.display_name}"
        db.add(row)


def sync_participant_relation(db: Session, *, user_id: str, entity: Entity, event: Event, relation_type: str) -> None:
    rows = db.scalars(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_type == "entity",
            Relation.source_id == entity.id,
            Relation.target_type == "event",
            Relation.target_id == event.id,
        )
    ).all()
    keeper = rows[0] if rows else None
    if keeper is None:
        keeper = Relation(
            user_id=user_id,
            source_type="entity",
            source_id=entity.id,
            relation_type=relation_type,
            target_type="event",
            target_id=event.id,
            evidence_count=1,
            meta_json={"source": "curation_participant"},
        )
    else:
        keeper.relation_type = relation_type
        keeper.meta_json = {"source": "curation_participant"}
    db.add(keeper)
    for row in rows[1:]:
        db.delete(row)


def compact_entity_alias_json(entity: Entity) -> None:
    alias_values: list[str] = []
    seen: set[str] = set()
    reserved = {normalize_name(entity.display_name), normalize_name(entity.canonical_name)}
    for alias in list(entity.alias_json or []):
        cleaned = clean_optional_string(alias)
        if cleaned is None:
            continue
        normalized = normalize_name(cleaned)
        if not normalized or normalized in seen or normalized in reserved:
            continue
        seen.add(normalized)
        alias_values.append(cleaned)
    entity.alias_json = alias_values


def log_curation_action(
    db: Session,
    *,
    user_id: str,
    target_type: str,
    target_id: str,
    action_type: str,
    status_before: str | None,
    status_after: str | None,
    payload_json: dict[str, Any],
) -> None:
    db.add(
        ReviewAction(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            action_type=action_type,
            status_before=status_before,
            status_after=status_after,
            payload_json=payload_json,
        )
    )


def clean_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    cleaned = str(value).strip()
    return cleaned or None


def clean_required_string(value: Any, message: str) -> str:
    cleaned = clean_optional_string(value)
    if cleaned is None:
        raise ValueError(message)
    return cleaned


def parse_optional_datetime(value: Any) -> datetime | None:
    cleaned = clean_optional_string(value)
    if cleaned is None:
        return None
    return datetime.fromisoformat(cleaned)
