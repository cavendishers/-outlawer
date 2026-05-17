from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_entity, serialize_event, serialize_note
from app.domains.retrieval.graph_query import get_timeline_fragments_for_entity
from app.domains.retrieval.entity_query import list_related_events_for_entity
from app.domains.retrieval.event_query import list_event_participants
from app.models.entity import Entity, EntityAlias, EventEntity, NoteEntity, Relation
from app.models.event import Event, TimelineItem
from app.models.note import Note
from app.models.review import ReviewAction
from app.models.style_view import StyleView
from app.domains.knowledge.aliases import list_entity_alias_rows, list_entity_alias_values, upsert_entity_alias_value
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
    related_events = list_related_events_for_entity(db, user_id=user_id, entity_id=entity.id)
    relations = build_relations_for_owner(db, user_id=user_id, owner_type="entity", owner_id=entity.id)
    note_count = int(db.scalar(select(func.count()).select_from(NoteEntity).where(NoteEntity.entity_id == entity.id)) or 0)

    return {
        "entity": serialize_entity(entity, aliases=list_entity_alias_values(db, entity)),
        "aliases": aliases,
        "related_events": related_events,
        "relations": relations,
        "timeline_fragments": get_timeline_fragments_for_entity(db, user_id, entity.id),
        "stats": {
            "alias_count": len(aliases),
            "related_event_count": len(related_events),
            "related_note_count": note_count,
            "relation_count": len(relations),
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
    return serialize_entity(entity, aliases=list_entity_alias_values(db, entity))


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

    row = upsert_entity_alias_value(
        db,
        entity=entity,
        alias=cleaned,
        alias_type=clean_optional_string(alias_type) or "manual",
    )
    if row is None:
        raise ValueError("Alias conflicts with current canonical or display name")

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
    participants = list_event_participants(db, event.id)
    relations = build_relations_for_owner(db, user_id=user_id, owner_type="event", owner_id=event.id)

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
    entity_id: str | None,
    entity_name: str | None = None,
    entity_type: str | None = None,
    role: str | None = None,
    relation_type: str | None = None,
) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    entity, created_entity = resolve_event_participant_entity(
        db,
        user_id=user_id,
        entity_id=entity_id,
        entity_name=entity_name,
        entity_type=entity_type,
    )
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

    apply_manual_participant_profile_defaults(
        db,
        user_id=user_id,
        event=event,
        entity=entity,
        role=row.role,
        relation_type=row.relation_type,
        created_entity=created_entity,
    )

    db.commit()
    return {
        "event_id": event.id,
        "entity_id": entity.id,
        "role": row.role,
        "relation_type": row.relation_type,
    }


def resolve_event_participant_entity(
    db: Session,
    *,
    user_id: str,
    entity_id: str | None,
    entity_name: str | None,
    entity_type: str | None,
) -> tuple[Entity, bool]:
    if entity_id:
        return get_owned_entity(db, user_id=user_id, entity_id=entity_id), False

    cleaned_name = clean_required_string(entity_name, "Participant entity name is required")
    cleaned_type = clean_optional_string(entity_type) or "person"
    normalized = normalize_name(cleaned_name)
    if not normalized:
        raise ValueError("Participant entity name is required")

    existing = db.scalar(
        select(Entity).where(
            Entity.user_id == user_id,
            Entity.normalized_name == normalized,
        )
    )
    if existing:
        return existing, False

    entity = Entity(
        user_id=user_id,
        entity_type=cleaned_type,
        canonical_name=cleaned_name,
        display_name=cleaned_name,
        description=None,
        alias_json=[],
        normalized_name=normalized,
        status="active",
        confidence_score=1.0,
    )
    db.add(entity)
    db.flush()
    return entity, True


def apply_manual_participant_profile_defaults(
    db: Session,
    *,
    user_id: str,
    event: Event,
    entity: Entity,
    role: str | None,
    relation_type: str,
    created_entity: bool,
) -> None:
    event_time = event.timeline_sort_time or event.start_time
    if event_time:
        if entity.first_seen_at is None or event_time < entity.first_seen_at:
            entity.first_seen_at = event_time
        if entity.last_seen_at is None or event_time > entity.last_seen_at:
            entity.last_seen_at = event_time

    role_text = display_role_text(role=role, relation_type=relation_type)
    if not entity.description:
        entity.description = f"手动加入《{event.title}》的{role_text}。"

    db.add(entity)
    upsert_manual_participant_style_view(db, user_id=user_id, event=event, entity=entity, role_text=role_text)


def upsert_manual_participant_style_view(
    db: Session,
    *,
    user_id: str,
    event: Event,
    entity: Entity,
    role_text: str,
) -> None:
    title = f"{entity.display_name} / {role_text}"
    content = (
        f"{entity.display_name}被手动纳入《{event.title}》的事件链。"
        f"TA在这段记录中的身份是{role_text}，后续档案会随着更多卷宗继续补全。"
    )
    story = db.scalar(
        select(StyleView).where(
            StyleView.user_id == user_id,
            StyleView.target_type == "entity",
            StyleView.target_id == entity.id,
            StyleView.style_type == "chunibyo",
        )
    )
    if story:
        if not story.content or "手动纳入" in story.content:
            story.title = title
            story.content = content
            db.add(story)
        return

    db.add(
        StyleView(
            user_id=user_id,
            target_type="entity",
            target_id=entity.id,
            style_type="chunibyo",
            title=title,
            content=content,
        )
    )


def display_role_text(*, role: str | None, relation_type: str | None) -> str:
    if role:
        return role
    if relation_type in {None, "", "participates_in"}:
        return "参与者"
    return relation_type


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
        if is_hidden_participant_relation(relation):
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
    get_owned_event(db, user_id=user_id, event_id=event_id)
    return upsert_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="event",
        owner_id=event_id,
        direction=direction,
        related_type=related_type,
        related_id=related_id,
        relation_type=relation_type,
    )


