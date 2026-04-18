from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.serializers import serialize_event
from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params, paginate_query
from app.core.responses import ok, paginated
from app.models.entity import Entity, EventEntity
from app.models.event import Event
from app.models.note import Note
from app.services.graph_service import get_related_events_for_event

router = APIRouter()


@router.get("")
def list_events(
    db: DbSession,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    query = select(Event).where(Event.user_id == user.id).order_by(Event.timeline_sort_time.desc())
    events, total = paginate_query(db, query, params)
    return paginated(
        items=[serialize_event(event) for event in events],
        total=total,
        page=params.page,
        page_size=params.page_size,
    )


@router.get("/{event_id}")
def get_event(event_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    event = db.get(Event, event_id)
    if not event or event.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")
    links = db.scalars(select(EventEntity).where(EventEntity.event_id == event.id)).all()
    participant_items = []
    seen_participant_ids: set[str] = set()
    for link in links:
        participant = db.get(Entity, link.entity_id)
        if not participant or participant.id in seen_participant_ids:
            continue
        seen_participant_ids.add(participant.id)
        participant_items.append(
            {
                "id": participant.id,
                "display_name": participant.display_name,
                "entity_type": participant.entity_type,
                "role": link.role,
                "relation_type": link.relation_type,
                "confidence_score": link.confidence_score,
            }
        )
    source_note = db.get(Note, event.source_note_id) if event.source_note_id else None
    return ok(
        {
            **serialize_event(event),
            "source_note_title": source_note.title if source_note else None,
            "participants": participant_items,
            "related_events": get_related_events_for_event(db, user.id, event),
        }
    )
