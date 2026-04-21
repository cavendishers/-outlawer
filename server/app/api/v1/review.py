from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok
from app.schemas.common import Envelope, PaginatedData
from app.schemas.review import (
    ConfirmEntityAliasRequest,
    ConfirmEntityAliasResponse,
    EntityReviewContextResponse,
    EventReviewContextResponse,
    MergeCandidateAcceptRequest,
    MergeCandidateAcceptResponse,
    MergeCandidateDetailResponse,
    MergeCandidateRejectRequest,
    MergeCandidateRejectResponse,
    MergeCandidateResponse,
)
from app.domains.governance import review

router = APIRouter()


@router.get("/merge-candidates", response_model=Envelope[PaginatedData[MergeCandidateResponse]])
def list_merge_candidates(
    db: DbSession,
    object_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
    user=Depends(get_current_user),
) -> dict:
    params = normalize_page_params(page, page_size)
    return ok(
        review.list_merge_candidates(
            db,
            user_id=user.id,
            object_type=object_type,
            status=status,
            page=params.page,
            page_size=params.page_size,
        )
    )


@router.get("/merge-candidates/{candidate_id}", response_model=Envelope[MergeCandidateDetailResponse])
def get_merge_candidate_detail(candidate_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review.get_merge_candidate_detail(db, user_id=user.id, candidate_id=candidate_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/reject", response_model=Envelope[MergeCandidateRejectResponse])
def reject_merge_candidate(
    candidate_id: str,
    payload: MergeCandidateRejectRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            review.reject_merge_candidate(
                db,
                user_id=user.id,
                candidate_id=candidate_id,
                reason=payload.reason,
                note=payload.note,
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/accept", response_model=Envelope[MergeCandidateAcceptResponse])
def accept_merge_candidate(
    candidate_id: str,
    payload: MergeCandidateAcceptRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    try:
        return ok(
            review.accept_merge_candidate(
                db,
                user_id=user.id,
                candidate_id=candidate_id,
                resolution=payload.resolution,
                survivor_id=payload.survivor_id,
                note=payload.note,
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/entities/{entity_id}/context", response_model=Envelope[EntityReviewContextResponse])
def get_entity_review_context(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review.get_entity_review_context(db, user_id=user.id, entity_id=entity_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/entities/{entity_id}/aliases", response_model=Envelope[ConfirmEntityAliasResponse])
def confirm_entity_alias(
    entity_id: str,
    payload: ConfirmEntityAliasRequest,
    db: DbSession,
    user=Depends(get_current_user),
) -> dict:
    alias = payload.alias.strip()
    if not alias:
        raise HTTPException(status_code=400, detail="Alias is required")
    try:
        return ok(
            review.confirm_entity_alias(
                db,
                user_id=user.id,
                entity_id=entity_id,
                alias=alias,
                note=payload.note,
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/events/{event_id}/context", response_model=Envelope[EventReviewContextResponse])
def get_event_review_context(event_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review.get_event_review_context(db, user_id=user.id, event_id=event_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