def update_event_relation(
    db: Session,
    *,
    user_id: str,
    event_id: str,
    relation_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    get_owned_event(db, user_id=user_id, event_id=event_id)
    return update_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="event",
        owner_id=event_id,
        relation_id=relation_id,
        payload=payload,
    )


def remove_event_relation(db: Session, *, user_id: str, event_id: str, relation_id: str) -> dict[str, Any]:
    get_owned_event(db, user_id=user_id, event_id=event_id)
    return remove_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="event",
        owner_id=event_id,
        relation_id=relation_id,
    )


def upsert_entity_relation(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    direction: str,
    related_type: str,
    related_id: str,
    relation_type: str,
) -> dict[str, Any]:
    get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    return upsert_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="entity",
        owner_id=entity_id,
        direction=direction,
        related_type=related_type,
        related_id=related_id,
        relation_type=relation_type,
    )


def update_entity_relation(
    db: Session,
    *,
    user_id: str,
    entity_id: str,
    relation_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    return update_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="entity",
        owner_id=entity_id,
        relation_id=relation_id,
        payload=payload,
    )


def remove_entity_relation(db: Session, *, user_id: str, entity_id: str, relation_id: str) -> dict[str, Any]:
    get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    return remove_relation_for_owner(
        db,
        user_id=user_id,
        owner_type="entity",
        owner_id=entity_id,
        relation_id=relation_id,
    )


