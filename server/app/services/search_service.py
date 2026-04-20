from math import sqrt

from sqlalchemy import exists, or_, select
from sqlalchemy.orm import Session

from app.models.embedding import Embedding
from app.models.entity import Entity, EntityAlias
from app.models.event import Event
from app.models.extraction import MergeCandidate
from app.models.note import Note
from app.services.entity_alias_service import build_entity_alias_map


def cosine_similarity(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(value * value for value in left)) or 1.0
    right_norm = sqrt(sum(value * value for value in right)) or 1.0
    return dot / (left_norm * right_norm)


def normalize_query(value: str | None) -> str:
    return (value or "").strip()


def clamp_limit(value: int) -> int:
    return max(1, min(value, 20))


def search_notes(db: Session, user_id: str, q: str, *, limit: int) -> list[dict]:
    if not q:
        return []
    pattern = f"%{q}%"
    notes = db.scalars(
        select(Note).where(
            Note.user_id == user_id,
            or_(Note.title.ilike(pattern), Note.summary.ilike(pattern), Note.canonical_text.ilike(pattern)),
        )
    ).all()
    items = [
        {
            "id": note.id,
            "title": note.title,
            "summary": note.summary,
            "status": note.status,
            "primary_time": note.primary_time.isoformat() if note.primary_time else None,
            "href": f"/story/note/{note.id}",
            "search_type": "note",
            "score": keyword_score(q, note.title, note.summary, note.canonical_text),
        }
        for note in notes
    ]
    items.sort(key=lambda item: (item["score"], item["primary_time"] or "", item["title"]), reverse=True)
    return items[:limit]


def search_entities(db: Session, user_id: str, q: str, *, limit: int) -> list[dict]:
    if not q:
        return []
    pattern = f"%{q}%"
    entities = db.scalars(
        select(Entity).where(
            Entity.user_id == user_id,
            or_(
                Entity.display_name.ilike(pattern),
                Entity.canonical_name.ilike(pattern),
                Entity.description.ilike(pattern),
                exists(
                    select(EntityAlias.id).where(
                        EntityAlias.entity_id == Entity.id,
                        or_(
                            EntityAlias.alias.ilike(pattern),
                            EntityAlias.normalized_alias.ilike(pattern),
                        ),
                    )
                ),
            ),
        )
    ).all()
    alias_map = build_entity_alias_map(db, entities)
    items = [
        {
            "id": entity.id,
            "display_name": entity.display_name,
            "canonical_name": entity.canonical_name,
            "entity_type": entity.entity_type,
            "description": entity.description,
            "aliases": alias_map.get(entity.id, []),
            "confidence_score": entity.confidence_score,
            "href": f"/story/entity/{entity.id}",
            "search_type": "entity",
            "score": keyword_score(q, entity.display_name, entity.canonical_name, entity.description, *alias_map.get(entity.id, [])),
        }
        for entity in entities
    ]
    items.sort(key=lambda item: (item["score"], item["confidence_score"] or 0, item["display_name"]), reverse=True)
    return items[:limit]


def search_events(db: Session, user_id: str, q: str, *, limit: int) -> list[dict]:
    if not q:
        return []
    pattern = f"%{q}%"
    events = db.scalars(
        select(Event).where(
            Event.user_id == user_id,
            or_(
                Event.title.ilike(pattern),
                Event.summary.ilike(pattern),
                Event.description.ilike(pattern),
                Event.location_text.ilike(pattern),
                Event.time_text.ilike(pattern),
            ),
        )
    ).all()
    items = [
        {
            "id": event.id,
            "title": event.title,
            "summary": event.summary,
            "event_type": event.event_type,
            "time_text": event.time_text,
            "location_text": event.location_text,
            "confidence_score": event.confidence_score,
            "href": f"/events/{event.id}",
            "search_type": "event",
            "score": keyword_score(q, event.title, event.summary, event.description, event.location_text, event.time_text),
        }
        for event in events
    ]
    items.sort(key=lambda item: (item["score"], item["time_text"] or "", item["title"]), reverse=True)
    return items[:limit]


