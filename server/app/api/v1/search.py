from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.models.note import Note
from app.schemas.common import Envelope
from app.schemas.search import (
    SearchMergeCandidateListResponse,
    SearchResultListResponse,
    SimilarNoteListResponse,
    UnifiedSearchResponse,
)
from app.services.search_service import (
    build_top_hits,
    clamp_limit,
    list_merge_candidates,
    normalize_query,
    search_entities,
    search_events,
    search_notes,
    similar_note_items,
    strip_scores,
)

router = APIRouter()


@router.get("", response_model=Envelope[SearchResultListResponse])
def search(q: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    notes = strip_scores(search_notes(db, user.id, q, limit=12))
    return ok(
        {
            "items": [
                {
                    "id": note["id"],
                    "title": note["title"],
                    "summary": note["summary"],
                    "type": "note",
                }
                for note in notes
            ]
        }
    )


@router.get("/unified", response_model=Envelope[UnifiedSearchResponse])
def unified_search(
    db: DbSession,
    q: str | None = None,
    seed_note_id: str | None = None,
    limit: int = 8,
    user=Depends(get_current_user),
) -> dict:
    normalized_query = normalize_query(q)
    normalized_limit = clamp_limit(limit)

    seed_note = None
    if seed_note_id:
        seed_note = db.get(Note, seed_note_id)
        if not seed_note or seed_note.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Seed note not found")

    scored_notes = search_notes(db, user.id, normalized_query, limit=normalized_limit) if normalized_query else []
    scored_entities = search_entities(db, user.id, normalized_query, limit=normalized_limit) if normalized_query else []
    scored_events = search_events(db, user.id, normalized_query, limit=normalized_limit) if normalized_query else []
    similar_notes = (
        similar_note_items(db, user.id, seed_note.id, limit=normalized_limit)
        if seed_note is not None
        else []
    )

    top_hits = build_top_hits(scored_notes, scored_entities, scored_events, similar_notes, limit=min(10, normalized_limit * 2))
    notes = strip_scores(scored_notes)
    entities = strip_scores(scored_entities)
    events = strip_scores(scored_events)

    return ok(
        {
            "query": normalized_query,
            "seed_note_id": seed_note.id if seed_note else None,
            "seed_note_title": seed_note.title if seed_note else None,
            "top_hits": top_hits,
            "notes": notes,
            "entities": entities,
            "events": events,
            "similar_notes": similar_notes,
            "stats": {
                "top_hit_count": len(top_hits),
                "note_count": len(notes),
                "entity_count": len(entities),
                "event_count": len(events),
                "similar_count": len(similar_notes),
            },
        }
    )


@router.get("/similar/{note_id}", response_model=Envelope[SimilarNoteListResponse])
def similar(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    note = db.get(Note, note_id)
    if not note or note.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return ok({"items": similar_note_items(db, user.id, note.id, limit=5)})


@router.get("/merge-candidates", response_model=Envelope[SearchMergeCandidateListResponse])
def list_merge_candidates_endpoint(
    db: DbSession,
    object_type: str | None = None,
    limit: int = 20,
    user=Depends(get_current_user),
) -> dict:
    return ok(
        {
            "items": list_merge_candidates(
                db,
                user_id=user.id,
                object_type=object_type,
                limit=clamp_limit(limit),
            )
        }
    )
