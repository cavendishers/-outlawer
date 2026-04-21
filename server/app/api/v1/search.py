from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import DbSession, get_current_user
from app.core.responses import ok
from app.domains.retrieval import search_query
from app.schemas.common import Envelope
from app.schemas.search import (
    SearchMergeCandidateListResponse,
    SearchResultListResponse,
    SimilarNoteListResponse,
    UnifiedSearchResponse,
)

router = APIRouter()


@router.get("", response_model=Envelope[SearchResultListResponse])
def search(q: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    notes = search_query.list_note_search_results(db, user_id=user.id, q=q, limit=12)
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
    try:
        return ok(search_query.build_unified_search_payload(db, user_id=user.id, q=q, seed_note_id=seed_note_id, limit=limit))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/similar/{note_id}", response_model=Envelope[SimilarNoteListResponse])
def similar(note_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok({"items": search_query.list_similar_note_results(db, user_id=user.id, note_id=note_id, limit=5)})
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/merge-candidates", response_model=Envelope[SearchMergeCandidateListResponse])
def list_merge_candidates_endpoint(
    db: DbSession,
    object_type: str | None = None,
    limit: int = 20,
    user=Depends(get_current_user),
) -> dict:
    return ok(
        {
            "items": search_query.list_merge_candidates(
                db,
                user_id=user.id,
                object_type=object_type,
                limit=search_query.clamp_limit(limit),
            )
        }
    )