def upsert_relation_for_owner(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    direction: str,
    related_type: str,
    related_id: str,
    relation_type: str,
) -> dict[str, Any]:
    relation_shape = resolve_relation_shape(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        direction=direction,
        related_type=related_type,
        related_id=related_id,
        relation_type=relation_type,
    )

    relation = db.scalar(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_type == relation_shape["source_type"],
            Relation.source_id == relation_shape["source_id"],
            Relation.relation_type == relation_shape["relation_type"],
            Relation.target_type == relation_shape["target_type"],
            Relation.target_id == relation_shape["target_id"],
        )
    )
    if relation is None:
        relation = Relation(
            user_id=user_id,
            source_type=relation_shape["source_type"],
            source_id=relation_shape["source_id"],
            relation_type=relation_shape["relation_type"],
            target_type=relation_shape["target_type"],
            target_id=relation_shape["target_id"],
            evidence_count=1,
            meta_json={"source": "curation"},
        )
    else:
        relation.meta_json = {"source": "curation"}
    db.add(relation)
    db.flush()
    log_curation_action(
        db,
        user_id=user_id,
        target_type="relation",
        target_id=relation.id,
        action_type="add_relation",
        status_before=None,
        status_after=relation.relation_type,
        payload_json={"owner_type": owner_type, "owner_id": owner_id, **relation_shape},
    )
    db.commit()
    db.refresh(relation)
    return serialize_relation_item_for_owner(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        relation=relation,
    ) or {"id": relation.id}


