from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import isoformat, serialize_entity
from app.core.pagination import PageParams, paginate_query
from app.models.entity import Entity, EventEntity
from app.models.event import Event
from app.services.graph_service import get_timeline_fragments_for_entity


def get_owned_entity(db: Session, *, user_id: str, entity_id: str) -> Entity:
    entity = db.get(Entity, entity_id)
    if entity is None or entity.user_id != user_id:
        raise ValueError("Entity not found")
    return entity


def list_entities(db: Session, *, user_id: str, params: PageParams) -> tuple[list[dict[str, Any]], int]:
    query = select(Entity).where(Entity.user_id == user_id).order_by(Entity.updated_at.desc())
    entities, total = paginate_query(db, query, params)
    return [serialize_entity(entity) for entity in entities], total


def list_related_events_for_entity(db: Session, *, user_id: str, entity_id: str) -> list[dict[str, Any]]:
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
                "start_time": isoformat(event.start_time),
            }
        )
    return items


def get_entity_detail(db: Session, *, user_id: str, entity_id: str) -> dict[str, Any]:
    entity = get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    related_events = list_related_events_for_entity(db, user_id=user_id, entity_id=entity.id)
    return {
        **serialize_entity(entity),
        "related_events": [
            {
                "id": item["id"],
                "title": item["title"],
                "summary": item["summary"],
                "time_text": item["time_text"],
                "event_type": item["event_type"],
            }
            for item in related_events
        ],
        "timeline_fragments": get_timeline_fragments_for_entity(db, user_id, entity.id),
    }


def list_entity_events(db: Session, *, user_id: str, entity_id: str) -> list[dict[str, Any]]:
    get_owned_entity(db, user_id=user_id, entity_id=entity_id)
    related_events = list_related_events_for_entity(db, user_id=user_id, entity_id=entity_id)
    return [
        {
            "id": item["id"],
            "title": item["title"],
            "summary": item["summary"],
            "event_type": item["event_type"],
            "start_time": item["start_time"],
        }
        for item in related_events
    ]
