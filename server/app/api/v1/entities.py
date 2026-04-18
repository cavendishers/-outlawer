from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.serializers import serialize_entity
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.entity import Entity, EventEntity
from app.models.event import Event
from app.services.graph_service import get_timeline_fragments_for_entity

router = APIRouter()


@router.get("")
def list_entities(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(Entity).where(Entity.user_id == user.id).order_by(Entity.updated_at.desc())
    entities, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_entity(entity) for entity in entities],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{entity_id}")
def get_entity(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    entity = db.get(Entity, entity_id)
    if not entity or entity.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    links = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity.id)).all()
    related_events = []
    seen_event_ids: set[str] = set()
    for link in links:
        event = db.get(Event, link.event_id)
        if not event or event.id in seen_event_ids:
            continue
        seen_event_ids.add(event.id)
        related_events.append(
            {
                "id": event.id,
                "title": event.title,
                "summary": event.summary,
                "time_text": event.time_text,
                "event_type": event.event_type,
            }
        )
    return ok(
        {
            **serialize_entity(entity),
            "related_events": related_events,
            "timeline_fragments": get_timeline_fragments_for_entity(db, user.id, entity.id),
        }
    )


@router.get("/{entity_id}/events")
def entity_events(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    entity = db.get(Entity, entity_id)
    if not entity or entity.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    links = db.scalars(select(EventEntity).where(EventEntity.entity_id == entity.id)).all()
    items = []
    seen_event_ids: set[str] = set()
    for link in links:
        event = db.get(Event, link.event_id)
        if not event or event.id in seen_event_ids:
            continue
        seen_event_ids.add(event.id)
        items.append(
            {
                "id": event.id,
                "title": event.title,
                "summary": event.summary,
                "event_type": event.event_type,
                "start_time": event.start_time.isoformat() if event.start_time else None,
            }
        )
    return ok({"items": items})