def update_relation_for_owner(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    relation_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    relation = get_owned_relation_for_owner(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        relation_id=relation_id,
    )
    current_shape = relation_shape_for_owner(owner_type=owner_type, owner_id=owner_id, relation=relation)
    next_shape = resolve_relation_shape(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        direction=payload.get("direction") or current_shape["direction"],
        related_type=payload.get("related_type") or current_shape["related_type"],
        related_id=payload.get("related_id") or current_shape["related_id"],
        relation_type=payload.get("relation_type") or relation.relation_type,
    )

    previous_relation_type = relation.relation_type
    relation.source_type = next_shape["source_type"]
    relation.source_id = next_shape["source_id"]
    relation.target_type = next_shape["target_type"]
    relation.target_id = next_shape["target_id"]
    relation.relation_type = next_shape["relation_type"]
    relation.meta_json = {"source": "curation"}
    db.add(relation)
    log_curation_action(
        db,
        user_id=user_id,
        target_type="relation",
        target_id=relation.id,
        action_type="update_relation",
        status_before=previous_relation_type,
        status_after=relation.relation_type,
        payload_json={
            "owner_type": owner_type,
            "owner_id": owner_id,
            "previous": current_shape,
            "next": next_shape,
        },
    )
    db.commit()
    db.refresh(relation)
    return serialize_relation_item_for_owner(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        relation=relation,
    ) or {"id": relation.id}


def remove_relation_for_owner(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    relation_id: str,
) -> dict[str, Any]:
    relation = get_owned_relation_for_owner(
        db,
        user_id=user_id,
        owner_type=owner_type,
        owner_id=owner_id,
        relation_id=relation_id,
    )
    log_curation_action(
        db,
        user_id=user_id,
        target_type="relation",
        target_id=relation.id,
        action_type="remove_relation",
        status_before=relation.relation_type,
        status_after=None,
        payload_json={"owner_type": owner_type, "owner_id": owner_id},
    )
    db.delete(relation)
    db.commit()
    return {"relation_id": relation_id, "status": "removed"}


def resolve_relation_shape(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    direction: str,
    related_type: str,
    related_id: str,
    relation_type: str,
) -> dict[str, str]:
    normalized_direction = clean_required_string(direction, "Direction is required")
    normalized_related_type = clean_required_string(related_type, "Related type is required")
    normalized_related_id = clean_required_string(related_id, "Related object is required")
    normalized_relation_type = clean_required_string(relation_type, "Relation type is required")
    if normalized_direction not in {"outgoing", "incoming"}:
        raise ValueError("Direction must be outgoing or incoming")
    if normalized_related_type not in {"entity", "event", "note"}:
        raise ValueError("Related type must be entity, event, or note")
    if normalized_related_type == owner_type and normalized_related_id == owner_id:
        raise ValueError("Cannot create a self-relation")
    if get_owned_object_summary(db, user_id=user_id, object_type=normalized_related_type, object_id=normalized_related_id) is None:
        raise ValueError("Related object not found")

    if normalized_direction == "outgoing":
        return {
            "direction": normalized_direction,
            "related_type": normalized_related_type,
            "related_id": normalized_related_id,
            "relation_type": normalized_relation_type,
            "source_type": owner_type,
            "source_id": owner_id,
            "target_type": normalized_related_type,
            "target_id": normalized_related_id,
        }
    return {
        "direction": normalized_direction,
        "related_type": normalized_related_type,
        "related_id": normalized_related_id,
        "relation_type": normalized_relation_type,
        "source_type": normalized_related_type,
        "source_id": normalized_related_id,
        "target_type": owner_type,
        "target_id": owner_id,
    }


def relation_shape_for_owner(*, owner_type: str, owner_id: str, relation: Relation) -> dict[str, str]:
    if relation.source_type == owner_type and relation.source_id == owner_id:
        return {
            "direction": "outgoing",
            "related_type": relation.target_type,
            "related_id": relation.target_id,
            "relation_type": relation.relation_type,
            "source_type": relation.source_type,
            "source_id": relation.source_id,
            "target_type": relation.target_type,
            "target_id": relation.target_id,
        }
    if relation.target_type == owner_type and relation.target_id == owner_id:
        return {
            "direction": "incoming",
            "related_type": relation.source_type,
            "related_id": relation.source_id,
            "relation_type": relation.relation_type,
            "source_type": relation.source_type,
            "source_id": relation.source_id,
            "target_type": relation.target_type,
            "target_id": relation.target_id,
        }
    raise ValueError("Relation does not belong to owner")


def get_owned_relation_for_owner(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    relation_id: str,
) -> Relation:
    relation = db.get(Relation, relation_id)
    if relation is None or relation.user_id != user_id:
        raise ValueError("Relation not found")
    if is_hidden_participant_relation(relation):
        raise ValueError("Participant relation must be maintained from the participant editor")
    if not (
        (relation.source_type == owner_type and relation.source_id == owner_id)
        or (relation.target_type == owner_type and relation.target_id == owner_id)
    ):
        raise ValueError("Relation not found")
    return relation


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


def build_entity_aliases(db: Session, entity_id: str) -> list[dict[str, Any]]:
    rows = list_entity_alias_rows(db, entity_id)
    return [serialize_entity_alias(row) for row in rows]


def serialize_entity_alias(row: EntityAlias) -> dict[str, Any]:
    return {
        "id": row.id,
        "alias": row.alias,
        "normalized_alias": row.normalized_alias,
        "alias_type": row.alias_type,
        "created_at": isoformat(row.created_at),
    }


def build_relations_for_owner(db: Session, *, user_id: str, owner_type: str, owner_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(
        select(Relation)
        .where(
            Relation.user_id == user_id,
            or_(
                (Relation.source_type == owner_type) & (Relation.source_id == owner_id),
                (Relation.target_type == owner_type) & (Relation.target_id == owner_id),
            ),
        )
        .order_by(Relation.created_at.asc())
    ).all()
    return [
        item
        for row in rows
        if (item := serialize_relation_item_for_owner(db, user_id=user_id, owner_type=owner_type, owner_id=owner_id, relation=row))
        is not None
    ]


def serialize_relation_item_for_owner(
    db: Session,
    *,
    user_id: str,
    owner_type: str,
    owner_id: str,
    relation: Relation,
) -> dict[str, Any] | None:
    if is_hidden_participant_relation(relation):
        return None

    if relation.source_type == owner_type and relation.source_id == owner_id:
        direction = "outgoing"
        peer = get_owned_object_summary(db, user_id=user_id, object_type=relation.target_type, object_id=relation.target_id)
    elif relation.target_type == owner_type and relation.target_id == owner_id:
        direction = "incoming"
        peer = get_owned_object_summary(db, user_id=user_id, object_type=relation.source_type, object_id=relation.source_id)
    else:
        return None

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


def is_hidden_participant_relation(relation: Relation) -> bool:
    if {relation.source_type, relation.target_type} != {"entity", "event"}:
        return False
    meta_source = relation.meta_json.get("source") if isinstance(relation.meta_json, dict) else None
    return meta_source == "curation_participant" or relation.relation_type == "participates_in"


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
            "data": serialize_entity(entity, aliases=list_entity_alias_values(db, entity)),
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
