from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import DbSession, get_current_user
from app.core.pagination import normalize_page_params
from app.core.responses import ok
from app.services import review_service

router = APIRouter()


@router.get("/merge-candidates")
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
        review_service.list_merge_candidates(
            db,
            user_id=user.id,
            object_type=object_type,
            status=status,
            page=params.page,
            page_size=params.page_size,
        )
    )


@router.get("/merge-candidates/{candidate_id}")
def get_merge_candidate_detail(candidate_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review_service.get_merge_candidate_detail(db, user_id=user.id, candidate_id=candidate_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/reject")
def reject_merge_candidate(candidate_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            review_service.reject_merge_candidate(
                db,
                user_id=user.id,
                candidate_id=candidate_id,
                reason=payload.get("reason") or "rejected_by_user",
                note=payload.get("note"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/merge-candidates/{candidate_id}/accept")
def accept_merge_candidate(candidate_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(
            review_service.accept_merge_candidate(
                db,
                user_id=user.id,
                candidate_id=candidate_id,
                resolution=payload.get("resolution") or "merge",
                survivor_id=payload.get("survivor_id"),
                note=payload.get("note"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/entities/{entity_id}/context")
def get_entity_review_context(entity_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review_service.get_entity_review_context(db, user_id=user.id, entity_id=entity_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/entities/{entity_id}/aliases")
def confirm_entity_alias(entity_id: str, payload: dict, db: DbSession, user=Depends(get_current_user)) -> dict:
    alias = (payload.get("alias") or "").strip()
    if not alias:
        raise HTTPException(status_code=400, detail="Alias is required")
    try:
        return ok(
            review_service.confirm_entity_alias(
                db,
                user_id=user.id,
                entity_id=entity_id,
                alias=alias,
                note=payload.get("note"),
            )
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/events/{event_id}/context")
def get_event_review_context(event_id: str, db: DbSession, user=Depends(get_current_user)) -> dict:
    try:
        return ok(review_service.get_event_review_context(db, user_id=user.id, event_id=event_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
