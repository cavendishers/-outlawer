from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.serializers import serialize_event
from app.core.pagination import PageParams, paginate_query
from app.models.entity import Entity, EventEntity
from app.models.event import Event
from app.models.note import Note
from app.services.graph_service import get_related_events_for_event


def get_owned_event(db: Session, *, user_id: str, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None or event.user_id != user_id:
        raise ValueError("Event not found")
    return event


def list_events(db: Session, *, user_id: str, params: PageParams) -> tuple[list[dict[str, Any]], int]:
    query = select(Event).where(Event.user_id == user_id).order_by(Event.timeline_sort_time.desc())
    events, total = paginate_query(db, query, params)
    return [serialize_event(event) for event in events], total


def list_event_participants(db: Session, event_id: str, *, dedupe: bool = False) -> list[dict[str, Any]]:
    links = db.scalars(select(EventEntity).where(EventEntity.event_id == event_id).order_by(EventEntity.display_order.asc())).all()
    if not links:
        return []

    entities = {
        entity.id: entity
        for entity in db.scalars(select(Entity).where(Entity.id.in_([link.entity_id for link in links]))).all()
    }

    items: list[dict[str, Any]] = []
    seen_participant_ids: set[str] = set()
    for link in links:
        participant = entities.get(link.entity_id)
        if participant is None:
            continue
        if dedupe and participant.id in seen_participant_ids:
            continue
        seen_participant_ids.add(participant.id)
        items.append(
            {
                "id": participant.id,
                "display_name": participant.display_name,
                "entity_type": participant.entity_type,
                "role": link.role,
                "relation_type": link.relation_type,
                "confidence_score": link.confidence_score,
            }
        )
    return items


def get_event_detail(db: Session, *, user_id: str, event_id: str) -> dict[str, Any]:
    event = get_owned_event(db, user_id=user_id, event_id=event_id)
    source_note = db.get(Note, event.source_note_id) if event.source_note_id else None
    return {
        **serialize_event(event),
        "source_note_title": source_note.title if source_note else None,
        "participants": list_event_participants(db, event.id, dedupe=True),
        "related_events": get_related_events_for_event(db, user_id, event),
    }