def similar_note_items(db: Session, user_id: str, note_id: str, *, limit: int) -> list[dict]:
    current_embedding = db.scalar(select(Embedding).where(Embedding.owner_type == "note", Embedding.owner_id == note_id))
    if not current_embedding:
        return []
    embeddings = db.scalars(
        select(Embedding).where(Embedding.owner_type == "note", Embedding.owner_id != note_id)
    ).all()
    scored = []
    for embedding in embeddings:
        target_note = db.get(Note, embedding.owner_id)
        if target_note and target_note.user_id == user_id:
            scored.append(
                {
                    "note_id": target_note.id,
                    "id": target_note.id,
                    "title": target_note.title,
                    "summary": target_note.summary,
                    "primary_time": target_note.primary_time.isoformat() if target_note.primary_time else None,
                    "href": f"/story/note/{target_note.id}",
                    "search_type": "similar_note",
                    "score": float(round(cosine_similarity(current_embedding.vector, embedding.vector), 4)),
                }
            )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:limit]


def list_merge_candidates(
    db: Session,
    *,
    user_id: str,
    object_type: str | None = None,
    limit: int = 20,
) -> list[dict]:
    query = select(MergeCandidate).where(MergeCandidate.user_id == user_id)
    if object_type:
        query = query.where(MergeCandidate.object_type == object_type)
    candidates = db.scalars(query.order_by(MergeCandidate.score.desc(), MergeCandidate.created_at.desc()).limit(limit)).all()
    return [
        {
            "id": candidate.id,
            "object_type": candidate.object_type,
            "source_id": candidate.source_id,
            "source_label": resolve_object_label(db, candidate.object_type, candidate.source_id),
            "candidate_id": candidate.candidate_id,
            "candidate_label": resolve_object_label(db, candidate.object_type, candidate.candidate_id),
            "score": float(candidate.score),
            "status": candidate.status,
            "reason": candidate.reason_json,
        }
        for candidate in candidates
    ]


def build_top_hits(
    notes: list[dict],
    entities: list[dict],
    events: list[dict],
    similar_notes: list[dict],
    *,
    limit: int,
) -> list[dict]:
    combined: list[dict] = []
    for note in notes[: min(3, len(notes))]:
        combined.append(
            {
                "id": note["id"],
                "label": note["title"],
                "summary": note.get("summary"),
                "href": note["href"],
                "result_type": "note",
                "meta": [note.get("status"), note.get("primary_time")[:10] if note.get("primary_time") else None],
                "score": note.get("score", 0),
            }
        )
    for entity in entities[: min(3, len(entities))]:
        combined.append(
            {
                "id": entity["id"],
                "label": entity["display_name"],
                "summary": entity.get("description"),
                "href": entity["href"],
                "result_type": "entity",
                "meta": [entity.get("entity_type")],
                "score": entity.get("score", 0),
            }
        )
    for event in events[: min(3, len(events))]:
        combined.append(
            {
                "id": event["id"],
                "label": event["title"],
                "summary": event.get("summary"),
                "href": event["href"],
                "result_type": "event",
                "meta": [event.get("time_text"), event.get("location_text")],
                "score": event.get("score", 0),
            }
        )
    for note in similar_notes[: min(2, len(similar_notes))]:
        combined.append(
            {
                "id": note["id"],
                "label": note["title"],
                "summary": note.get("summary"),
                "href": note["href"],
                "result_type": "similar_note",
                "meta": [f"相似度 {int(note['score'] * 100)}%"],
                "score": note.get("score", 0),
            }
        )
    combined.sort(key=lambda item: item.get("score", 0), reverse=True)
    return strip_scores(combined[:limit])


def keyword_score(q: str, *values: str | None) -> int:
    normalized_query = q.strip().lower()
    if not normalized_query:
        return 0
    score = 0
    for index, value in enumerate(values):
        if not value:
            continue
        normalized_value = value.lower()
        weight = max(1, 6 - index)
        if normalized_value == normalized_query:
            score += 160 * weight
        elif normalized_value.startswith(normalized_query):
            score += 120 * weight
        elif normalized_query in normalized_value:
            score += 60 * weight
    return score


def strip_scores(items: list[dict]) -> list[dict]:
    cleaned: list[dict] = []
    for item in items:
        copied = dict(item)
        copied.pop("score", None)
        cleaned.append(copied)
    return cleaned


def resolve_object_label(db: Session, object_type: str, object_id: str) -> str | None:
    if object_type == "note":
        note = db.get(Note, object_id)
        return note.title if note else None
    if object_type == "event":
        event = db.get(Event, object_id)
        return event.title if event else None
    if object_type == "entity":
        entity = db.get(Entity, object_id)
        return entity.display_name if entity else None
    return None
